"""
Module 6: Stock Video, Image & Procedural Asset Engine (core/media_retriever.py).

Submodule 6.1 — Pexels HD Portrait Video Fetcher (9:16, height >= 1280).
Submodule 6.2 — Pexels High-Res Portrait Image Fetcher (large2x vertical).
Submodule 6.3 — Zero-Failure Procedural Fallback (FFmpeg lavfi animated background).
"""
from __future__ import annotations

import logging
import random
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

import httpx

log = logging.getLogger("youtube.media_retriever")

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_CACHE_CLIPS = _MODULE_ROOT / "storage" / "cache" / "raw_clips"
_CACHE_IMAGES = _MODULE_ROOT / "storage" / "cache" / "images"
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "youtube_config.json"

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_IMAGE_URL = "https://api.pexels.com/v1/search"


def _load_pexels_key() -> str:
    """Load the Pexels API key from config."""
    import json
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("pexels_api_key", "")
    return ""


# ------------------------------------------------------------------ #
# Submodule 6.1 — Pexels HD Portrait Video Fetcher
# ------------------------------------------------------------------ #

async def _fetch_pexels_video(query: str, api_key: str) -> Optional[Path]:
    """
    Search Pexels for a portrait 9:16 video clip and download it.
    Returns the local file path or None if unavailable.
    """
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "orientation": "portrait",
        "size": "medium",
        "per_page": 15,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(PEXELS_VIDEO_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            videos = data.get("videos", [])

            # Filter for portrait clips (width <= height, height >= 1280)
            candidates = []
            for v in videos:
                for vf in v.get("video_files", []):
                    w = vf.get("width", 0)
                    h = vf.get("height", 0)
                    if w <= h and h >= 1280 and vf.get("link"):
                        candidates.append(vf)

            if not candidates:
                log.warning("No portrait video found for query: %s", query)
                return None

            chosen = random.choice(candidates)
            download_url = chosen["link"]

            safe_q = re.sub(r'[^a-zA-Z0-9_\-]', '_', query)[:32]
            filename = f"clip_{safe_q}_{random.randint(1000, 9999)}.mp4"
            filepath = _CACHE_CLIPS / filename

            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as dl_client:
                dl_resp = await dl_client.get(download_url)
                dl_resp.raise_for_status()
                filepath.write_bytes(dl_resp.content)

            log.info("Downloaded Pexels video: %s (%d bytes)", filename, len(dl_resp.content))
            return filepath

    except Exception as exc:
        log.warning("Pexels video fetch failed for '%s': %s", query, exc)
        return None


# ------------------------------------------------------------------ #
# Submodule 6.2 — Pexels High-Res Portrait Image Fetcher
# ------------------------------------------------------------------ #

async def _fetch_pexels_image(query: str, api_key: str) -> Optional[Path]:
    """
    Search Pexels for a high-res portrait image and download it.
    Returns the local file path or None if unavailable.
    """
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "orientation": "portrait",
        "size": "large",
        "per_page": 15,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(PEXELS_IMAGE_URL, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            photos = data.get("photos", [])

            if not photos:
                log.warning("No portrait image found for query: %s", query)
                return None

            chosen = random.choice(photos)
            # Use large2x for highest quality
            src = chosen.get("src", {})
            download_url = src.get("large2x") or src.get("large") or src.get("original", "")

            if not download_url:
                return None

            safe_q = re.sub(r'[^a-zA-Z0-9_\-]', '_', query)[:32]
            filename = f"img_{safe_q}_{random.randint(1000, 9999)}.jpg"
            filepath = _CACHE_IMAGES / filename

            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as dl_client:
                dl_resp = await dl_client.get(download_url)
                dl_resp.raise_for_status()
                filepath.write_bytes(dl_resp.content)

            log.info("Downloaded Pexels image: %s (%d bytes)", filename, len(dl_resp.content))
            return filepath

    except Exception as exc:
        log.warning("Pexels image fetch failed for '%s': %s", query, exc)
        return None


# ------------------------------------------------------------------ #
# Submodule 6.3 — Zero-Failure Procedural Fallback
# ------------------------------------------------------------------ #

def _generate_procedural_clip(duration: float, index: int, run_id: str) -> Path:
    """
    Generate a 1080x1920 30fps animated gradient background via FFmpeg lavfi.
    This ensures rendering never fails even with zero internet connectivity.
    """
    output = _CACHE_CLIPS / f"procedural_{run_id}_{index:02d}.mp4"

    # Pick random gradient colors for visual variety
    colors = [
        ("0x1a1a2e", "0x16213e", "0xe94560"),
        ("0x0f0c29", "0x302b63", "0x24243e"),
        ("0x141e30", "0x243b55", "0x141e30"),
        ("0x000428", "0x004e92", "0x000428"),
        ("0x200122", "0x6f0000", "0x200122"),
    ]
    c1, c2, c3 = random.choice(colors)
    hue_shift = random.randint(0, 360)

    frames = int(duration * 30)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c={c1}:s=1080x1920:d={duration}:r=30,"
            f"drawbox=x=0:y=0:w=1080:h=960:color={c2}@0.6:t=fill,"
            f"hue=h={hue_shift}+t*15,"
            f"format=yuv420p"
        ),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "fastdecode",
        "-threads", "4",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        str(output)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log.error("Procedural clip generation failed: %s", result.stderr[:300])
        raise RuntimeError(f"Procedural fallback failed: {result.stderr[:200]}")

    log.info("Generated procedural clip: %s (%.1fs)", output.name, duration)
    return output


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

async def retrieve_media(
    visual_prompts: list[dict[str, str]],
    run_id: str,
    scene_duration: float = 4.0
) -> list[dict[str, Any]]:
    """
    Fetch or generate all media assets for the visual prompts.

    Args:
        visual_prompts: List of {"type": "video"|"image", "query": "..."} dicts.
        run_id: Unique pipeline run identifier.
        scene_duration: Duration per scene in seconds.

    Returns:
        List of {"type": "video"|"image", "path": Path, "duration": float} dicts.
    """
    _CACHE_CLIPS.mkdir(parents=True, exist_ok=True)
    _CACHE_IMAGES.mkdir(parents=True, exist_ok=True)

    api_key = _load_pexels_key()
    results: list[dict[str, Any]] = []

    for i, vp in enumerate(visual_prompts):
        media_type = vp.get("type", "video")
        query = vp.get("query", "abstract background")

        filepath: Optional[Path] = None

        if api_key:
            if media_type == "video":
                filepath = await _fetch_pexels_video(query, api_key)
            else:
                filepath = await _fetch_pexels_image(query, api_key)

        if filepath is None:
            # Fallback to procedural generation
            log.info("Using procedural fallback for scene %d (%s)", i, query)
            filepath = _generate_procedural_clip(scene_duration, i, run_id)
            media_type = "video"  # Procedural is always video

        results.append({
            "type": media_type,
            "path": filepath,
            "duration": scene_duration,
            "query": query,
        })

    log.info("Media retrieval complete: %d assets", len(results))
    return results


class MediaRetriever:
    """Class wrapper for stock media and procedural fallback retrieval."""
    def __init__(self, cache_dir: Optional[Path] = None, pexels_api_key: Optional[str] = None):
        self.cache_dir = Path(cache_dir) if cache_dir else _CACHE_CLIPS.parent
        self.pexels_api_key = pexels_api_key

    async def retrieve_visual_assets(
        self,
        visual_prompts: list[dict[str, str]],
        run_id: str,
        scene_duration: float = 4.0
    ) -> list[dict[str, Any]]:
        return await retrieve_media(visual_prompts, run_id, scene_duration)

