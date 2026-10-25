"""
OmniAgent OS - Master FastAPI Application & Real-Time WebSocket Event Bus.

Integrates all 6 master modules into a unified REST & WebSocket API:
  - /ws/agent: Bi-directional streaming for agent thoughts, tool execution & Human-in-the-Loop approvals.
  - /ws/terminal: Interactive PTY terminal stream for integrated xterm.js.
  - REST endpoints for file explorer, window management, audio STT/TTS, screenshots, settings, and audit logs.
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agent.orchestrator import orchestrator
from config import (
    BACKEND_HOST, BACKEND_PORT, IS_WINDOWS, OS_NAME, PROJECT_ROOT, SCREENSHOT_DIR, WORKSPACE_ROOT
)
from gateway.provider_gateway import ALL_PROVIDERS, DEFAULT_MODELS, PROVIDER_LABELS, gateway
from gateway.vault import vault
from multimodal.coordinate_mapper import enable_dpi_awareness, list_monitors, primary_monitor_region
from multimodal.screen_capture import screen_capture
from multimodal.stt import stt
from multimodal.tts import tts
from multimodal.vad_listener import vad_listener
from os_control.file_tools import list_dir, read_file_content, search_workspace_code, write_file_content
from os_control.window_manager import find_windows, focus_window, list_windows
from safety.approval_bridge import approval_bridge
from safety.audit_logger import audit
from safety.kill_switch import kill_switch
from schemas import (
    ApprovalDecision, FileWriteRequest, FocusRequest, RiskAssessment, RiskLevel,
    SettingsUpdate, TTSRequest
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"
)
log = logging.getLogger("omniagent.server")


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    log.info("Starting OmniAgent OS Server on %s:%d ...", BACKEND_HOST, BACKEND_PORT)
    enable_dpi_awareness()

    loop = asyncio.get_running_loop()
    kill_switch.bind_loop(loop)
    kill_switch.start_hotkey_listener()

    yield

    # Teardown sequence
    log.info("Shutting down OmniAgent OS Server...")
    kill_switch.stop_hotkey_listener()
    tts.shutdown()
    vad_listener.stop()


app = FastAPI(title="OmniAgent OS Workspace", version="2.0.0", lifespan=lifespan)

# Allow local frontend Vite dev server or local browser bundle
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount screenshots directory for easy static image retrieval
if SCREENSHOT_DIR.exists():
    app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOT_DIR)), name="screenshots")

# Mount Autonomous YouTube Production Subsystem Router
from routers.youtube_router import router as youtube_router
app.include_router(youtube_router)

FRONTEND_DIST: Path = PROJECT_ROOT / "frontend" / "dist"


# --------------------------------------------------------------------------- #
# REST: System Status & Settings
# --------------------------------------------------------------------------- #
@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
async def get_system_status() -> dict[str, Any]:
    ollama_stat = await gateway.ollama_status()
    mon = primary_monitor_region()
    return {
        "status": "online",
        "os": OS_NAME,
        "is_windows": IS_WINDOWS,
        "workspace_root": str(WORKSPACE_ROOT),
        "primary_display": mon.as_dict(),
        "kill_switch_engaged": kill_switch.engaged,
        "kill_switch_hotkey_active": kill_switch.hotkey_active,
        "providers": {
            p: {
                "label": PROVIDER_LABELS.get(p, p),
                "configured": gateway.is_configured(p),
                "default_model": DEFAULT_MODELS.get(p, "")
            }
            for p in ALL_PROVIDERS
        },
        "ollama": ollama_stat,
        "stt": stt.status(),
        "tts": tts.status()
    }


@app.get("/api/settings")
async def get_settings() -> dict[str, Any]:
    return {
        "settings": vault.settings(),
        "key_status": vault.key_status(),
        "available_providers": [
            {"id": p, "name": PROVIDER_LABELS.get(p, p), "default_model": DEFAULT_MODELS.get(p, "")}
            for p in ALL_PROVIDERS
        ]
    }


@app.post("/api/settings")
async def update_settings(payload: SettingsUpdate) -> dict[str, Any]:
    if payload.api_keys:
        vault.set_keys(payload.api_keys)
    if payload.settings:
        vault.update_settings(payload.settings)
    audit.log("settings_updated", updated_keys=list(payload.api_keys.keys()), updated_settings=list(payload.settings.keys()))
    return {"ok": True, "settings": vault.settings(), "key_status": vault.key_status()}


# --------------------------------------------------------------------------- #
# REST: Safety & Emergency Controls
# --------------------------------------------------------------------------- #
@app.post("/api/killswitch/trigger")
async def trigger_killswitch() -> dict[str, Any]:
    kill_switch.trigger("UI Emergency Button")
    approval_bridge.deny_all("Kill switch engaged from UI")
    return {"ok": True, "kill_switch_engaged": True}


@app.post("/api/killswitch/reset")
async def reset_killswitch() -> dict[str, Any]:
    kill_switch.reset()
    return {"ok": True, "kill_switch_engaged": False}


@app.post("/api/approval")
async def resolve_approval(decision: ApprovalDecision) -> dict[str, Any]:
    ok = approval_bridge.resolve(decision.id, decision.approved, decided_by=decision.decided_by, note=decision.note)
    return {"ok": ok, "id": decision.id}


@app.get("/api/audit")
async def get_audit_log(limit: int = 150) -> list[dict[str, Any]]:
    return audit.tail(limit=limit)


# --------------------------------------------------------------------------- #
# REST: Workspace Filesystem
# --------------------------------------------------------------------------- #
@app.get("/api/files/tree")
async def get_file_tree(path: str = ".", recursive: bool = False) -> dict[str, Any]:
    return list_dir(path, recursive=recursive)


@app.get("/api/files/read")
async def get_file_content(path: str) -> dict[str, Any]:
    res = read_file_content(path)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Read error"))
    return res


@app.post("/api/files/write")
async def post_file_content(req: FileWriteRequest) -> dict[str, Any]:
    res = write_file_content(req.path, req.content)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("error", "Write error"))
    return res


@app.get("/api/files/search")
async def search_files(q: str) -> dict[str, Any]:
    return search_workspace_code(q)


# --------------------------------------------------------------------------- #
# REST: Window Manager & Desktop Automation
# --------------------------------------------------------------------------- #
@app.get("/api/windows")
async def get_windows() -> list[dict[str, Any]]:
    return [w.as_dict() for w in list_windows()]


@app.post("/api/windows/focus")
async def post_focus_window(req: FocusRequest) -> dict[str, Any]:
    target = req.target
    wins = find_windows(target)
    if not wins:
        raise HTTPException(status_code=404, detail=f"No window matching '{target}' found.")
    ok = focus_window(wins[0].hwnd)
    return {"ok": ok, "window": wins[0].as_dict()}


@app.get("/api/screenshot")
async def take_screenshot(grid: bool = False) -> dict[str, Any]:
    s = vault.settings()
    cap = screen_capture.capture(
        max_width=int(s.get("screenshot_max_width", 1366)),
        quality=int(s.get("screenshot_jpeg_quality", 70)),
        grid=grid
    )
    return {
        "ok": True,
        "filename": cap.file_name,
        "width": cap.width,
        "height": cap.height,
        "url": f"/screenshots/{cap.file_name}",
        "b64": cap.b64
    }


# --------------------------------------------------------------------------- #
# REST: Voice & Multimodal (STT / TTS)
# --------------------------------------------------------------------------- #
@app.post("/api/stt/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read()
    s = vault.settings()
    res = stt.transcribe_bytes(data, suffix=Path(file.filename or "audio.webm").suffix, model_name=s.get("whisper_model", "base"))
    return res


@app.post("/api/tts/speak")
async def synthesize_speech(req: TTSRequest) -> Response:
    s = vault.settings()
    rate = int(s.get("tts_rate", 185))
    try:
        wav_bytes = tts.synthesize(req.text, rate=rate)
        return Response(content=wav_bytes, media_type="audio/wav")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# --------------------------------------------------------------------------- #
# WebSocket: Real-time Agent Reasoning Bus (/ws/agent)
# --------------------------------------------------------------------------- #
@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    await websocket.accept()
    current_session_id = f"sess_{os.urandom(4).hex()}"
    active_task: Optional[asyncio.Task] = None

    async def emit(event: dict[str, Any]) -> None:
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            pass

    try:
        # Send initial connected greeting and current approvals
        await emit({"type": "connected", "data": {"session_id": current_session_id}})
        pending_approvals = approval_bridge.pending_for()
        for apr in pending_approvals:
            await emit({"type": "approval_request", "data": apr})

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            data = msg.get("data", {})

            if msg_type == "start_goal":
                goal = str(data.get("goal", "")).strip()
                if not goal:
                    continue

                img_b64 = data.get("image_b64")
                current_session_id = str(data.get("session_id") or current_session_id)

                if active_task and not active_task.done():
                    active_task.cancel()

                # Launch autonomous ReAct orchestrator loop
                active_task = asyncio.create_task(
                    orchestrator.run_loop(
                        session_id=current_session_id,
                        user_goal=goal,
                        emit=emit,
                        initial_image_b64=img_b64
                    )
                )

            elif msg_type == "abort_goal":
                if active_task and not active_task.done():
                    active_task.cancel()
                approval_bridge.deny_all("Aborted by user", decided_by="user")
                await emit({"type": "agent_cancelled", "data": {"session_id": current_session_id}})

            elif msg_type == "approval_decision":
                appr_id = str(data.get("id", ""))
                approved = bool(data.get("approved", False))
                note = str(data.get("note", ""))
                approval_bridge.resolve(appr_id, approved, decided_by="user", note=note)

            elif msg_type == "ping":
                await emit({"type": "pong", "ts": data.get("ts")})

    except WebSocketDisconnect:
        log.info("Agent WebSocket disconnected (session %s)", current_session_id)
        if active_task and not active_task.done():
            active_task.cancel()


# --------------------------------------------------------------------------- #
# WebSocket: Terminal PTY Multiplexer (/ws/terminal)
# --------------------------------------------------------------------------- #
@app.websocket("/ws/terminal")
async def websocket_terminal_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Determine command shell
    if IS_WINDOWS:
        cmd = ["powershell.exe", "-NoLogo"]
    else:
        cmd = ["/bin/bash"]

    try:
        # Create asynchronous subprocess with piped I/O
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(WORKSPACE_ROOT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        async def read_stream(stream, is_stderr: bool = False):
            try:
                while True:
                    line = await stream.read(1024)
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    await websocket.send_text(json.dumps({"type": "output", "data": text}))
            except Exception:
                pass

        stdout_task = asyncio.create_task(read_stream(proc.stdout))
        stderr_task = asyncio.create_task(read_stream(proc.stderr, is_stderr=True))

        try:
            while True:
                msg_raw = await websocket.receive_text()
                try:
                    payload = json.loads(msg_raw)
                    action = payload.get("type")
                    if action == "input" and proc.stdin:
                        proc.stdin.write(payload.get("data", "").encode("utf-8"))
                        await proc.stdin.drain()
                except Exception:
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            stdout_task.cancel()
            stderr_task.cancel()
            if proc.returncode is None:
                try:
                    proc.terminate()
                except Exception:
                    pass

    except Exception as exc:
        log.warning("Terminal spawn error: %s", exc)
        await websocket.close()


@app.get("/api/providers/gemini/models")
async def get_gemini_models() -> dict[str, Any]:
    from gateway.provider_gateway import AVAILABLE_GEMINI_MODELS
    return {"models": AVAILABLE_GEMINI_MODELS}


# Mount static frontend production build if available, with resilient index fallback
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

@app.get("/")
async def serve_index():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse(
        """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="3">
<title>OmniAgent OS — Initializing</title>
<style>
body { background: #0b0c10; color: #06b6d4; font-family: monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
.box { border: 1px solid #1e293b; padding: 30px; border-radius: 12px; background: #0f172a; text-align: center; box-shadow: 0 0 20px rgba(6,182,212,0.2); }
h1 { margin-top: 0; color: #38bdf8; }
.spinner { width: 32px; height: 32px; border: 3px solid rgba(6,182,212,0.2); border-top-color: #06b6d4; border-radius: 50%; animation: spin 1s linear infinite; margin: 20px auto; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<div class="box">
  <h1>⚡ OmniAgent OS Workspace</h1>
  <div class="spinner"></div>
  <p>Compiling native frontend bundle... Auto-refreshing in 3s</p>
  <p style="font-size:11px;color:#94a3b8;">Run 'run_setup.bat' or 'cmd /c npm run build' in frontend folder</p>
</div>
</body>
</html>"""
    )

if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=BACKEND_HOST, port=BACKEND_PORT, reload=False)
