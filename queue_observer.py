import time

import redis

from log_config import logger
from persistence_settings import REDIS_HOST, REDIS_PORT, TASK_QUEUE_NAME
from task import Task

QUEUE_OBSERVER_SLEEP_PERIOD_SECONDS = 300

cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_tasks() -> list[Task]:
    task_ids = cache.lrange(TASK_QUEUE_NAME, 0, -1)
    tasks = []
    for task_id in task_ids:
        task_data = cache.get(f"task:{task_id}")
        if task_data:
            tasks.append(Task.model_validate_json(task_data))
    return tasks


if __name__ == "__main__":
    while True:
        tasks = get_tasks()
        logger.info(f"There are {len(tasks)} tasks waiting in the queue:")
        for task in tasks:
            logger.info(f"  {task.id}: {task.title}")
        time.sleep(QUEUE_OBSERVER_SLEEP_PERIOD_SECONDS)
