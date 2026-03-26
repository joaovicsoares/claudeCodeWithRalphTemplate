from dataclasses import asdict

from fastapi import APIRouter, File, Form, UploadFile

from app.services import ralph_service

router = APIRouter(prefix="/ralph", tags=["ralph"])


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    return asdict(ralph_service.get_job(job_id))


@router.post("/jobs")
async def create_job(
    prd_file: UploadFile = File(...),
    tool: str = Form("codex"),
    max_iterations: int = Form(50),
    target_repo_path: str = Form('.'),
) -> dict:
    job = await ralph_service.create_job(prd_file=prd_file, tool=tool, max_iterations=max_iterations, target_repo_path=target_repo_path)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "message": "Job accepted and started asynchronously",
    }
