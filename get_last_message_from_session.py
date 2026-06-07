import argparse
import os

import requests

from log_config import logger

API_KEY = os.environ["DEVIN_API_KEY"]
BASE = "https://api.devin.ai/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}


def get_last_message_from_session(session_id: str) -> str:
    resp = requests.get(
        f"{BASE}/enterprise/sessions/{session_id}/messages",
        headers=HEADERS,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    devin_messages = [m for m in items if m["source"] == "devin"]
    return devin_messages[-1]["message"] if devin_messages else ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch the last Devin message from a session")
    parser.add_argument("session_id", help="Devin session ID")
    args = parser.parse_args()

    message = get_last_message_from_session(args.session_id)
    logger.info(message)
