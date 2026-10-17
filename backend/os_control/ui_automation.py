"""
Sub-Module 5.2: Accessibility & UI Element Inspector (Windows UI Automation / pywinauto).

Allows inspecting and interacting with UI elements in desktop applications (such
as Visual Studio or SSMS) via accessibility APIs:
  - Finding elements by Name, ControlType, or AutomationId.
  - Dumping the UI tree of the target or active window.
  - Clicking buttons (e.g. SSMS "Execute", VS "Start / Debug", Dialog buttons).
  - Setting text into edit fields directly without moving the mouse pointer.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional

from config import IS_WINDOWS
from safety.kill_switch import kill_switch

log = logging.getLogger("omniagent.ui_automation")


class UIAutomationEngine:
    def __init__(self) -> None:
        self._uia_app: Any = None

    def dump_control_tree(self, hwnd: int, max_depth: int = 3, max_elements: int = 80) -> list[dict[str, Any]]:
        """
        Dumps the visual element tree of a window using Windows UI Automation.
        Returns a simplified list of interactive controls (buttons, edits, menus, tabs, etc.).
        """
        kill_switch.check()
        if not IS_WINDOWS:
            return [{"error": "UI Automation tree inspection is only available on Windows."}]

        try:
            from pywinauto import Application

            app = Application(backend="uia").connect(handle=hwnd)
            window = app.window(handle=hwnd)

            elements: list[dict[str, Any]] = []

            def _traverse(ctrl: Any, depth: int) -> None:
                if depth > max_depth or len(elements) >= max_elements:
                    return

                try:
                    elem_info = ctrl.element_info
                    name = elem_info.name or ""
                    control_type = elem_info.control_type or ""
                    auto_id = getattr(elem_info, "automation_id", "") or ""
                    rect = elem_info.rectangle

                    # Only capture controls with meaningful identifiers or interactive types
                    interactive_types = {
                        "Button", "Edit", "MenuItem", "TabItem", "TreeItem",
                        "ListItem", "CheckBox", "RadioButton", "ComboBox",
                        "Document", "Pane", "ToolBar", "Window"
                    }

                    if (name or auto_id) and (control_type in interactive_types or depth <= 1):
                        elements.append({
                            "name": name,
                            "control_type": control_type,
                            "automation_id": auto_id,
                            "depth": depth,
                            "rect": {
                                "left": rect.left,
                                "top": rect.top,
                                "width": rect.width(),
                                "height": rect.height()
                            }
                        })

                    for child in ctrl.children():
                        if len(elements) >= max_elements:
                            break
                        _traverse(child, depth + 1)
                except Exception as e:
                    log.debug("Control inspection traversal error: %s", e)

            _traverse(window, 0)
            return elements

        except Exception as exc:
            log.warning("dump_control_tree failed for hwnd %s: %s", hwnd, exc)
            return [{"error": f"Failed to dump UI tree: {exc}"}]

    def click_element(
        self,
        hwnd: int,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        auto_id: Optional[str] = None,
        timeout: float = 5.0
    ) -> dict[str, Any]:
        """
        Finds a specific UI control in the window and invokes its default click action.
        """
        kill_switch.check()
        if not IS_WINDOWS:
            return {"ok": False, "error": "UI element click is only supported on Windows."}

        try:
            from pywinauto import Application

            app = Application(backend="uia").connect(handle=hwnd)
            window = app.window(handle=hwnd)

            criteria: dict[str, Any] = {}
            if name:
                criteria["title"] = name
            if control_type:
                criteria["control_type"] = control_type
            if auto_id:
                criteria["auto_id"] = auto_id

            if not criteria:
                return {"ok": False, "error": "Must specify at least one search criterion (name, control_type, auto_id)."}

            ctrl = window.child_window(**criteria)
            try:
                ctrl.wait("visible", timeout=timeout)
            except Exception:
                ctrl.wait("exists", timeout=2.0)

            # Try invoke or click
            try:
                ctrl.invoke()
                method = "invoke"
            except Exception:
                ctrl.click_input()
                method = "click_input"

            time.sleep(0.3)
            return {"ok": True, "action": f"clicked element using {method}", "criteria": criteria}

        except Exception as exc:
            log.warning("click_element failed: %s", exc)
            return {"ok": False, "error": str(exc), "criteria": criteria}

    def set_element_text(
        self,
        hwnd: int,
        text: str,
        name: Optional[str] = None,
        auto_id: Optional[str] = None,
        timeout: float = 5.0
    ) -> dict[str, Any]:
        """
        Locates an Edit/Document control in the target window and sets its text value.
        """
        kill_switch.check()
        if not IS_WINDOWS:
            return {"ok": False, "error": "UI element set text is only supported on Windows."}

        try:
            from pywinauto import Application

            app = Application(backend="uia").connect(handle=hwnd)
            window = app.window(handle=hwnd)

            criteria: dict[str, Any] = {}
            if name:
                criteria["title"] = name
            if auto_id:
                criteria["auto_id"] = auto_id

            ctrl = window.child_window(control_type="Edit", **criteria) if criteria else window.child_window(control_type="Edit")
            ctrl.wait("visible", timeout=timeout)
            ctrl.set_edit_text(text)

            return {"ok": True, "action": "set_text_success", "length": len(text)}

        except Exception as exc:
            log.warning("set_element_text failed: %s", exc)
            return {"ok": False, "error": str(exc)}


ui_automation = UIAutomationEngine()
