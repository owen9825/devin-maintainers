#!/usr/bin/env python3
import argparse
import time
import uuid
from typing import Optional

import redis

from persistence_settings import REDIS_HOST, REDIS_PORT, TASK_QUEUE_NAME
from task import Task

from log_config import logger


def create_task(
    title: str,
    notes: Optional[str] = None,
    is_pull_request: bool = False,
) -> Task:
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        worker=None,
        creation_time=int(time.time()),
        notes=notes,
        is_pull_request=is_pull_request,
    )
    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    cache.set(f"task:{task.id}", task.model_dump_json())
    cache.rpush(TASK_QUEUE_NAME, task.id)
    return task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a task to the Devin task queue")
    parser.add_argument("--title", required=True, help="Short description of the task")
    parser.add_argument("--notes", default=None, help="Optional additional notes")
    args = parser.parse_args()

    task = create_task(args.title, args.notes)
    logger.info(f"Created task {task.id}: {task.title!r} → {task.worker}")
