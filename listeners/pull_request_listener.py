import os
import time

import redis
import requests

from create_task import create_task
from log_config import logger
from persistence_settings import REDIS_HOST, REDIS_PORT

PULL_REQUEST_LISTENER_SLEEP_PERIOD_SECONDS = int(
    os.environ.get("PULL_REQUEST_LISTENER_SLEEP_PERIOD_SECONDS", 300)
)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = "owen9825/superset"
GITHUB_API = "https://api.github.com"
SEEN_PRS_KEY = "pull_request_listener:seen_prs"

github_headers = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    github_headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def fetch_open_prs() -> list:
    resp = requests.get(
        f"{GITHUB_API}/repos/{REPO}/pulls",
        headers=github_headers,
        params={"state": "open", "per_page": 100},
    )
    resp.raise_for_status()
    return resp.json()


def sync_pull_requests() -> int:
    prs = fetch_open_prs()
    count = 0
    for pr in prs:
        pr_number = str(pr["number"])
        if cache.sismember(SEEN_PRS_KEY, pr_number):
            continue
        create_task(
            title=pr["title"],
            worker="task_worker",
            notes=pr["html_url"],
            is_pull_request=True,
        )
        cache.sadd(SEEN_PRS_KEY, pr_number)
        logger.info(f"Queued PR #{pr_number}: {pr['title']!r}")
        count += 1
    return count


if __name__ == "__main__":
    while True:
        logger.info("Checking for new pull requests…")
        count = sync_pull_requests()
        logger.info(f"Queued {count} new PR(s)")
        time.sleep(PULL_REQUEST_LISTENER_SLEEP_PERIOD_SECONDS)
