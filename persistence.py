from typing import Optional

import redis

from persistence_settings import REDIS_HOST, REDIS_PORT, get_previous_execution_time_key

_cache = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_last_execution_time(module_name: str) -> Optional[int]:
    value = _cache.get(get_previous_execution_time_key(module_name))
    return int(value) if value is not None else None


def set_last_execution_time(module_name: str, unix_time: int) -> None:
    _cache.set(get_previous_execution_time_key(module_name), unix_time)
