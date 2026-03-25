from fastapi import APIRouter

from app.core.config import N8N_WEBHOOK_URL
from app.core.utils import utc_now_iso
from app.services import ralph_service

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "running": ralph_service.is_running(),
        "n8n_configured": bool(N8N_WEBHOOK_URL),
        "time": utc_now_iso(),
    }
