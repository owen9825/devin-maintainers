import os

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
TASK_QUEUE_NAME = "devin-tasks"


def get_previous_execution_time_key(module_name: str) -> str:
    return f"{module_name}_execution"
