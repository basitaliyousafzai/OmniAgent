"""
OmniAgent OS - Sovereign Native Desktop Application Launcher.

Runs OmniAgent OS as a 100% native standalone desktop application.
No browser tabs, no web URLs, no browser chrome.
Direct hardware-accelerated desktop window with sovereign isolation.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

import uvicorn

from backend.config import BACKEND_HOST, BACKEND_PORT


def is_backend_alive() -> bool:
    """Checks if the FastAPI backend is already running and responding."""
    try:
        url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/api/health"
        req = urllib.request.Request(url, headers={"User-Agent": "OmniAgent-Desktop"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def start_backend():
    """Starts the FastAPI backend in a background worker thread."""
    try:
        uvicorn.run("app:app", host=BACKEND_HOST, port=BACKEND_PORT, log_level="warning")
    except Exception as e:
        print(f"[!] Backend server notice: {e}")


def find_browser_app_bin() -> tuple[str | None, str]:
    """Finds Microsoft Edge or Google Chrome executable for native standalone app window."""
    edge_candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in edge_candidates:
        if os.path.exists(p):
            return p, "Edge"

    chrome_candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]
    for p in chrome_candidates:
        if os.path.exists(p):
            return p, "Chrome"

    which_edge = shutil.which("msedge")
    if which_edge:
        return which_edge, "Edge"

    which_chrome = shutil.which("chrome")
    if which_chrome:
        return which_chrome, "Chrome"

    return None, "None"


def launch_native_app_window(url: str):
    """
    Launches OmniAgent in true standalone desktop app window mode
    (Zero tabs, zero address bar, zero browser chrome, isolated app profile).
    """
    import tempfile

    browser_bin, browser_name = find_browser_app_bin()
    # Unique non-colliding profile prevents ProcessSingleton lock collisions
    temp_profile = tempfile.mkdtemp(prefix=f"omniagent_{browser_name.lower()}_")

    if browser_bin:
        args = [
            browser_bin,
            f"--app={url}",
            f"--user-data-dir={temp_profile}",
            "--window-size=1520,960",
            "--window-position=50,50",
            "--disable-features=Translate,ChromeWhatsNewUI",
            "--no-first-run",
            "--no-default-browser-check",
            "--app-name=OmniAgent OS"
        ]
        print(f"[*] Launching sovereign desktop application window via {browser_name} Runtime...")
        try:
            proc = subprocess.Popen(args)
            proc.wait()
        except KeyboardInterrupt:
            print("\n[*] Exiting OmniAgent OS...")
        finally:
            try:
                shutil.rmtree(temp_profile, ignore_errors=True)
            except Exception:
                pass
    else:
        # Fallback to pywebview if neither Edge nor Chrome is found
        try:
            import webview
            storage = str(ROOT_DIR / ".omniagent_data" / "webview_cache")
            window = webview.create_window(
                title="OmniAgent OS — Autonomous Multimodal Desktop Agent",
                url=url,
                width=1520,
                height=960,
                min_size=(1024, 700),
                resizable=True,
                background_color="#0b0c10"
            )
            webview.start(storage_path=storage, debug=False)
        except Exception as err:
            print(f"[!] Fallback window error: {err}")


def main():
    print("=" * 70)
    print("      OMNIAGENT OS: AUTONOMOUS MULTIMODAL DESKTOP AGENT")
    print("   [Mode: Sovereign Native Desktop App | AI Engine: Google Gemini]")
    print("=" * 70)

    # 1. Start backend if not already listening
    if not is_backend_alive():
        print("[*] Initializing OmniAgent OS core backend...")
        backend_thread = threading.Thread(target=start_backend, daemon=True, name="OmniAgent-Backend")
        backend_thread.start()

        # Wait up to 10 seconds for backend to become ready
        for _ in range(20):
            if is_backend_alive():
                break
            time.sleep(0.5)
    else:
        print("[*] OmniAgent OS backend is active and healthy.")

    url = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    launch_native_app_window(url)


if __name__ == "__main__":
    main()

