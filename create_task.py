#!/usr/bin/env python3
import argparse
import time
import uuid
from typing import Optional

import redis

from persistence_settings import REDIS_HOST, REDIS_PORT, TASK_QUEUE_NAME
from task import Task

from log_config import logger


def create_task(title: str, worker: str, notes: Optional[str] = None) -> Task:
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        worker=worker,
        creation_time=int(time.time()),
        notes=notes,
    )
    cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    cache.set(f"task:{task.id}", task.model_dump_json())
    cache.rpush(TASK_QUEUE_NAME, task.id)
    return task


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a task to the Devin task queue")
    parser.add_argument("title", help="Short description of the task")
    parser.add_argument("worker", help="Worker script that will handle the task (e.g. peon1)")
    parser.add_argument("--notes", default=None, help="Optional additional notes")
    args = parser.parse_args()

    task = create_task(args.title, args.worker, args.notes)
    logger.info(f"Created task {task.id}: {task.title!r} → {task.worker}")
