import json
import os
import time
import requests

from log_config import logger

API_KEY = os.environ["DEVIN_API_KEY"]
ORG_ID = os.environ["DEVIN_ORG_ID"]
BASE = "https://api.devin.ai/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
SELF_ID = os.environ["SELF_USER_ID"]


def run():
    me = requests.get(f"{BASE}/self", headers=HEADERS)
    me.raise_for_status()
    data = me.json()
    logger.info(f"Authenticated as: {data.get('service_user_name') or data.get('user_name')}")

    session = requests.post(
        f"{BASE}/organizations/{ORG_ID}/sessions",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"prompt": "Create a Python script that analyzes CSV data", "create_as_user_id": SELF_ID},
    ).json()
    logger.info(f"Session: {session['url']}")

    session_url = f"{BASE}/organizations/{ORG_ID}/sessions/{session['session_id']}"
    while True:
        session_data = requests.get(session_url, headers=HEADERS).json()
        status = session_data["status"]
        logger.info(f"Session {session['session_id']}: {json.dumps(session_data)}")
        if status in ("exit", "error", "suspended") or session_data["status_detail"] == "waiting_for_user":
            # todo: how do we kill a session?
            break
        time.sleep(10)


if __name__ == "__main__":
    run()
