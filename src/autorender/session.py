"""Auto render session management."""
import time
import logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class RenderJob:
    """A single render job."""
    draft_name: str
    draft_path: str
    status: str = "pending"  # pending, rendering, done, error
    start_time: float = 0
    end_time: float = 0
    error_msg: str = ""


@dataclass
class RenderSession:
    """Tracks the state of a batch render session."""
    jobs: list = field(default_factory=list)
    status: SessionStatus = SessionStatus.IDLE
    current_index: int = 0
    total_completed: int = 0
    total_errors: int = 0
    start_time: float = 0

    @property
    def current_job(self) -> Optional[RenderJob]:
        if 0 <= self.current_index < len(self.jobs):
            return self.jobs[self.current_index]
        return None

    @property
    def progress_percent(self) -> float:
        if not self.jobs:
            return 0
        return (self.total_completed / len(self.jobs)) * 100

    @property
    def elapsed_time(self) -> float:
        if self.start_time == 0:
            return 0
        return time.time() - self.start_time

    def add_job(self, name: str, path: str):
        self.jobs.append(RenderJob(draft_name=name, draft_path=path))

    def start(self):
        self.status = SessionStatus.RUNNING
        self.start_time = time.time()
        self.current_index = 0
        if self.jobs:
            self.jobs[0].status = "rendering"
            self.jobs[0].start_time = time.time()

    def complete_current(self):
        job = self.current_job
        if job:
            job.status = "done"
            job.end_time = time.time()
            self.total_completed += 1

        self.current_index += 1
        if self.current_index >= len(self.jobs):
            self.status = SessionStatus.COMPLETED
        else:
            next_job = self.jobs[self.current_index]
            next_job.status = "rendering"
            next_job.start_time = time.time()

    def error_current(self, msg: str):
        job = self.current_job
        if job:
            job.status = "error"
            job.error_msg = msg
            job.end_time = time.time()
            self.total_errors += 1

        self.current_index += 1
        if self.current_index >= len(self.jobs):
            self.status = SessionStatus.COMPLETED

    def stop(self):
        self.status = SessionStatus.IDLE
