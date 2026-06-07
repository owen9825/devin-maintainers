import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
from create_task import create_task
from log_config import logger

API_KEY = os.environ["DEVIN_API_KEY"]
ORG_ID = os.environ["DEVIN_ORG_ID"]
BASE = "https://api.devin.ai/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
SELF_ID = os.environ["SELF_USER_ID"]

PROMPT_FILE = Path(__file__).parent.parent / "prompts" / "mock_nvd_listening_prompt.txt"

# Set DEVIN_ENTERPRISE=true if your account has the ViewAccountSessions enterprise permission.
# docs.devin.ai/api-reference/v3/sessions/get-enterprise-session-messages.md
DEVIN_ENTERPRISE = os.environ.get("DEVIN_ENTERPRISE", "false").lower() == "true"


def get_last_devin_message(session_id: str) -> str:
    # devin_id must have the "devin-" prefix per the API spec.
    devin_id = session_id if session_id.startswith("devin-") else f"devin-{session_id}"

    # Attempt 1: enterprise messages endpoint (paginated conversation history).
    # docs.devin.ai/api-reference/v3/sessions/get-enterprise-session-messages.md
    # Requires ViewAccountSessions at enterprise level.
    if DEVIN_ENTERPRISE:
        resp = requests.get(
            f"{BASE}/enterprise/sessions/{devin_id}/messages",
            headers=HEADERS,
            params={"org_id": ORG_ID},
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        devin_messages = [m for m in items if m["source"] == "devin"]
        return devin_messages[-1]["message"] if devin_messages else ""

    # Attempt 2: v1 session endpoint (includes messages[] for non-enterprise accounts).
    # docs.devin.ai/api-reference/v1/sessions/retrieve-details-about-an-existing-session.md
    devin_id = session_id if session_id.startswith("devin-") else f"devin-{session_id}"
    resp = requests.get(
        f"https://api.devin.ai/v1/sessions/{devin_id}",
        headers=HEADERS,
    )
    if resp.status_code == 200:
        messages = resp.json().get("messages", [])
        devin_messages = [m for m in messages if m.get("origin") == "devin" or m.get("type") == "devin_message"]
        if devin_messages:
            return devin_messages[-1]["message"]
        logger.info(f"v1 returned {len(messages)} message(s) but none from Devin: {json.dumps(messages)}")
    else:
        logger.info(f"v1 session endpoint returned {resp.status_code}: {resp.text}")

    # Attempt 3: structured_output from the org-scoped session GET (accessible to all accounts,
    # but only populated when Devin produces validated output — null for conversational sessions).
    # docs.devin.ai/api-reference/v3/sessions/get-organizations-session.md
    resp = requests.get(
        f"{BASE}/organizations/{ORG_ID}/sessions/{session_id}",
        headers=HEADERS,
    )
    resp.raise_for_status()
    output = resp.json().get("structured_output") or ""
    logger.info(f"structured_output: {output!r}")
    return output


def terminate_session(session_id: str) -> None:
    requests.delete(
        f"{BASE}/organizations/{ORG_ID}/sessions/{session_id}",
        headers=HEADERS,
        params={"archive": "true"},
    ).raise_for_status()

def is_session_in_ending_state(session_data):
    status = session_data["status"]
    return status in ("exit", "error", "suspended") or session_data["status_detail"] == "waiting_for_user"

def start_session() -> dict:
    me = requests.get(f"{BASE}/self", headers=HEADERS)
    me.raise_for_status()
    data = me.json()
    logger.info(f"Authenticated as: {data.get('service_user_name') or data.get('user_name')}")

    prompt = PROMPT_FILE.read_text()  # "come up with a ridiculous vulnerability"
    session = requests.post(
        f"{BASE}/organizations/{ORG_ID}/sessions",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"prompt": prompt, "create_as_user_id": SELF_ID},
    ).json()
    logger.info(f"Session: {session['url']}")
    return session


def poll_session(session_id: str) -> dict:
    session_url = f"{BASE}/organizations/{ORG_ID}/sessions/{session_id}"
    session_data = {}
    while True:
        session_data = requests.get(session_url, headers=HEADERS).json()
        logger.info(f"Session {session_id}: {json.dumps(session_data)}")
        if is_session_in_ending_state(session_data):
            break
        time.sleep(10)
    return session_data


def extract_nvd_data(session_id: str) -> dict:
    output_text = get_last_devin_message(session_id)
    if not output_text:
        logger.warning(f"No messages found for session {session_id}")
        raise SystemExit("Could not find any Devin messages in session")

    # Find a triple-backtick code block at the end of the message containing the JSON
    for block in reversed(re.findall(r"```(?:\w+)?\s*(.*?)\s*```", output_text, re.DOTALL)):
        try:
            candidate = json.loads(block)
            if "title" in candidate and "notes" in candidate:
                return candidate
        except json.JSONDecodeError:
            continue

    logger.info(f"Session output: {output_text}")
    raise SystemExit("Could not find a JSON object with 'title' and 'notes' in session output")


def enqueue_vulnerability(nvd_data: dict) -> None:
    task = create_task(
        title=nvd_data["title"],
        worker="nvd_listener",
        notes=nvd_data["notes"],
    )
    logger.info(f"Task added to queue: {task.id}")


def run():
    session = start_session()
    session_data = poll_session(session["session_id"])
    if session_data["status"] != "exit":
        terminate_session(session["session_id"])
        raise SystemExit(f"Session ended with status: {session_data['status']} / {session_data.get('status_detail')}")
    nvd_data = extract_nvd_data(session["session_id"])
    logger.info(f"Vulnerability title: {nvd_data['title']}")
    enqueue_vulnerability(nvd_data)


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["messages", session_id]:
            msg = get_last_devin_message(session_id)
            print(msg) if msg else logger.warning("No message content found")
        case ["extract", session_id]:
            print(json.dumps(extract_nvd_data(session_id), indent=2))
        case ["enqueue", session_id]:
            enqueue_vulnerability(extract_nvd_data(session_id))
        case []:
            run()
        case _:
            raise SystemExit("Usage: mock_nvd_listener [messages|extract|enqueue <session_id>]")
