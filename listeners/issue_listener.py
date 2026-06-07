import json
import os
import time

import redis
import requests

from log_config import logger

ISSUE_LISTENER_SLEEP_PERIOD_SECONDS = int(
    os.environ.get("ISSUE_LISTENER_SLEEP_PERIOD_SECONDS", 300)
)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

REPO = "apache/superset"
GITHUB_API = "https://api.github.com"
LAST_FETCH_KEY = "issue_listener:last_fetch"

headers = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def fetch_issues(since=None):
    page = 1
    while True:
        params = {"state": "all", "per_page": 100, "page": page}
        if since:
            params["since"] = since
        resp = requests.get(
            f"{GITHUB_API}/repos/{REPO}/issues",
            headers=headers,
            params=params,
        )
        resp.raise_for_status()
        issues = resp.json()
        if not issues:
            break
        yield from issues
        page += 1


def sync_issues() -> int:
    since = cache.get(LAST_FETCH_KEY)
    fetch_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    count = 0
    for issue in fetch_issues(since=since):
        cache.set(issue["html_url"], json.dumps(issue))
        count += 1
    cache.set(LAST_FETCH_KEY, fetch_time)
    logger.info(f"Synced {count} issues (since={since or 'beginning'})")
    return count


if __name__ == "__main__":
    while True:
        sync_issues()
        time.sleep(ISSUE_LISTENER_SLEEP_PERIOD_SECONDS)
