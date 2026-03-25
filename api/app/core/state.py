import threading

from app.schemas.jobs import JobState

jobs: dict[str, JobState] = {}
jobs_lock = threading.Lock()
