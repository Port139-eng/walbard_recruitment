"""Appwrite Function entry point for the NationStates recruitment bot.

Each execution discovers newly founded nations and sends ONE recruitment
telegram to the first eligible unseen nation.  The cron schedule defined
in appwrite.json (*/2 * * * * — every 2 minutes) controls the send rate,
mirroring the NS_DELAY behaviour of the original long-running autopilot.

State persistence
-----------------
If the environment variable APPWRITE_BUCKET_ID is set the function stores
``sent_nations.json`` and ``discovered_nations.json`` in that Appwrite
Storage bucket so state survives across executions.  Without it the files
fall back to the local filesystem (ephemeral — state resets each run).
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from recruitment import (
    discover_new_nations,
    fetch_nation_region,
    load_discovered_nations,
    load_region_campaigns,
    load_sent_nations,
    make_session,
    normalize_region_name,
    save_discovered_nations,
    save_sent_nations,
    send_tg,
)

# ---------------------------------------------------------------------------
# Appwrite Storage helpers
# ---------------------------------------------------------------------------

_SENT_FILE_ID = "sent_nations"
_DISCOVERED_FILE_ID = "discovered_nations"
_SENT_FILENAME = "sent_nations.json"
_DISCOVERED_FILENAME = "discovered_nations.json"


def _make_appwrite_client() -> Optional[Any]:
    """Return a configured Appwrite Client, or None if env vars are missing."""
    endpoint = os.environ.get("APPWRITE_FUNCTION_API_ENDPOINT")
    project_id = os.environ.get("APPWRITE_FUNCTION_PROJECT_ID")
    api_key = os.environ.get("APPWRITE_API_KEY")
    if not (endpoint and project_id and api_key):
        return None
    from appwrite.client import Client  # noqa: PLC0415

    return (
        Client()
        .set_endpoint(endpoint)
        .set_project(project_id)
        .set_key(api_key)
    )


def _storage_load(client: Any, bucket_id: str, file_id: str) -> Optional[bytes]:
    """Download a file from Appwrite Storage; return None if it does not exist."""
    from appwrite.exception import AppwriteException  # noqa: PLC0415
    from appwrite.services.storage import Storage  # noqa: PLC0415

    try:
        return Storage(client).get_file_download(bucket_id, file_id)
    except AppwriteException:
        return None


def _storage_save(client: Any, bucket_id: str, file_id: str, filename: str, data: bytes) -> None:
    """Upload (or replace) a file in Appwrite Storage."""
    from appwrite.exception import AppwriteException  # noqa: PLC0415
    from appwrite.input_file import InputFile  # noqa: PLC0415
    from appwrite.services.storage import Storage  # noqa: PLC0415

    storage = Storage(client)
    # Remove any existing version before uploading the new one.
    try:
        storage.delete_file(bucket_id, file_id)
    except AppwriteException:
        pass
    storage.create_file(
        bucket_id,
        file_id,
        InputFile.from_bytes(data, filename, "application/json"),
    )


def _load_set_from_storage(client: Any, bucket_id: str, file_id: str, key: str) -> set:
    raw = _storage_load(client, bucket_id, file_id)
    if raw is None:
        return set()
    try:
        return set(json.loads(raw.decode("utf-8")).get(key, []))
    except (json.JSONDecodeError, AttributeError):
        return set()


def _save_set_to_storage(
    client: Any, bucket_id: str, file_id: str, filename: str, key: str, data: set
) -> None:
    payload = json.dumps({key: sorted(data)}, indent=2).encode("utf-8")
    _storage_save(client, bucket_id, file_id, filename, payload)


# ---------------------------------------------------------------------------
# Appwrite Function entry point
# ---------------------------------------------------------------------------


def main(context):  # noqa: ANN001
    """Run one recruitment iteration.

    Called by Appwrite on every cron tick (every 2 minutes by default).
    """
    # ------------------------------------------------------------------
    # 1. Validate required NationStates credentials
    # ------------------------------------------------------------------
    for var in ("NS_CLIENT_KEY", "NS_TGID", "NS_SECRET_KEY"):
        if not os.environ.get(var):
            msg = f"Missing required environment variable: {var}"
            context.error(msg)
            return context.res.json({"error": msg}, 500)

    # ------------------------------------------------------------------
    # 2. Set up state backend (Appwrite Storage or local filesystem)
    # ------------------------------------------------------------------
    bucket_id = os.environ.get("APPWRITE_BUCKET_ID")
    appwrite_client = _make_appwrite_client() if bucket_id else None
    use_storage = bool(bucket_id and appwrite_client)

    if use_storage:
        sent_nations = _load_set_from_storage(
            appwrite_client, bucket_id, _SENT_FILE_ID, "sent_nations"
        )
        discovered_nations = _load_set_from_storage(
            appwrite_client, bucket_id, _DISCOVERED_FILE_ID, "discovered_nations"
        )
    else:
        sent_nations = load_sent_nations()
        discovered_nations = load_discovered_nations()

    context.log(
        f"State loaded — sent: {len(sent_nations)}, discovered: {len(discovered_nations)}"
    )

    # ------------------------------------------------------------------
    # 3. Discover new nations & load active regional campaigns
    # ------------------------------------------------------------------
    session = make_session()
    campaigns = load_region_campaigns()
    new_nations = discover_new_nations(session)

    context.log(f"Discovered {len(new_nations)} nations from NationStates API")

    # ------------------------------------------------------------------
    # 4. Process: find the first eligible unseen nation and send ONE TG
    # ------------------------------------------------------------------
    undiscovered = [n for n in new_nations if n not in discovered_nations]
    discovered_nations.update(new_nations)

    telegram_sent = False
    skipped = 0
    target_nation = None

    for nation in undiscovered:
        if nation in sent_nations:
            skipped += 1
            continue

        # Apply regional campaign filter if any campaigns are active.
        if campaigns:
            region = fetch_nation_region(session, nation)
            if not region or normalize_region_name(region) not in campaigns:
                context.log(
                    f"Skipping {nation} — region '{region or 'unknown'}' not in active campaign"
                )
                skipped += 1
                continue

        # Send the recruitment telegram.
        resp = send_tg(session, nation)
        status = getattr(resp, "status_code", None)
        if resp and status is not None and 200 <= status < 300:
            sent_nations.add(nation)
            telegram_sent = True
            target_nation = nation
            context.log(f"Sent recruitment telegram to {nation}")
        else:
            context.error(f"Failed to send telegram to {nation}")

        # One telegram per execution — exit the loop.
        break

    # ------------------------------------------------------------------
    # 5. Persist updated state
    # ------------------------------------------------------------------
    if use_storage:
        _save_set_to_storage(
            appwrite_client, bucket_id, _SENT_FILE_ID, _SENT_FILENAME, "sent_nations", sent_nations
        )
        _save_set_to_storage(
            appwrite_client,
            bucket_id,
            _DISCOVERED_FILE_ID,
            _DISCOVERED_FILENAME,
            "discovered_nations",
            discovered_nations,
        )
    else:
        save_sent_nations(sent_nations)
        save_discovered_nations(discovered_nations)

    # ------------------------------------------------------------------
    # 6. Return summary
    # ------------------------------------------------------------------
    result = {
        "new_nations_found": len(new_nations),
        "undiscovered_this_run": len(undiscovered),
        "telegram_sent": telegram_sent,
        "nation_targeted": target_nation,
        "skipped": skipped,
        "total_sent_ever": len(sent_nations),
        "state_backend": "appwrite_storage" if use_storage else "local_filesystem",
    }
    context.log(f"Run complete: {result}")
    return context.res.json(result)
