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
    def _find_ssms_dialog(self) -> Optional[Any]:
        """Finds any active 'Connect to Server' dialog belonging to SSMS."""
        from os_control.window_manager import list_windows
        for w in list_windows():
            if "connect to server" in w.title.lower():
                return w
        return None

    def _find_ssms_main_window(self) -> Optional[Any]:
        """Finds the main SSMS workspace window (ignoring modal connect dialogs)."""
        from os_control.window_manager import list_windows
        for w in list_windows():
            if ("ssms" in w.process_name.lower() or "sql server management studio" in w.title.lower()) and "connect to server" not in w.title.lower():
                return w
        return None

    def ssms_connect_default(self) -> dict[str, Any]:
        """
        Connects SSMS to the default server.
        If the modal 'Connect to Server' dialog is visible, focuses it and sends Enter
        (or clicks Connect) to establish the database engine connection.
        Waits until the connection is established and the main IDE window is ready.
        """
        dialog = self._find_ssms_dialog()
        if not dialog:
            # If SSMS is not open at all, launch or focus it
            wins = find_windows("ssms")
            if not wins:
                res = launch_or_focus("ssms")
                if not res.get("focused") and not res.get("reused_existing_instance"):
                    time.sleep(2.0)
            # Re-check for dialog after launch
            for _ in range(10):
                dialog = self._find_ssms_dialog()
                if dialog:
                    break
                time.sleep(0.5)

        if dialog:
            log.info("Focusing SSMS 'Connect to Server' dialog (hwnd=%s)...", dialog.hwnd)
            focus_window(dialog.hwnd)
            time.sleep(0.4)
            # Enter triggers the default 'Connect' button with existing server name
            log.info("Sending ENTER to connect to default SQL Server instance...")
            gui_controller.send_hotkey(["enter"])

            # Wait for modal dialog to dismiss (connection established)
            for _ in range(15):
                time.sleep(0.5)
                if not self._find_ssms_dialog():
                    log.info("SSMS 'Connect to Server' dialog dismissed. Connected successfully.")
                    break
            time.sleep(0.8)

        # Bring main SSMS window to foreground
        main_win = self._find_ssms_main_window()
        if main_win:
            focus_window(main_win.hwnd)
            time.sleep(0.4)
            return {"ok": True, "action": "ssms_connect_default", "window": main_win.title}

        return {"ok": True, "action": "ssms_connect_default", "note": "Connection command sent."}

    def ssms_new_query(self) -> dict[str, Any]:
        """
        Ensures SSMS is connected to default server, brings main window to front,
        and opens a fresh SQL Query editor tab (Ctrl+N).
        """
        # 1. First ensure any 'Connect to Server' dialog is connected
        self.ssms_connect_default()

        # 2. Locate main SSMS window
        main_win = self._find_ssms_main_window()
        if not main_win:
            wins = find_windows("ssms")
            if wins:
                main_win = wins[0]

        if not main_win:
            return {"ok": False, "error": "Could not locate active SQL Server Management Studio window."}

        focus_window(main_win.hwnd)
        time.sleep(0.4)

        # 3. Open New Query tab via Ctrl+N
        log.info("Sending Ctrl+N to open new query window in SSMS...")
        gui_controller.send_hotkey(["ctrl", "n"])
        time.sleep(0.8)

        return {"ok": True, "action": "ssms_new_query", "hotkey": "Ctrl+N", "window": main_win.title}

    def ssms_execute_query(self, sql_query: Optional[str] = None) -> dict[str, Any]:
        """
        Focuses SSMS, ensures connection to default server, opens new query tab if needed,
        pastes/types the query, and executes via F5.
        """
        # Ensure connection first
        self.ssms_connect_default()

        main_win = self._find_ssms_main_window()
        if not main_win:
            wins = find_windows("ssms")
            if wins:
                main_win = wins[0]

        if not main_win:
            return {"ok": False, "error": "SQL Server Management Studio (SSMS) is not running."}

        focus_window(main_win.hwnd)
        time.sleep(0.4)

        if sql_query:
            # If query is provided, open a clean new query tab first to avoid overriding existing text
            gui_controller.send_hotkey(["ctrl", "n"])
            time.sleep(0.8)

            # Paste/type query safely
            gui_controller.type_string(sql_query, press_enter=True)
            time.sleep(0.4)

        # F5 executes query in SSMS
        log.info("Sending F5 to execute SQL query in SSMS...")
        gui_controller.send_hotkey(["f5"])
        time.sleep(0.6)
        return {
            "ok": True,
            "action": "ssms_execute_query",
            "hotkey": "F5",
            "query_length": len(sql_query) if sql_query else 0,
            "window": main_win.title
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
            if act in ("connect", "connect_default", "login"):
                return self.ssms_connect_default()
            if act in ("new_query", "new_tab", "query"):
                return self.ssms_new_query()
            if act in ("run_query", "execute", "run", "paste_and_run"):
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
