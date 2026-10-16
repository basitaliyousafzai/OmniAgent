"""
Sub-Module 3.2 / 5: Universal Application Controller & Desktop Recipes.

Provides high-level semantic workflows for controlling external desktop software:
  1. Visual Studio:
     - Open solution (.sln) or file.
     - Trigger Solution Build (Ctrl+Shift+B).
     - Start Debugging (F5) / Stop Debugging (Shift+F5).
     - Focus Error List (Ctrl+\, E).
  2. SQL Server Management Studio (SSMS) / DBeaver / Azure Data Studio:
     - Focus or launch SSMS.
     - Open new query window (Ctrl+N).
     - Paste SQL query and Execute (F5 or Ctrl+E).
     - Capture execution status.
  3. Web Browsers (Chrome, Edge, Firefox):
     - Launch URL, reload page (Ctrl+R), open DevTools (F12).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from os_control.gui_controller import gui_controller
from os_control.window_manager import find_windows, focus_window, launch_or_focus

log = logging.getLogger("omniagent.app_orchestrator")


class AppOrchestrator:
    # ----------------------------------------------------------------------- #
    # Visual Studio Recipes
    # ----------------------------------------------------------------------- #
    def vs_build_solution(self) -> dict[str, Any]:
        """Focuses Visual Studio and triggers Ctrl+Shift+B to build the solution."""
        wins = find_windows("devenv")
        if not wins:
            return {"ok": False, "error": "Visual Studio (devenv) is not currently running."}

        focus_window(wins[0].hwnd)
        time.sleep(0.3)
        res = gui_controller.send_hotkey(["ctrl", "shift", "b"])
        return {
            "ok": True,
            "action": "visual_studio_build_solution",
            "hotkey": "Ctrl+Shift+B",
            "window": wins[0].title
        }

    def vs_start_debugging(self) -> dict[str, Any]:
        """Focuses Visual Studio and starts debugging with F5."""
        wins = find_windows("devenv")
        if not wins:
            return {"ok": False, "error": "Visual Studio is not running."}

        focus_window(wins[0].hwnd)
        time.sleep(0.3)
        gui_controller.send_hotkey(["f5"])
        return {"ok": True, "action": "visual_studio_start_debugging", "hotkey": "F5"}

    def vs_stop_debugging(self) -> dict[str, Any]:
        """Focuses Visual Studio and stops debugging with Shift+F5."""
        wins = find_windows("devenv")
        if not wins:
            return {"ok": False, "error": "Visual Studio is not running."}

        focus_window(wins[0].hwnd)
        time.sleep(0.3)
        gui_controller.send_hotkey(["shift", "f5"])
        return {"ok": True, "action": "visual_studio_stop_debugging", "hotkey": "Shift+F5"}

    def vs_open_error_list(self) -> dict[str, Any]:
        """Brings up the Visual Studio Error List window using chord Ctrl+\, E."""
        wins = find_windows("devenv")
        if not wins:
            return {"ok": False, "error": "Visual Studio is not running."}

        focus_window(wins[0].hwnd)
        time.sleep(0.3)
        # Visual Studio chords: Ctrl+\ followed by E
        gui_controller.send_hotkey(["ctrl", "\\"])
        time.sleep(0.1)
        gui_controller.press_key("e")
        return {"ok": True, "action": "visual_studio_open_error_list"}

    # ----------------------------------------------------------------------- #
    # SQL Server Management Studio (SSMS) Recipes
    # ----------------------------------------------------------------------- #
    def ssms_new_query(self) -> dict[str, Any]:
        """Focuses SSMS and opens a new query tab (Ctrl+N)."""
        wins = find_windows("ssms")
        if not wins:
            # Try launching or focusing
            res = launch_or_focus("ssms")
            if not res.get("focused"):
                return {"ok": False, "error": "SSMS is not running and could not be focused."}

        wins = find_windows("ssms")
        if wins:
            focus_window(wins[0].hwnd)
            time.sleep(0.3)
            gui_controller.send_hotkey(["ctrl", "n"])
            time.sleep(0.5)
            return {"ok": True, "action": "ssms_new_query", "hotkey": "Ctrl+N"}
        return {"ok": False, "error": "Could not locate SSMS window."}

    def ssms_execute_query(self, sql_query: Optional[str] = None) -> dict[str, Any]:
        """
        Focuses SSMS. If sql_query is provided, pastes it into the active query
        editor, then presses F5 to execute.
        """
        wins = find_windows("ssms")
        if not wins:
            return {"ok": False, "error": "SQL Server Management Studio (SSMS) is not running."}

        focus_window(wins[0].hwnd)
        time.sleep(0.3)

        if sql_query:
            # Paste query into editor
            gui_controller.type_string(sql_query, press_enter=True)
            time.sleep(0.3)

        # F5 executes query in SSMS
        gui_controller.send_hotkey(["f5"])
        time.sleep(0.5)
        return {
            "ok": True,
            "action": "ssms_execute_query",
            "hotkey": "F5",
            "query_length": len(sql_query) if sql_query else 0
        }

    # ----------------------------------------------------------------------- #
    # Browser Recipes
    # ----------------------------------------------------------------------- #
    def browser_open_url(self, url: str, browser: str = "chrome") -> dict[str, Any]:
        """Launches or brings browser to foreground and navigates to URL."""
        res = launch_or_focus(browser, [url])
        return {"ok": True, "action": "browser_open_url", "url": url, "result": res}

    def browser_reload(self, browser: str = "chrome") -> dict[str, Any]:
        wins = find_windows(browser)
        if not wins:
            return {"ok": False, "error": f"{browser} is not running."}

        focus_window(wins[0].hwnd)
        time.sleep(0.2)
        gui_controller.send_hotkey(["ctrl", "r"])
        return {"ok": True, "action": "browser_reload"}

    # ----------------------------------------------------------------------- #
    # Generic Dispatcher
    # ----------------------------------------------------------------------- #
    def dispatch_action(self, target_app: str, action: str, argument: str = "") -> dict[str, Any]:
        """
        High-level dispatcher for desktop applications.
        """
        app = target_app.lower().strip()
        act = action.lower().strip()

        if "visual studio" in app or "devenv" in app or app == "vs":
            if act in ("build", "compile"):
                return self.vs_build_solution()
            if act in ("debug", "run", "start"):
                return self.vs_start_debugging()
            if act in ("stop", "abort"):
                return self.vs_stop_debugging()
            if act in ("errors", "error_list"):
                return self.vs_open_error_list()

        if "ssms" in app or "sql" in app or "management studio" in app:
            if act in ("new_query", "new_tab"):
                return self.ssms_new_query()
            if act in ("run_query", "execute", "paste_and_run"):
                return self.ssms_execute_query(argument)

        if any(b in app for b in ("chrome", "edge", "firefox", "browser")):
            if act in ("open", "navigate", "url"):
                return self.browser_open_url(argument, browser=app)
            if act in ("reload", "refresh"):
                return self.browser_reload(browser=app)

        # Fallback: focus app and type or send key
        res = launch_or_focus(target_app)
        if act == "type":
            gui_controller.type_string(argument)
            return {"ok": True, "action": "generic_type", "target": target_app}

        return {"ok": False, "error": f"Unknown app action combination: {target_app} -> {action}"}


app_orchestrator = AppOrchestrator()
