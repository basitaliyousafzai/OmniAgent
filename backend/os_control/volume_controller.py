"""
Sub-Module 5.4: Windows Master Audio & Volume Controller.

Provides native Windows volume control via user32 key events:
  - set_volume(percent: 0-100)
  - volume_up(steps)
  - volume_down(steps)
  - toggle_mute()
"""
from __future__ import annotations

import ctypes
import logging
import time
from typing import Any

from config import IS_WINDOWS

log = logging.getLogger("omniagent.volume")

# Windows Virtual-Key Codes for Volume
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


def _send_vk(vk: int) -> None:
    if not IS_WINDOWS:
        return
    user32 = ctypes.windll.user32
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)


class VolumeController:
    def set_volume(self, percent: int) -> dict[str, Any]:
        """Sets Windows master volume to approximately percent (0 - 100)."""
        target = max(0, min(100, int(percent)))
        if not IS_WINDOWS:
            return {"ok": False, "error": "Volume control is currently supported on Windows."}

        # 50 down presses guarantees volume is at 0%
        for _ in range(50):
            _send_vk(VK_VOLUME_DOWN)

        # Each volume up press increases volume by 2%
        up_steps = target // 2
        for _ in range(up_steps):
            _send_vk(VK_VOLUME_UP)

        log.info("System volume set to %d%% (%d steps)", target, up_steps)
        return {"ok": True, "action": "set_volume", "target_percent": target}

    def volume_up(self, steps: int = 5) -> dict[str, Any]:
        for _ in range(max(1, steps)):
            _send_vk(VK_VOLUME_UP)
        return {"ok": True, "action": "volume_up", "steps": steps}

    def volume_down(self, steps: int = 5) -> dict[str, Any]:
        for _ in range(max(1, steps)):
            _send_vk(VK_VOLUME_DOWN)
        return {"ok": True, "action": "volume_down", "steps": steps}

    def toggle_mute(self) -> dict[str, Any]:
        _send_vk(VK_VOLUME_MUTE)
        return {"ok": True, "action": "toggle_mute"}


volume_controller = VolumeController()
