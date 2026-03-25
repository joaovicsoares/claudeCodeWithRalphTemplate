from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[3]
RALPH_DIR = REPO_ROOT / "scripts" / "ralph"
PRD_PATH = RALPH_DIR / "prd.json"
RUNTIME_DIR = RALPH_DIR / "runtime"
LOCK_FILE = RUNTIME_DIR / ".ralph.lock"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "").strip()

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
