import os
import time
import requests

from persistence_settings import TASK_QUEUE_NAME

from log_config import logger

API_KEY = os.environ["DEVIN_API_KEY"]
ORG_ID = os.environ["DEVIN_ORG_ID"]
BASE = "https://api.devin.ai/v3"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
QUEUE_OBSERVER_SLEEP_PERIOD_SECONDS = 300


def get_tasks() -> list:
    return requests.get(
        f"{BASE}/organizations/{ORG_ID}/queues/{TASK_QUEUE_NAME}/tasks",
        headers=HEADERS,
    ).json()


if __name__ == "__main__":
    while True:
        tasks = get_tasks()
        names = [t["name"] for t in tasks]
        logger.info(f"There are {len(names)} tasks waiting in the queue:")
        for name in names:
            logger.info(f"  {name}")
        time.sleep(QUEUE_OBSERVER_SLEEP_PERIOD_SECONDS)
