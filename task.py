import time
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str
    title: str
    creation_time: float = Field(default_factory=time.time)
    worker: Optional[str] = None
    status: Literal["waiting", "in progress", "finished"] = "waiting"
    notes: Optional[str] = None
    is_pull_request: bool = False
