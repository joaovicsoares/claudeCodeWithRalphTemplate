from __future__ import annotations

import json
import subprocess
import threading
import uuid
from dataclasses import asdict
from pathlib import Path
from urllib import request

from fastapi import HTTPException, UploadFile

from app.core.config import LOCK_FILE, N8N_WEBHOOK_URL, PRD_PATH, REPO_ROOT, RUNTIME_DIR
from app.core.state import jobs, jobs_lock
from app.core.utils import trim_log, utc_now_iso
from app.schemas.jobs import JobState


def get_job(job_id: str) -> JobState:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job


def is_running() -> bool:
    with jobs_lock:
        return any(j.status == "running" for j in jobs.values())


async def create_job(prd_file: UploadFile, tool: str = "codex", max_iterations: int = 50) -> JobState:
    tool = tool.strip().lower()
    if tool not in {"amp", "claude", "codex"}:
        raise HTTPException(status_code=400, detail="tool must be amp, claude, or codex")
    if max_iterations < 1 or max_iterations > 500:
        raise HTTPException(status_code=400, detail="max_iterations must be between 1 and 500")

    if prd_file.filename and not prd_file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted")

    raw = await prd_file.read()
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")

    try:
        json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {exc}") from exc

    if LOCK_FILE.exists():
        raise HTTPException(status_code=409, detail="Ralph loop is already running")

    job_id = str(uuid.uuid4())
    log_file = str(RUNTIME_DIR / f"{job_id}.log")
    job = JobState(
        job_id=job_id,
        status="queued",
        tool=tool,
        max_iterations=max_iterations,
        created_at=utc_now_iso(),
        log_file=log_file,
    )

    with jobs_lock:
        jobs[job_id] = job

    PRD_PATH.write_bytes(raw)

    thread = threading.Thread(target=_run_loop_and_notify, args=(job_id,), daemon=True)
    thread.start()

    return job


def _run_loop_and_notify(job_id: str) -> None:
    with jobs_lock:
        job = jobs[job_id]
        job.status = "running"
        job.started_at = utc_now_iso()

    LOCK_FILE.write_text(job_id, encoding="utf-8")

    cmd = [
        "bash",
        "./scripts/ralph/ralph.sh",
        "--tool",
        job.tool,
        str(job.max_iterations),
    ]

    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    Path(job.log_file).write_text(output, encoding="utf-8")

    with jobs_lock:
        job.status = "completed" if proc.returncode == 0 else "failed"
        job.exit_code = proc.returncode
        job.finished_at = utc_now_iso()
        job.message = "Ralph loop ended successfully" if proc.returncode == 0 else "Ralph loop ended with error"

    try:
        _send_n8n_callback(job, output)
        with jobs_lock:
            job.webhook_status = "sent" if N8N_WEBHOOK_URL else "skipped"
    except Exception as exc:  # noqa: BLE001
        with jobs_lock:
            job.webhook_status = f"failed: {exc}"
    finally:
        LOCK_FILE.unlink(missing_ok=True)


def _send_n8n_callback(job: JobState, log_output: str) -> None:
    if not N8N_WEBHOOK_URL:
        return

    payload = {
        "event": "ralph_loop_finished",
        "job": asdict(job),
        "summary": {
            "status": job.status,
            "exit_code": job.exit_code,
            "finished_at": job.finished_at,
        },
        "log_tail": trim_log(log_output),
    }

    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        N8N_WEBHOOK_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    request.urlopen(req, timeout=20).read()
