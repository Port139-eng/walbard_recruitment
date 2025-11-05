from __future__ import annotations
"""Railway-friendly looped recruitment autopilot."""

import json
import logging
import os
import time
from typing import List, Optional, Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Env variables (must be set in Railway / environment)
CLIENT_KEY = os.getenv("NS_CLIENT_KEY")
TGID = os.getenv("NS_TGID")
SECRET_KEY = os.getenv("NS_SECRET_KEY")
USER_AGENT = os.getenv("NS_USER_AGENT", "WalbardRecruitBot")

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
DELAY = int(os.getenv("NS_DELAY", "180"))
POLL_SLEEP = int(os.getenv("NS_POLL_SLEEP", "60"))
STATE_FILE = "sent_nations.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def make_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def send_tg(session: requests.Session, nation: str, dry_run: bool = False) -> Optional[requests.Response]:
    if not CLIENT_KEY or not TGID or not SECRET_KEY:
        logging.error("Missing required environment variables: NS_CLIENT_KEY/NS_TGID/NS_SECRET_KEY")
        return None

    if dry_run:
        logging.info("dry-run: would send TG to %s", nation)
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"dry-run"
        return resp

    payload = {"a": "sendTG", "client": CLIENT_KEY, "tgid": TGID, "key": SECRET_KEY, "to": nation}
    try:
        resp = session.post(API_URL, data=payload, timeout=30)
        resp.raise_for_status()
        logging.info("Sent TG to %s: %s", nation, resp.text)
        return resp
    except requests.RequestException as exc:
        logging.error("Failed to send TG to %s: %s", nation, exc)
        return None


def load_targets() -> List[str]:
    if not os.path.exists("targets.txt"):
        return []
    with open("targets.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


def load_sent_nations() -> Set[str]:
    """Load previously sent nations from persistent state file."""
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return set(data.get("sent_nations", []))
    except (json.JSONDecodeError, IOError) as exc:
        logging.warning("Failed to load state file %s: %s", STATE_FILE, exc)
        return set()


def save_sent_nations(sent_nations: Set[str]) -> None:
    """Save sent nations to persistent state file."""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump({"sent_nations": sorted(list(sent_nations))}, fh, indent=2)
    except IOError as exc:
        logging.error("Failed to save state file %s: %s", STATE_FILE, exc)


def main_loop() -> None:
    session = make_session()
    sent_nations = set()

    logging.info("Autopilot started. Press Ctrl+C to stop.")

    try:
        while True:
            targets = load_targets()
            targets_to_send = [nation for nation in targets if nation not in sent_nations]

            if not targets_to_send:
                logging.info("No new targets. Sleeping for %s seconds...", POLL_SLEEP)
                time.sleep(POLL_SLEEP)
                continue

            for nation in targets_to_send:
                resp = send_tg(session, nation)
                if resp and getattr(resp, "status_code", None) and 200 <= resp.status_code < 300:
                    sent_nations.add(nation)
                else:
                    logging.info("Not adding %s to sent list due to failed send.", nation)
                logging.info("Sleeping %s seconds before next TG...", DELAY)
                time.sleep(DELAY)
    except KeyboardInterrupt:
        logging.info("Autopilot stopped by user.")


if __name__ == "__main__":
    main_loop()
