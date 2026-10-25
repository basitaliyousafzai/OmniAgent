"""
Module 8: CPU FFmpeg Video Compositor & Renderer (core/video_compositor.py).

Submodule 8.1 — Ken Burns Image Motion Engine (zoompan animation).
Submodule 8.2 — B-Roll Clip Standardizer (scale, crop, normalize to 1080x1920).
Submodule 8.3 — Safe-Zone Subtitle Burner (bold yellow/black burned captions).
Submodule 8.4 — CPU-Capped Master Encoder (libx264 ultrafast, threads 4).
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("youtube.video_compositor")

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_CACHE_CLIPS = _MODULE_ROOT / "storage" / "cache" / "raw_clips"
_RENDERED_DIR = _MODULE_ROOT / "storage" / "rendered"
_FONTS_DIR = _MODULE_ROOT / "storage" / "assets" / "fonts"

# CPU encoding constants — zero GPU/CUDA/NVENC flags
CPU_ENCODE = [
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-tune", "fastdecode",
    "-threads", "4",
    "-pix_fmt", "yuv420p",
]


# ------------------------------------------------------------------ #
# Submodule 8.1 — Ken Burns Image Motion Engine
# ------------------------------------------------------------------ #

def _animate_image(image_path: Path, duration: float, output_path: Path) -> Path:
    """
    Convert a static image into a smooth Ken Burns zoom/pan 1080x1920 clip.

    Uses zoompan filter:
      z: slow zoom from 1.0 to 1.18 (0.0015 per frame)
      d: total frames (duration * 30fps)
      x/y: center-locked pan
      s: output resolution 1080x1920
      fps: 30
    """
    frames = int(duration * 30)

    # zoompan filter with center-locked smooth zoom
    zoompan_filter = (
        f"zoompan=z='min(zoom+0.0015,1.18)':d={frames}"
        f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":s=1080x1920:fps=30,"
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-vf", zoompan_filter,
        "-t", str(duration),
        *CPU_ENCODE,
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error("Ken Burns animation failed for %s: %s", image_path.name, result.stderr[:300])
        raise RuntimeError(f"Ken Burns failed: {result.stderr[:200]}")

    log.info("Ken Burns animated: %s -> %s (%.1fs)", image_path.name, output_path.name, duration)
    return output_path


# ------------------------------------------------------------------ #
# Submodule 8.2 — B-Roll Clip Standardizer
# ------------------------------------------------------------------ #

def _standardize_clip(input_path: Path, duration: float, output_path: Path) -> Path:
    """
    Scale, center-crop, and normalize a video clip to 1080x1920, 30fps, setsar=1.
    """
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30,"
        "setsar=1,"
        "format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", vf,
        "-t", str(duration),
        "-an",  # Strip original audio
        *CPU_ENCODE,
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error("Clip standardization failed for %s: %s", input_path.name, result.stderr[:300])
        raise RuntimeError(f"Clip standardize failed: {result.stderr[:200]}")

    log.info("Standardized clip: %s -> %s (%.1fs)", input_path.name, output_path.name, duration)
    return output_path


# ------------------------------------------------------------------ #
# Submodule 8.3 — Safe-Zone Subtitle Burner
# ------------------------------------------------------------------ #

def _get_subtitle_style() -> str:
    """
    Build ASS/SSA subtitle style string for burned subtitles.

    Bold yellow text with 3px black outline, lower-middle positioning.
    """
    # Attempt to use Montserrat-Black if available, fallback to Arial Bold
    font_name = "Arial"
    montserrat_path = _FONTS_DIR / "Montserrat-Black.ttf"
    if montserrat_path.exists():
        font_name = "Montserrat Black"

    style = (
        f"FontName={font_name},"
        f"FontSize=20,"
        f"Bold=1,"
        f"PrimaryColour=&H0000FFFF,"
        f"OutlineColour=&H00000000,"
        f"BorderStyle=1,"
        f"Outline=3,"
        f"Alignment=2,"
        f"MarginV=140"
    )
    return style


# ------------------------------------------------------------------ #
# Submodule 8.4 — CPU-Capped Master Encoder
# ------------------------------------------------------------------ #

def compose_video(
    media_assets: list[dict[str, Any]],
    master_audio_path: Path,
    srt_path: Path,
    run_id: str,
) -> Path:
    """
    Full video composition pipeline:
    1. Process each media asset (Ken Burns for images, standardize for videos).
    2. Concatenate all processed clips.
    3. Sync master audio (-shortest).
    4. Burn subtitles with styled yellow/black captions.
    5. Output final 1080x1920 MP4 with CPU encoding.

    Returns the path to the rendered output file.
    """
    _CACHE_CLIPS.mkdir(parents=True, exist_ok=True)
    _RENDERED_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Process each media asset into standardized clips
    processed_clips: list[Path] = []

    for i, asset in enumerate(media_assets):
        asset_type = asset.get("type", "video")
        asset_path = Path(asset.get("path", ""))
        duration = float(asset.get("duration", 4.0))

        processed_path = _CACHE_CLIPS / f"processed_{run_id}_{i:02d}.mp4"

        if asset_type == "image" and asset_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            _animate_image(asset_path, duration, processed_path)
        else:
            _standardize_clip(asset_path, duration, processed_path)

        processed_clips.append(processed_path)

    if not processed_clips:
        raise RuntimeError("No media clips available for composition")

    # Step 2: Build concat list
    concat_list_path = _CACHE_CLIPS / f"concat_{run_id}.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for clip in processed_clips:
            safe_path = str(clip).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    # Step 3: Concatenate visual clips into a single video (no audio)
    concat_output = _CACHE_CLIPS / f"visual_concat_{run_id}.mp4"
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_path),
        "-c", "copy",
        str(concat_output)
    ]
    concat_result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=180)
    if concat_result.returncode != 0:
        log.error("Visual concatenation failed: %s", concat_result.stderr[:300])
        raise RuntimeError(f"Visual concat failed: {concat_result.stderr[:200]}")

    # Step 4+5: Merge audio, burn subtitles, and encode final output
    final_output = _RENDERED_DIR / f"short_{run_id}.mp4"
    subtitle_style = _get_subtitle_style()

    # Escape the SRT path for FFmpeg subtitles filter (Windows backslash handling)
    srt_escaped = str(srt_path).replace("\\", "/").replace(":", r"\:")

    vf_filter = (
        f"subtitles=filename='{srt_escaped}'"
        f":force_style='{subtitle_style}'"
    )

    final_cmd = [
        "ffmpeg", "-y",
        "-i", str(concat_output),
        "-i", str(master_audio_path),
        "-vf", vf_filter,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",
        *CPU_ENCODE,
        "-c:a", "aac", "-b:a", "192k",
        str(final_output)
    ]

    final_result = subprocess.run(final_cmd, capture_output=True, text=True, timeout=600)
    if final_result.returncode != 0:
        log.error("Final encoding failed: %s", final_result.stderr[:500])
        raise RuntimeError(f"Final encode failed: {final_result.stderr[:300]}")

    # Cleanup intermediate files
    for clip in processed_clips:
        clip.unlink(missing_ok=True)
    concat_list_path.unlink(missing_ok=True)
    concat_output.unlink(missing_ok=True)

    file_size = final_output.stat().st_size
    log.info(
        "Video composition complete: %s (%d bytes, %.1f MB)",
        final_output.name, file_size, file_size / (1024 * 1024)
    )
    return final_output


class VideoCompositor:
    """Class wrapper for CPU FFmpeg video composition, Ken Burns animation, and subtitle burning."""

    def __init__(
        self,
        output_dir: Optional[Path | str] = None,
        cache_dir: Optional[Path | str] = None
    ) -> None:
        self.output_dir: Path = Path(output_dir) if output_dir else _RENDERED_DIR
        self.cache_dir: Path = Path(cache_dir) if cache_dir else _CACHE_CLIPS.parent

    def render_short(
        self,
        visual_assets: list[dict[str, Any]],
        audio_path: Path | str,
        srt_path: Path | str,
        run_id: str
    ) -> Path:
        return compose_video(
            media_assets=visual_assets,
            master_audio_path=Path(audio_path),
            srt_path=Path(srt_path),
            run_id=run_id
        )

