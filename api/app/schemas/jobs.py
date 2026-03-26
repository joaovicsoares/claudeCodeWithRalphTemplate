from dataclasses import dataclass


@dataclass
class JobState:
    job_id: str
    status: str
    tool: str
    max_iterations: int
    target_repo_path: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    message: str | None = None
    log_file: str | None = None
    webhook_status: str | None = None
