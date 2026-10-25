"""
FastAPI Router for OmniAgent Autonomous YouTube Production Subsystem.

Provides REST and SSE endpoints for:
- Daily upload ledger and status monitoring
- Configuration and niche management
- On-demand pipeline triggering (with live SSE log streaming)
- Topic history inspection
- Rendered video playback preview
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

log = logging.getLogger("omniagent.api.youtube")

router = APIRouter(prefix="/api/youtube", tags=["YouTube Automator"])

# Paths
MODULE_ROOT = Path(__file__).resolve().parent.parent.parent / "modules" / "youtube_automator"
CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "youtube_config.json"
STORAGE_ROOT = MODULE_ROOT / "storage"
DB_PATH = STORAGE_ROOT / "db" / "youtube_agent.db"
RENDERED_DIR = STORAGE_ROOT / "rendered"

# Lazy-loaded database helper
def get_db():
    from modules.youtube_automator.core.db_manager import DatabaseManager
    return DatabaseManager(DB_PATH)


class ConfigUpdateRequest(BaseModel):
    niche: Optional[str] = None
    production_mode: Optional[str] = None
    llm_provider: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    ollama_model: Optional[str] = None
    pexels_api_key: Optional[str] = None
    privacy_status: Optional[str] = None
    auto_cleanup_cache: Optional[bool] = None


class TriggerPipelineRequest(BaseModel):
    force: bool = False
    dry_run: bool = False
    custom_topic: Optional[str] = None


# Global active job state for live SSE progress
active_job = {
    "is_running": False,
    "current_stage": "IDLE",
    "percent": 0,
    "detail": "Ready",
    "last_result": None
}


@router.get("/status")
async def get_youtube_status() -> Dict[str, Any]:
    """Retrieves current status, today's upload state, and pipeline health."""
    db = get_db()
    today_str = datetime.date.today().isoformat()
    today_upload = db.get_today_upload(today_str)
    all_uploads = db.get_all_uploads(limit=10)

    # Load config summary (safely mask secrets)
    config = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                raw_cfg = json.load(f)
                config = {
                    "niche": raw_cfg.get("niche", "AI Innovations & Breakthroughs"),
                    "production_mode": raw_cfg.get("production_mode", "solo"),
                    "llm_provider": raw_cfg.get("llm_provider", "gemini"),
                    "has_gemini_key": bool(raw_cfg.get("gemini_api_key")),
                    "has_openrouter_key": bool(raw_cfg.get("openrouter_api_key")),
                    "has_pexels_key": bool(raw_cfg.get("pexels_api_key")),
                    "has_oauth_token": (MODULE_ROOT / "token.json").exists(),
                    "privacy_status": raw_cfg.get("privacy_status", "public")
                }
        except Exception:
            pass

    return {
        "today_date": today_str,
        "today_completed": bool(today_upload and today_upload.get("status") == "COMPLETED"),
        "today_record": today_upload,
        "recent_uploads": all_uploads,
        "config_summary": config,
        "active_job": active_job
    }


@router.get("/config")
async def get_youtube_config() -> Dict[str, Any]:
    """Returns the full configuration with sensitive keys partially masked."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Mask API keys for security in UI
            masked = dict(cfg)
            for k in ["gemini_api_key", "openrouter_api_key", "pexels_api_key"]:
                val = masked.get(k, "")
                if val and len(val) > 8:
                    masked[k] = val[:4] + "..." + val[-4:]
            return masked
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_youtube_config(update: ConfigUpdateRequest) -> Dict[str, str]:
    """Updates configuration fields in config/youtube_config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    updates_dict = update.dict(exclude_unset=True)
    for k, v in updates_dict.items():
        if v is not None:
            # Don't overwrite with masked string
            if isinstance(v, str) and "..." in v:
                continue
            existing[k] = v

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    return {"status": "SUCCESS", "message": "YouTube Automator configuration updated."}


@router.get("/history")
async def get_upload_history(limit: int = 50) -> Dict[str, Any]:
    """Returns the daily uploads history ledger."""
    db = get_db()
    uploads = db.get_all_uploads(limit=limit)
    topics = db.get_recent_topics(limit=limit)
    return {"uploads": uploads, "topics": topics}


@router.get("/logs")
async def get_execution_logs(limit: int = 100) -> Dict[str, Any]:
    """Returns recent structured execution telemetry logs."""
    db = get_db()
    logs = db.get_recent_logs(limit=limit)
    return {"logs": logs}


@router.get("/niches")
async def get_recommended_niches() -> Dict[str, Any]:
    """Invokes AI niche consultation."""
    from modules.youtube_automator.setup_wizard import consult_ai_niches
    cfg = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    provider = cfg.get("llm_provider", "gemini")
    key = cfg.get("gemini_api_key") if provider == "gemini" else cfg.get("openrouter_api_key", "")
    niches = consult_ai_niches(provider, key or "")
    return {"niches": niches}


async def _execute_orchestrator_job(force: bool, dry_run: bool, custom_topic: Optional[str]):
    from modules.youtube_automator.orchestrator import MasterOrchestrator
    orchestrator = MasterOrchestrator()

    def on_progress(stage: str, percent: int, detail: str):
        active_job["current_stage"] = stage
        active_job["percent"] = percent
        active_job["detail"] = detail

    active_job["is_running"] = True
    active_job["current_stage"] = "STARTING"
    active_job["percent"] = 5
    active_job["detail"] = "Initializing autonomous pipeline..."

    try:
        result = await orchestrator.run_pipeline(
            force=force,
            dry_run=dry_run,
            custom_topic=custom_topic,
            progress_callback=on_progress
        )
        active_job["last_result"] = result
        active_job["detail"] = "Pipeline execution complete."
    except Exception as ex:
        active_job["detail"] = f"Failed: {ex}"
        active_job["last_result"] = {"status": "FAILED", "error": str(ex)}
        log.error(f"Pipeline job execution failed: {ex}")
    finally:
        active_job["is_running"] = False


@router.post("/run")
async def trigger_pipeline(
    req: TriggerPipelineRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Triggers autonomous Shorts production pipeline in the background."""
    if active_job["is_running"]:
        return {
            "status": "ALREADY_RUNNING",
            "message": "A production job is currently in progress.",
            "current_stage": active_job["current_stage"],
            "percent": active_job["percent"]
        }

    background_tasks.add_task(_execute_orchestrator_job, req.force, req.dry_run, req.custom_topic)
    return {
        "status": "STARTED",
        "message": "YouTube autonomous production pipeline initiated.",
        "force": req.force,
        "dry_run": req.dry_run
    }


@router.get("/stream")
async def stream_live_progress() -> StreamingResponse:
    """Server-Sent Events (SSE) endpoint for real-time UI pipeline updates."""
    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            data = json.dumps(active_job)
            yield f"data: {data}\n\n"
            if not active_job["is_running"] and active_job["percent"] in (0, 100):
                # Poll less frequently when idle
                await asyncio.sleep(2.0)
            else:
                await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/video/{filename}")
async def serve_rendered_video(filename: str):
    """Streams a rendered short MP4 for in-browser video playback."""
    file_path = RENDERED_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Rendered video not found")
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename
    )
