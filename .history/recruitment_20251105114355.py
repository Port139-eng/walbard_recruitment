"""Recruitment telegram sender for NationStates with improved CLI, retries and logging.

Usage examples:
  python recruitment.py --targets nation1 nation2
  python recruitment.py --targets-file targets.txt --delay 180

Secrets can be provided via environment variables: NS_CLIENT_KEY, NS_TGID, NS_SECRET_KEY
If not provided, defaults in this file are used (not recommended for production).
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from typing import Iterable, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Default configuration (prefer setting via environment variables)
CLIENT_KEY = os.getenv("NS_CLIENT_KEY", "f1db6341")
TGID = os.getenv("NS_TGID", "36674241")
SECRET_KEY = os.getenv("NS_SECRET_KEY", "41414cbef296")
USER_AGENT = os.getenv("NS_USER_AGENT", "RecruitBot (by Ephraim)")

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"


def make_session(retries: int = 3, backoff_factor: float = 0.5, status_forcelist: Optional[List[int]] = None) -> requests.Session:
    """Create a Requests session configured with retry/backoff.

    Args:
        retries: number of total retries for failed requests.
        backoff_factor: multiplier for backoff sleep between retries.
        status_forcelist: HTTP status codes to retry on.
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=status_forcelist, allowed_methods=False)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def send_tg(session: requests.Session, nation: str, client_key: str, tgid: str, secret_key: str, dry_run: bool = False) -> requests.Response:
    """Send a telegram to a nation via the NationStates API.

    Raises requests.RequestException on network errors.
    """
    payload = {
        "a": "sendTG",
        "client": client_key,
        "tgid": tgid,
        "key": secret_key,
        "to": nation,
    }

    if dry_run:
        logging.info("dry-run: would send TG to %s with payload=%s", nation, {k: (v if k != "key" else "***") for k, v in payload.items()})
        # create a dummy response-like object for tests if needed
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"dry-run"
        return resp

    logging.debug("Sending TG to %s", nation)
    resp = session.post(API_URL, data=payload, timeout=30)
    resp.raise_for_status()
    logging.info("Sent TG to %s: status=%s", nation, resp.status_code)
    return resp


def load_targets_from_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as fh:
        lines = [line.strip() for line in fh]
    # filter out empty lines and comments
    return [l for l in lines if l and not l.startswith("#")]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send recruitment telegrams to NationStates nations.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--targets", nargs="+", help="List of target nation names (space separated).")
    group.add_argument("--targets-file", help="Path to a text file with one nation per line.")
    parser.add_argument("--delay", type=int, default=180, help="Delay between telegrams in seconds (default: 180).")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries for HTTP requests.")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually send requests; just log actions.")
    parser.add_argument("--verbose", "-v", action="count", default=0, help="Increase verbosity (can be repeated).")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    log_level = logging.WARNING
    if args.verbose >= 2:
        log_level = logging.DEBUG
    elif args.verbose == 1:
        log_level = logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(message)s")

    # Resolve targets
    if args.targets_file:
        targets = load_targets_from_file(args.targets_file)
    else:
        targets = list(args.targets or [])

    if not targets:
        logging.error("No targets provided after loading; exiting.")
        return 2

    # Warn if secrets are defaults
    if CLIENT_KEY.startswith("f1db") or SECRET_KEY.startswith("41414"):
        logging.warning("Using embedded default client/secret values. Set NS_CLIENT_KEY/NS_SECRET_KEY environment variables to override for production.")

    session = make_session(retries=args.retries)

    for idx, nation in enumerate(targets, start=1):
        try:
            resp = send_tg(session, nation, CLIENT_KEY, TGID, SECRET_KEY, dry_run=args.dry_run)
            # Log response body at debug level (avoid leaking secrets in logs)
            logging.debug("Response for %s: %s", nation, resp.text if hasattr(resp, "text") else repr(resp))
        except requests.RequestException as exc:
            logging.error("Failed to send TG to %s: %s", nation, exc)
        if idx < len(targets):
            logging.info("Sleeping for %s seconds before next TG...", args.delay)
            time.sleep(args.delay)

    logging.info("Done processing %d targets.", len(targets))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
import requests
import time

CLIENT_KEY = "f1db6341"  # your new client key
TGID = "36674241"         # your recruitment telegram ID
SECRET_KEY = "41414cbef296"  # your secret key
USER_AGENT = "WalbardRecruitBot"  

# List of nations to send telegrams to
targets = ["nation1", "nation2", "nation3"]  # replace with actual targets

def send_tg(nation):
    url = f"https://www.nationstates.net/cgi-bin/api.cgi"
    payload = {
        "a": "sendTG",
        "client": CLIENT_KEY,
        "tgid": TGID,
        "key": SECRET_KEY,
        "to": nation
    }
    headers = {"User-Agent": USER_AGENT}
    response = requests.post(url, data=payload, headers=headers)
    print(f"Sent TG to {nation}: {response.text}")

# Send telegrams with safe timing
for nation in targets:
    send_tg(nation)
    time.sleep(180)  # 3 minutes per telegram (recruitment API limit)
