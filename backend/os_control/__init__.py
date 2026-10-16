"""Master Module 5: Full OS & External Software Automation Plane."""
from os_control.window_manager import (
    find_windows, focus_window, launch_app, launch_or_focus, list_windows,
    list_processes, foreground_window, window_control, WindowInfo
)
from os_control.ui_automation import ui_automation
from os_control.gui_controller import gui_controller
from os_control.file_tools import read_file_content, write_file_content, list_dir, search_workspace_code
from os_control.shell_runner import shell_runner
from os_control.app_orchestrator import app_orchestrator

__all__ = [
    "find_windows", "focus_window", "launch_app", "launch_or_focus", "list_windows",
    "list_processes", "foreground_window", "window_control", "WindowInfo",
    "ui_automation", "gui_controller", "read_file_content", "write_file_content",
    "list_dir", "search_workspace_code", "shell_runner", "app_orchestrator"
]
