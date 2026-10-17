"""
Sub-Module 5.3: Mouse, Keyboard & Hotkey Synthesizer.

Provides desktop input automation via PyAutoGUI with fail-safes:
  - Coordinate translation from normalized space (0-1000) to native screen pixels.
  - Left click, right click, double click, mouse move, and drag.
  - Safe text typing with clipboard fallback (pyperclip) for fast & unicode-safe entry.
  - Keyboard shortcuts and hotkey chords (e.g. F5, Ctrl+Shift+B, Ctrl+E, Ctrl+S).
  - Integration with Emergency Kill Switch (aborts immediately if Ctrl+Esc triggered).
"""
from __future__ import annotations

import logging
import time
from typing import Any, Sequence

import pyautogui
import pyperclip

def _ease_out_quad(n: float) -> float:
    """Quadratic easing-out curve for natural human mouse motion (t: 0.0 -> 1.0)."""
    return -n * (n - 2.0)

from gateway.vault import vault
from multimodal.coordinate_mapper import mapper
from safety.kill_switch import kill_switch

log = logging.getLogger("omniagent.gui_controller")

# PyAutoGUI configuration (Safety handled via OmniAgent sovereign Ctrl+Esc Kill Switch)
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.01


class GUIController:
    def __init__(self) -> None:
        pass

    def _sleep_action_delay(self) -> None:
        delay = float(vault.get("gui_action_delay", 0.08))
        if delay > 0:
            time.sleep(delay)

    def mouse_move(self, norm_x: float, norm_y: float) -> tuple[int, int]:
        kill_switch.check()
        try:
            from os_control.window_manager import ensure_interactive_desktop
            ensure_interactive_desktop()
        except Exception:
            pass
        px, py = mapper.to_pixels(norm_x, norm_y)
        pyautogui.moveTo(px, py, duration=0.10, tween=_ease_out_quad)
        return px, py

    def mouse_click(
        self,
        norm_x: float,
        norm_y: float,
        click_type: str = "left",
        button: str = "left"
    ) -> dict[str, Any]:
        kill_switch.check()
        try:
            from os_control.window_manager import ensure_interactive_desktop
            ensure_interactive_desktop()
        except Exception:
            pass
        px, py = mapper.to_pixels(norm_x, norm_y)

        # Fast and smooth human-like glide to target coordinates
        pyautogui.moveTo(px, py, duration=0.09, tween=_ease_out_quad)
        time.sleep(0.01)

        if click_type == "double":
            pyautogui.doubleClick(button=button)
        elif click_type == "right":
            pyautogui.rightClick()
        else:
            pyautogui.click(button=button)

        self._sleep_action_delay()
        return {"action": "click", "norm_x": norm_x, "norm_y": norm_y, "pixel_x": px, "pixel_y": py, "click_type": click_type}

    def mouse_drag(
        self,
        start_norm_x: float,
        start_norm_y: float,
        end_norm_x: float,
        end_norm_y: float,
        duration: float = 0.5
    ) -> dict[str, Any]:
        kill_switch.check()
        start_px, start_py = mapper.to_pixels(start_norm_x, start_norm_y)
        end_px, end_py = mapper.to_pixels(end_norm_x, end_norm_y)

        pyautogui.moveTo(start_px, start_py)
        pyautogui.dragTo(end_px, end_py, duration=duration, button="left")
        self._sleep_action_delay()
        return {"action": "drag", "from": (start_px, start_py), "to": (end_px, end_py)}

    def type_string(self, text: str, press_enter: bool = False, use_clipboard_threshold: int = 15) -> dict[str, Any]:
        """
        Types text into the active focused window.
        Uses clipboard paste (Ctrl+V) if text is multi-line, long, or contains non-ASCII characters.
        """
        kill_switch.check()
        if not text:
            return {"action": "type_string", "count": 0}

        # Fast and reliable unicode paste for complex or multi-line strings
        is_complex = len(text) > use_clipboard_threshold or "\n" in text or not text.isascii()

        if is_complex:
            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass

            pyperclip.copy(text)
            time.sleep(0.05)
            # Paste hotkey
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)

            # Restore clipboard after small delay
            try:
                if old_clipboard:
                    pyperclip.copy(old_clipboard)
            except Exception:
                pass
        else:
            pyautogui.write(text, interval=0.005)

        if press_enter:
            pyautogui.press("enter")

        self._sleep_action_delay()
        return {"action": "type_string", "length": len(text), "pasted": is_complex, "pressed_enter": press_enter}

    def send_hotkey(self, keys: Sequence[str]) -> dict[str, Any]:
        """
        Sends hotkey combinations (e.g. ['ctrl', 'shift', 'b'], ['f5'], ['ctrl', 's']).
        Normalizes common naming variations.
        """
        kill_switch.check()
        try:
            from os_control.window_manager import ensure_interactive_desktop
            ensure_interactive_desktop()
        except Exception:
            pass
        if not keys:
            return {"action": "send_hotkey", "error": "No keys provided"}

        normalized: list[str] = []
        for k in keys:
            k_lower = k.lower().strip()
            # Normalize common names
            mapping = {
                "control": "ctrl",
                "return": "enter",
                "escape": "esc",
                "windows": "win",
                "winleft": "win",
                "altleft": "alt",
                "ctrlleft": "ctrl",
            }
            normalized.append(mapping.get(k_lower, k_lower))

        pyautogui.hotkey(*normalized)
        self._sleep_action_delay()
        return {"action": "send_hotkey", "keys": normalized}

    def press_key(self, key: str, presses: int = 1) -> dict[str, Any]:
        kill_switch.check()
        pyautogui.press(key.lower().strip(), presses=presses)
        self._sleep_action_delay()
        return {"action": "press_key", "key": key, "presses": presses}

    def scroll(self, clicks: int, norm_x: Optional[float] = None, norm_y: Optional[float] = None) -> dict[str, Any]:
        """
        Scrolls the mouse wheel.
        clicks: positive for scrolling up, negative for scrolling down (e.g. -5 to scroll down).
        norm_x, norm_y: optional normalized coordinates to position mouse over before scrolling.
        """
        kill_switch.check()
        if norm_x is not None and norm_y is not None:
            px, py = mapper.to_pixels(norm_x, norm_y)
            pyautogui.moveTo(px, py)
        pyautogui.scroll(clicks)
        self._sleep_action_delay()
        return {"action": "scroll", "clicks": clicks}


gui_controller = GUIController()

