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
_prompt_review_pr = (_prompts / "review_pr_prompt.txt").read_text()


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


def _log_resolution(output: str, title: str, pr_url: str) -> None:
    pr_number = pr_url.rstrip("/").split("/")[-1]
    output_lower = output.lower()
    if "merged" in output_lower:
        action = "Merged"
    elif "closed" in output_lower:
        action = "Closed"
    else:
        action = "Resolved"
    logger.info(f"{action} «{title}» in PR #{pr_number}")


def _review_existing_pr(task: Task) -> None:
    pr_url = task.notes
    logger.info(f"Reviewing PR: {pr_url}")
    session = create_session(_prompt_review_pr.format(pr_url=pr_url))
    logger.info(f"Session: {session['url']}")
    result = poll_until_complete(session)
    _log_resolution(result.get("structured_output", ""), task.title, pr_url)


def _create_and_review_pr(task: Task) -> None:
    session1 = create_session(_prompt_task.format(title=task.title, notes=task.notes or "", repo=REPO))
    logger.info(f"Session 1: {session1['url']}")
    result1 = poll_until_complete(session1)
    output1 = result1.get("structured_output", "")

    pr_match = PR_URL_PATTERN.search(output1)
    if not pr_match:
        logger.info(f"Devin declined to raise a PR: {output1}")
        return

    pr_url = pr_match.group(0)
    logger.info(f"PR raised: {pr_url}")

    session2 = create_session(_prompt_review.format(pr_url=pr_url))
    logger.info(f"Session 2: {session2['url']}")
    result2 = poll_until_complete(session2)
    _log_resolution(result2.get("structured_output", ""), task.title, pr_url)


def run_task(task_id: str) -> None:
    task = Task.model_validate_json(cache.get(f"task:{task_id}"))
    logger.info(f"Processing task {task.id}: {task.title!r}")

    if task.is_pull_request:
        _review_existing_pr(task)
    else:
        _create_and_review_pr(task)


if __name__ == "__main__":
    task_id = cache.lpop(TASK_QUEUE_NAME)
    if not task_id:
        logger.info("No tasks in queue")
        raise SystemExit(0)
    run_task(task_id)
