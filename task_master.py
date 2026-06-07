import os
import threading
import time

import redis

from persistence_settings import REDIS_HOST, REDIS_PORT, TASK_QUEUE_NAME
from task_worker import run_task

from log_config import logger

TASK_MASTER_SLEEP_PERIOD_SECONDS = int(os.environ.get("TASK_MASTER_SLEEP_PERIOD_SECONDS", 10))

cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def run():
    logger.info("Task master started")
    while True:
        dispatched = 0
        while task_id := cache.lpop(TASK_QUEUE_NAME):
            t = threading.Thread(target=run_task, args=(task_id,), name=f"task-{task_id[:8]}", daemon=True)
            t.start()
            logger.info(f"Dispatched task {task_id} → thread {t.name}")
            dispatched += 1
        if not dispatched:
            time.sleep(TASK_MASTER_SLEEP_PERIOD_SECONDS)


if __name__ == "__main__":
    run()
