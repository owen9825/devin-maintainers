import json
import os
import re
import time
from pathlib import Path

import redis
import requests

from persistence_settings import REDIS_HOST, REDIS_PORT, TASK_QUEUE_NAME
from task import Task

from log_config import logger

API_KEY = os.environ["DEVIN_API_KEY"]
ORG_ID = os.environ["DEVIN_ORG_ID"]
BASE = "https://api.devin.ai/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
SELF_ID = os.environ["SELF_USER_ID"]
REPO = "https://github.com/owen9825/superset"

PR_URL_PATTERN = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+")

cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

_prompts = Path(__file__).parent / "prompts"
_prompt_task = (_prompts / "start_working_task_prompt.txt").read_text()
_prompt_review = (_prompts / "task_pr_prompt.txt").read_text()


def create_session(prompt: str) -> dict:
    return requests.post(
        f"{BASE}/organizations/{ORG_ID}/sessions",
        headers={**HEADERS, "Content-Type": "application/json"},
        json={"prompt": prompt, "create_as_user_id": SELF_ID},
    ).json()


def poll_until_complete(session: dict) -> dict:
    session_url = f"{BASE}/organizations/{ORG_ID}/sessions/{session['session_id']}"
    while True:
        response = requests.get(session_url, headers=HEADERS).json()
        status = response["status"]
        logger.info(f"Session {session['session_id']}: {json.dumps(response)}")
        if status in ("exit", "error", "suspended") or response["status_detail"] == "waiting_for_user":
            # todo: how do we kill a session?
            return response
        time.sleep(10)


def run_task(task_id: str) -> None:
    task = Task.model_validate_json(cache.get(f"task:{task_id}"))
    logger.info(f"Processing task {task.id}: {task.title!r}")

    # Session 1: ask Devin to carry out the task
    session1 = create_session(_prompt_task.format(title=task.title, notes=task.notes or "", repo=REPO))
    logger.info(f"Session 1: {session1['url']}")
    result1 = poll_until_complete(session1)
    output1 = result1.get("structured_output", "")

    pr_match = PR_URL_PATTERN.search(output1)
    if not pr_match:
        logger.info(f"Devin declined to raise a PR: {output1}")
        return

    pr_url = pr_match.group(0)
    pr_number = pr_url.rstrip("/").split("/")[-1]
    logger.info(f"PR raised: {pr_url}")

    # Session 2: ask Devin to review and action the PR
    session2 = create_session(_prompt_review.format(pr_url=pr_url))
    logger.info(f"Session 2: {session2['url']}")
    result2 = poll_until_complete(session2)
    output2 = result2.get("structured_output", "").lower()

    if "merged" in output2:
        action = "Merged"
    elif "closed" in output2:
        action = "Closed"
    else:
        action = "Resolved"

    logger.info(f"{action} «{task.title}» in PR #{pr_number}")


if __name__ == "__main__":
    task_id = cache.lpop(TASK_QUEUE_NAME)
    if not task_id:
        logger.info("No tasks in queue")
        raise SystemExit(0)
    run_task(task_id)
