"""
Sub-Module 4.5: Visual Coordinate Normalizer.

The vision model reasons in a resolution-independent space of 0..1000 on both
axes relative to the screenshot it was shown. This module converts those
coordinates to physical desktop pixels, accounting for multi-monitor offsets
(negative origins for monitors left/above the primary) and Windows DPI scaling.
"""
from __future__ import annotations

import ctypes
import logging
import threading
from dataclasses import asdict, dataclass

from config import IS_WINDOWS

log = logging.getLogger("omniagent.coords")
NORM_MAX = 1000.0
_dpi_done = False


def enable_dpi_awareness() -> None:
    """Make this process per-monitor DPI aware so mss, pyautogui and Win32 share one pixel space."""
    global _dpi_done
    if _dpi_done or not IS_WINDOWS:
        return
    _dpi_done = True
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # PER_MONITOR_AWARE_V2
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception as exc:  # noqa: BLE001
        log.debug("DPI awareness unavailable: %s", exc)


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int
    monitor_index: int = 1

    def as_dict(self) -> dict:
        return asdict(self)


class CoordinateMapper:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reference: Region | None = None

    def set_reference(self, region: Region) -> None:
        with self._lock:
            self._reference = region

    def reference(self) -> Region:
        with self._lock:
            if self._reference is not None:
                return self._reference
        region = primary_monitor_region()
        self.set_reference(region)
        return region

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(NORM_MAX, float(v)))

    def to_pixels(self, norm_x: float, norm_y: float, region: Region | None = None) -> tuple[int, int]:
        r = region or self.reference()
        nx, ny = self._clamp(norm_x), self._clamp(norm_y)
        px = r.left + round(nx / NORM_MAX * (r.width - 1))
        py = r.top + round(ny / NORM_MAX * (r.height - 1))
        return int(px), int(py)

    def to_normalized(self, px: int, py: int, region: Region | None = None) -> tuple[int, int]:
        r = region or self.reference()
        nx = (px - r.left) / max(1, r.width - 1) * NORM_MAX
        ny = (py - r.top) / max(1, r.height - 1) * NORM_MAX
        return int(round(self._clamp(nx))), int(round(self._clamp(ny)))


def list_monitors() -> list[Region]:
    import mss

    with mss.mss() as sct:
        out = []
        for idx, mon in enumerate(sct.monitors):
            out.append(Region(left=mon["left"], top=mon["top"], width=mon["width"], height=mon["height"], monitor_index=idx))
        return out


def primary_monitor_region() -> Region:
    monitors = list_monitors()
    return monitors[1] if len(monitors) > 1 else monitors[0]


mapper = CoordinateMapper()
