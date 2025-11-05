"""Railway-friendly looped recruitment autopilot.

Continuously reads `targets.txt`, sends telegrams one-by-one, sleeps `DELAY`
seconds between sends, and keeps running. Tracks successful sends to avoid
resending the same nation.
"""

import logging
import os
import time
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Env variables (must be set in Railway / environment)
CLIENT_KEY = os.getenv("NS_CLIENT_KEY")
TGID = os.getenv("NS_TGID")
SECRET_KEY = os.getenv("NS_SECRET_KEY")
USER_AGENT = os.getenv("NS_USER_AGENT", "WalbardRecruitBot")

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
DELAY = int(os.getenv("NS_DELAY", "180"))  # seconds between TGs
POLL_SLEEP = int(os.getenv("NS_POLL_SLEEP", "60"))  # sleep when no new targets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def make_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=False)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def send_tg(session: requests.Session, nation: str, client_key: Optional[str] = None, tgid: Optional[str] = None, secret_key: Optional[str] = None, dry_run: bool = False) -> Optional[requests.Response]:
    """Send a TG to the given nation.

    Signature is backward-compatible with existing tests:
      send_tg(session, nation, client_key, tgid, secret_key, dry_run)

    If client_key/tgid/secret_key are not provided, environment variables are used.
    Returns the Response on success, or None on error.
    """
    # allow test override or use env vars
    effective_client = client_key or CLIENT_KEY
    effective_tgid = tgid or TGID
    effective_secret = secret_key or SECRET_KEY

    if dry_run:
        logging.info("dry-run: would send TG to %s with client=%s tgid=%s", nation, effective_client, effective_tgid)
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"dry-run"
        return resp

    if not effective_client or not effective_tgid or not effective_secret:
        logging.error("Missing required environment variables or parameters: NS_CLIENT_KEY/NS_TGID/NS_SECRET_KEY. Aborting send.")
        return None

    payload = {"a": "sendTG", "client": effective_client, "tgid": effective_tgid, "key": effective_secret, "to": nation}
    try:
        resp = session.post(API_URL, data=payload, timeout=30)
        resp.raise_for_status()
        logging.info("Sent TG to %s: %s", nation, resp.text)
        return resp
    except requests.RequestException as e:
        logging.error("Failed to send TG to %s: %s", nation, e)
        return None


def load_targets() -> List[str]:
    if not os.path.exists("targets.txt"):
        return []
    with open("targets.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


def main_loop() -> None:
    session = make_session()
    sent_nations = set()

    logging.info("Autopilot started. Press Ctrl+C to stop.")

    try:
        while True:
            targets = load_targets()
            # send only nations we haven't successfully sent to yet
            targets_to_send = [n for n in targets if n not in sent_nations]

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
"""Railway-friendly looped recruitment autopilot.

Continuously reads `targets.txt`, sends telegrams one-by-one, sleeps `DELAY`
seconds between sends, and keeps running. Tracks successful sends to avoid
resending the same nation.
"""
import logging
import os
import time
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Env variables (must be set in Railway / environment)
CLIENT_KEY = os.getenv("NS_CLIENT_KEY")
TGID = os.getenv("NS_TGID")
SECRET_KEY = os.getenv("NS_SECRET_KEY")
USER_AGENT = os.getenv("NS_USER_AGENT", "WalbardRecruitBot")

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
DELAY = int(os.getenv("NS_DELAY", "180"))  # seconds between TGs
POLL_SLEEP = int(os.getenv("NS_POLL_SLEEP", "60"))  # sleep when no new targets

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def make_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=False)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def send_tg(session: requests.Session, nation: str, client_key: Optional[str] = None, tgid: Optional[str] = None, secret_key: Optional[str] = None, dry_run: bool = False) -> Optional[requests.Response]:
    """Send a TG to the given nation.

    Signature is backward-compatible with existing tests:
      send_tg(session, nation, client_key, tgid, secret_key, dry_run)

    If client_key/tgid/secret_key are not provided, environment variables are used.
    Returns the Response on success, or None on error.
    """
    # allow test override or use env vars
    effective_client = client_key or CLIENT_KEY
    effective_tgid = tgid or TGID
    effective_secret = secret_key or SECRET_KEY

    if dry_run:
        logging.info("dry-run: would send TG to %s with client=%s tgid=%s", nation, effective_client, effective_tgid)
        resp = requests.Response()
        resp.status_code = 200
        resp._content = b"dry-run"
        return resp

    if not effective_client or not effective_tgid or not effective_secret:
        logging.error("Missing required environment variables or parameters: NS_CLIENT_KEY/NS_TGID/NS_SECRET_KEY. Aborting send.")
        return None

    payload = {"a": "sendTG", "client": effective_client, "tgid": effective_tgid, "key": effective_secret, "to": nation}
    try:
        resp = session.post(API_URL, data=payload, timeout=30)
        resp.raise_for_status()
        logging.info("Sent TG to %s: %s", nation, resp.text)
        return resp
    except requests.RequestException as e:
        logging.error("Failed to send TG to %s: %s", nation, e)
        return None


def load_targets() -> List[str]:
    if not os.path.exists("targets.txt"):
        return []
    with open("targets.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


def main_loop() -> None:
    session = make_session()
    sent_nations = set()

    logging.info("Autopilot started. Press Ctrl+C to stop.")

    try:
        while True:
            targets = load_targets()
            # send only nations we haven't successfully sent to yet
            targets_to_send = [n for n in targets if n not in sent_nations]

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
    """Railway-friendly looped recruitment autopilot.

    Continuously reads `targets.txt`, sends telegrams one-by-one, sleeps `DELAY`
    seconds between sends, and keeps running. Tracks successful sends to avoid
    resending the same nation.
    """
    from __future__ import annotations

    import logging
    import os
    import time
    from typing import List, Optional

    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    # Env variables (must be set in Railway / environment)
    CLIENT_KEY = os.getenv("NS_CLIENT_KEY")
    TGID = os.getenv("NS_TGID")
    SECRET_KEY = os.getenv("NS_SECRET_KEY")
    USER_AGENT = os.getenv("NS_USER_AGENT", "WalbardRecruitBot")

    API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
    DELAY = int(os.getenv("NS_DELAY", "180"))  # seconds between TGs
    POLL_SLEEP = int(os.getenv("NS_POLL_SLEEP", "60"))  # sleep when no new targets

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


    def make_session(retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
        session = requests.Session()
        retry = Retry(total=retries, read=retries, connect=retries, backoff_factor=backoff_factor, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=False)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": USER_AGENT})
        return session


    def send_tg(session: requests.Session, nation: str) -> Optional[requests.Response]:
        """Send a TG to the given nation. Returns the Response on success, or None on error."""
        if not CLIENT_KEY or not TGID or not SECRET_KEY:
            logging.error("Missing required environment variables: NS_CLIENT_KEY/NS_TGID/NS_SECRET_KEY. Aborting send.")
            return None

        payload = {"a": "sendTG", "client": CLIENT_KEY, "tgid": TGID, "key": SECRET_KEY, "to": nation}
        try:
            resp = session.post(API_URL, data=payload, timeout=30)
            resp.raise_for_status()
            logging.info("Sent TG to %s: %s", nation, resp.text)
            return resp
        except requests.RequestException as e:
            logging.error("Failed to send TG to %s: %s", nation, e)
            return None


    def load_targets() -> List[str]:
        if not os.path.exists("targets.txt"):
            return []
        with open("targets.txt", "r", encoding="utf-8") as fh:
            return [line.strip() for line in fh if line.strip() and not line.startswith("#")]


    def main_loop() -> None:
        session = make_session()
        sent_nations = set()

        logging.info("Autopilot started. Press Ctrl+C to stop.")

        try:
            while True:
                targets = load_targets()
                # send only nations we haven't successfully sent to yet
                targets_to_send = [n for n in targets if n not in sent_nations]

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
