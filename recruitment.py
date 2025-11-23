from __future__ import annotations
"""Railway-friendly looped recruitment autopilot for newly founded nations."""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from xml.etree import ElementTree as ET

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Env variables (must be set in Railway / environment)
CLIENT_KEY = os.getenv("NS_CLIENT_KEY")
TGID = os.getenv("NS_TGID")
SECRET_KEY = os.getenv("NS_SECRET_KEY")
USER_AGENT = os.getenv("NS_USER_AGENT", "WalbardRecruitBot")

API_URL = "https://www.nationstates.net/cgi-bin/api.cgi"
DELAY = int(os.getenv("NS_DELAY", "120"))
POLL_SLEEP = int(os.getenv("NS_POLL_SLEEP", "60"))
DISCOVER_SLEEP = int(os.getenv("NS_DISCOVER_SLEEP", "60"))  # Poll for new nations every 60s
STATE_FILE = "sent_nations.json"
DISCOVERED_FILE = "discovered_nations.json"
REGION_CAMPAIGNS_FILE = os.getenv("NS_REGION_CAMPAIGNS_FILE", "region_targets.json")

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


def normalize_region_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return "_".join(name.strip().lower().split())


def parse_timestamp(raw_value: Optional[str]) -> Optional[datetime]:
    if not raw_value:
        return None
    value = raw_value.strip()
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        logging.warning("Invalid timestamp '%s' in %s", raw_value, REGION_CAMPAIGNS_FILE)
        return None


def load_region_campaigns(now: Optional[datetime] = None) -> Dict[str, str]:
    """Return mapping of normalized region name -> campaign tag for active campaigns."""
    if not os.path.exists(REGION_CAMPAIGNS_FILE):
        return {}

    try:
        with open(REGION_CAMPAIGNS_FILE, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except (json.JSONDecodeError, IOError) as exc:
        logging.warning("Failed to load region campaigns from %s: %s", REGION_CAMPAIGNS_FILE, exc)
        return {}

    campaigns = payload.get("campaigns", []) if isinstance(payload, dict) else []
    now_ts = now or datetime.now(timezone.utc)
    region_map: Dict[str, str] = {}

    for campaign in campaigns:
        if not isinstance(campaign, dict):
            continue
        tag = campaign.get("tag") or "campaign"
        starts_at = parse_timestamp(campaign.get("starts_at"))
        ends_at = parse_timestamp(campaign.get("ends_at"))

        if starts_at and now_ts < starts_at:
            continue
        if ends_at and now_ts > ends_at:
            continue

        regions = campaign.get("regions", [])
        if not isinstance(regions, list):
            continue
        for region in regions:
            normalized = normalize_region_name(region)
            if normalized:
                region_map[normalized] = tag

    if region_map:
        logging.info("Loaded %d active region targets", len(region_map))
    return region_map


def discover_new_nations(session: requests.Session) -> List[str]:
    """Fetch newly founded nations from NationStates API."""
    try:
        # API endpoint for getting new nations
        # Uses the "newnations" shard which returns nations founded in the last 24 hours
        params = {"q": "newnations"}
        headers = {"User-Agent": USER_AGENT}
        resp = session.get(API_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        
        # Parse XML response
        root = ET.fromstring(resp.content)
        nations = []
        
        # newnations returns a comma-separated string
        newnations_elem = root.find("NEWNATIONS")
        if newnations_elem is not None and newnations_elem.text:
            nation_list = newnations_elem.text.split(",")
            nations = [n.strip() for n in nation_list if n.strip()]
        
        logging.info("Discovered %d newly founded nations", len(nations))
        return nations
    except requests.RequestException as exc:
        logging.error("Failed to discover new nations: %s", exc)
        return []
    except ET.ParseError as exc:
        logging.error("Failed to parse API response: %s", exc)
        return []


def fetch_nation_region(session: requests.Session, nation: str) -> Optional[str]:
    params = {"nation": nation.replace(" ", "_"), "q": "region"}
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = session.get(API_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        region_elem = root.find("REGION")
        if region_elem is not None and region_elem.text:
            return region_elem.text.strip()
        return None
    except requests.RequestException as exc:
        logging.warning("Failed to fetch region for %s: %s", nation, exc)
        return None
    except ET.ParseError as exc:
        logging.warning("Failed to parse region response for %s: %s", nation, exc)
        return None


def load_discovered_nations() -> Set[str]:
    """Load previously discovered nations to avoid duplicates."""
    if not os.path.exists(DISCOVERED_FILE):
        return set()
    try:
        with open(DISCOVERED_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return set(data.get("discovered_nations", []))
    except (json.JSONDecodeError, IOError) as exc:
        logging.warning("Failed to load discovered nations file: %s", exc)
        return set()


def save_discovered_nations(discovered: Set[str]) -> None:
    """Save discovered nations to avoid re-discovering them."""
    try:
        with open(DISCOVERED_FILE, "w", encoding="utf-8") as fh:
            json.dump({"discovered_nations": sorted(list(discovered))}, fh, indent=2)
    except IOError as exc:
        logging.error("Failed to save discovered nations file: %s", exc)


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
    sent_nations = load_sent_nations()
    discovered_nations = load_discovered_nations()
    nation_region_cache: Dict[str, Optional[str]] = {}

    logging.info("Autopilot started. Loaded %d sent nations, %d discovered nations. Press Ctrl+C to stop.", 
                 len(sent_nations), len(discovered_nations))

    try:
        while True:
            region_targets = load_region_campaigns()

            # Discover newly founded nations
            new_nations = discover_new_nations(session)
            
            if new_nations:
                # Find nations we haven't discovered yet
                undiscovered = [n for n in new_nations if n not in discovered_nations]
                
                if undiscovered:
                    logging.info("Found %d new undiscovered nations", len(undiscovered))
                    discovered_nations.update(undiscovered)
                    save_discovered_nations(discovered_nations)
                    
                    # Send to each new nation
                    for nation in undiscovered:
                        campaign_tag = None
                        if region_targets:
                            region_name = nation_region_cache.get(nation)
                            if region_name is None:
                                region_name = fetch_nation_region(session, nation)
                                nation_region_cache[nation] = region_name
                            normalized_region = normalize_region_name(region_name)
                            campaign_tag = region_targets.get(normalized_region)
                            if not campaign_tag:
                                logging.info("Skipping %s; region '%s' not in active campaign", nation, region_name or "unknown")
                                continue
                            logging.info("Targeting %s under campaign '%s' (region: %s)", nation, campaign_tag, region_name)

                        if nation not in sent_nations:
                            logging.info("Sending TG to newly founded nation: %s", nation)
                            resp = send_tg(session, nation)
                            if resp and getattr(resp, "status_code", None) and 200 <= resp.status_code < 300:
                                sent_nations.add(nation)
                                save_sent_nations(sent_nations)
                                if campaign_tag:
                                    logging.info("Successfully sent TG to %s [campaign=%s]", nation, campaign_tag)
                                else:
                                    logging.info("Successfully sent TG to %s", nation)
                            else:
                                logging.warning("Failed to send TG to %s", nation)
                            
                            logging.info("Sleeping %s seconds before next TG...", DELAY)
                            time.sleep(DELAY)
                else:
                    logging.info("No new undiscovered nations. Sleeping for %s seconds...", DISCOVER_SLEEP)
                    time.sleep(DISCOVER_SLEEP)
            else:
                logging.info("Could not discover new nations. Sleeping for %s seconds...", DISCOVER_SLEEP)
                time.sleep(DISCOVER_SLEEP)
                
    except KeyboardInterrupt:
        logging.info("Autopilot stopped by user.")
        save_sent_nations(sent_nations)
        save_discovered_nations(discovered_nations)


if __name__ == "__main__":
    main_loop()
