"""
Sub-Module 4.4: High-Performance Screen Capture & Vision Diff Engine.

* Multi-monitor capture with `mss` (falls back to Pillow.ImageGrab).
* Down-scales and JPEG-compresses frames for the vision model (latency/cost).
* Optional 0..1000 coordinate grid overlay to help the model pick click targets.
* Diff engine: reports how much of the screen changed vs the previous frame and
  where (normalized bounding box) - used to verify that GUI actions had effect.
* Screenshots are written to ./.omniagent_data/screenshots and pruned.
"""
from __future__ import annotations

import base64
import io
import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from config import MAX_SCREENSHOTS_KEPT, SCREENSHOT_DIR
from multimodal.coordinate_mapper import Region, mapper

log = logging.getLogger("omniagent.capture")


@dataclass
class CaptureResult:
    file_name: str
    path: str
    b64: str
    mime: str
    width: int
    height: int
    region: Region
    diff: dict[str, Any] = field(default_factory=dict)

    def describe(self) -> str:
        r = self.region
        text = (
            f"Screenshot of monitor {r.monitor_index} ({r.width}x{r.height} px at offset {r.left},{r.top}); "
            f"image sent at {self.width}x{self.height}. Use normalized coordinates 0-1000 relative to this image."
        )
        if self.diff:
            if self.diff.get("changed_pct") is not None:
                text += f" Change vs previous frame: {self.diff['changed_pct']:.1f}% of pixels"
                if self.diff.get("bbox_norm"):
                    text += f", changed region (norm x1,y1,x2,y2) = {self.diff['bbox_norm']}"
                text += "."
        return text


class ScreenCapture:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._previous: Optional[Image.Image] = None
        self._previous_region: Optional[Region] = None
        self.latest: Optional[CaptureResult] = None

    def _grab(self, monitor_index: int) -> tuple[Image.Image, Region]:
        try:
            from os_control.window_manager import ensure_interactive_desktop
            ensure_interactive_desktop()
        except Exception:
            pass
        try:
            import mss

            with mss.mss() as sct:
                monitors = sct.monitors
                if monitor_index < 0 or monitor_index >= len(monitors):
                    monitor_index = 1 if len(monitors) > 1 else 0
                mon = monitors[monitor_index]
                raw = sct.grab(mon)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                return img, Region(mon["left"], mon["top"], mon["width"], mon["height"], monitor_index)
        except Exception as exc:  # noqa: BLE001
            log.warning("mss capture failed (%s); falling back to ImageGrab", exc)
            from PIL import ImageGrab

            img = ImageGrab.grab(all_screens=monitor_index == 0).convert("RGB")
            return img, Region(0, 0, img.width, img.height, monitor_index)

    @staticmethod
    def _draw_grid(img: Image.Image) -> Image.Image:
        img = img.copy()
        draw = ImageDraw.Draw(img, "RGBA")
        w, h = img.size
        try:
            font = ImageFont.truetype("arial.ttf", max(10, w // 110))
        except OSError:
            font = ImageFont.load_default()
        for i in range(1, 10):
            x = int(w * i / 10)
            y = int(h * i / 10)
            draw.line([(x, 0), (x, h)], fill=(255, 0, 180, 90), width=1)
            draw.line([(0, y), (w, y)], fill=(255, 0, 180, 90), width=1)
            draw.text((x + 2, 2), str(i * 100), fill=(255, 0, 180, 230), font=font)
            draw.text((2, y + 2), str(i * 100), fill=(255, 0, 180, 230), font=font)
        return img

    def _diff(self, current: Image.Image, region: Region) -> dict[str, Any]:
        if self._previous is None or self._previous_region != region:
            return {}
        a = self._previous.convert("L").resize((320, int(320 * current.height / max(1, current.width))))
        b = current.convert("L").resize(a.size)
        delta = ImageChops.difference(a, b).point(lambda p: 255 if p > 24 else 0)
        hist = delta.histogram()
        changed = hist[255]
        pct = changed / (a.width * a.height) * 100
        bbox = delta.getbbox()
        bbox_norm = None
        if bbox:
            bbox_norm = [
                round(bbox[0] / a.width * 1000), round(bbox[1] / a.height * 1000),
                round(bbox[2] / a.width * 1000), round(bbox[3] / a.height * 1000),
            ]
        return {"changed_pct": round(pct, 2), "bbox_norm": bbox_norm}

    def _prune(self) -> None:
        files = sorted(SCREENSHOT_DIR.glob("shot_*.jpg"), key=lambda p: p.stat().st_mtime)
        for old in files[:-MAX_SCREENSHOTS_KEPT]:
            try:
                old.unlink()
            except OSError:
                pass

    def capture(self, monitor_index: int = 1, max_width: int = 1366, quality: int = 70, grid: bool = False) -> CaptureResult:
        with self._lock:
            img, region = self._grab(monitor_index)
            diff = self._diff(img, region)
            self._previous, self._previous_region = img, region
            mapper.set_reference(region)

            out = img
            if out.width > max_width:
                ratio = max_width / out.width
                out = out.resize((max_width, int(out.height * ratio)), Image.LANCZOS)
            if grid:
                out = self._draw_grid(out)
            buf = io.BytesIO()
            out.save(buf, format="JPEG", quality=quality, optimize=True)
            data = buf.getvalue()
            name = f"shot_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time() * 1000) % 1000:03d}.jpg"
            path: Path = SCREENSHOT_DIR / name
            path.write_bytes(data)
            self._prune()
            result = CaptureResult(
                file_name=name, path=str(path), b64=base64.b64encode(data).decode("ascii"), mime="image/jpeg",
                width=out.width, height=out.height, region=region, diff=diff,
            )
            self.latest = result
            return result


screen_capture = ScreenCapture()
