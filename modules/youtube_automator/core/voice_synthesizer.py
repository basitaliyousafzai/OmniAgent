"""
Module 5: Neural Dual-Voice TTS & Subtitle Aligner (core/voice_synthesizer.py).

Submodule 5.1 — Multi-Speaker Async Synthesizer (edge-tts).
Submodule 5.2 — Cumulative Turn Offset Calculator (ffprobe duration measurement).
Submodule 5.3 — Retention Caption Formatter (.srt) with 2-4 word groups.
Submodule 5.4 — Seamless Audio Concatenator (all turns -> single narration file).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

import edge_tts

log = logging.getLogger("youtube.voice_synthesizer")

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_CACHE_AUDIO = _MODULE_ROOT / "storage" / "cache" / "audio"
_CACHE_SUBS = _MODULE_ROOT / "storage" / "cache" / "subtitles"

# Voice assignment map
VOICE_MAP = {
    "Narrator": "en-US-ChristopherNeural",
    "Host": "en-US-ChristopherNeural",
    "Expert": "en-US-JennyNeural",
}


# ------------------------------------------------------------------ #
# Submodule 5.2 — Duration measurement via ffprobe
# ------------------------------------------------------------------ #

def _get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(audio_path)
            ],
            capture_output=True, text=True, timeout=15
        )
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0.0))
    except Exception as exc:
        log.warning("ffprobe duration failed for %s: %s", audio_path, exc)
        return 0.0


# ------------------------------------------------------------------ #
# Submodule 5.1 — Multi-Speaker Async Synthesizer
# ------------------------------------------------------------------ #

async def _synthesize_turn(
    speaker: str,
    text: str,
    output_path: Path,
    cumulative_offset_ms: float
) -> tuple[float, list[dict[str, Any]]]:
    """
    Synthesize a single dialogue turn with edge-tts.

    Returns (duration_seconds, word_boundaries_with_global_offsets).
    """
    voice = VOICE_MAP.get(speaker, "en-US-ChristopherNeural")
    communicate = edge_tts.Communicate(text, voice)

    word_boundaries: list[dict[str, Any]] = []

    # Collect word boundary events
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            chunk_type = chunk.get("type")
            if chunk_type == "audio":
                audio_data = chunk.get("data")
                if audio_data:
                    f.write(audio_data)
            elif chunk_type == "WordBoundary":
                word_boundaries.append({
                    "text": str(chunk.get("text", "")),
                    "offset_ms": float(chunk.get("offset", 0)) / 10_000 + cumulative_offset_ms,
                    "duration_ms": float(chunk.get("duration", 0)) / 10_000,
                })
            elif chunk["type"] == "SentenceBoundary":
                stext = chunk.get("text", "").strip()
                words = stext.split()
                if words:
                    sent_offset = chunk.get("offset", 0) / 10_000 + cumulative_offset_ms
                    sent_dur = chunk.get("duration", 0) / 10_000
                    word_dur = max(sent_dur / len(words), 200.0)
                    for idx, w in enumerate(words):
                        word_boundaries.append({
                            "text": w,
                            "offset_ms": sent_offset + (idx * word_dur),
                            "duration_ms": word_dur
                        })

    duration = _get_audio_duration(output_path)
    log.info(
        "Synthesized turn: speaker=%s, voice=%s, duration=%.2fs, words=%d",
        speaker, voice, duration, len(word_boundaries)
    )
    return duration, word_boundaries


# ------------------------------------------------------------------ #
# Submodule 5.3 — Retention Caption Formatter (.srt)
# ------------------------------------------------------------------ #

def _format_srt_time(ms: float) -> str:
    """Convert milliseconds to SRT timestamp HH:MM:SS,mmm using exact integer arithmetic."""
    total_ms = int(round(ms))
    hours = total_ms // 3600000
    rem = total_ms % 3600000
    minutes = rem // 60000
    rem = rem % 60000
    seconds = rem // 1000
    millis = rem % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _build_srt(all_boundaries: list[dict[str, Any]], output_path: Path) -> None:
    """
    Group word boundaries into 2-4 word punchy captions and write .srt file.
    """
    if not all_boundaries:
        output_path.write_text("1\n00:00:00,000 --> 00:00:03,000\n \n\n", encoding="utf-8")
        return

    lines: list[str] = []
    caption_index = 1
    group: list[dict[str, Any]] = []

    for wb in all_boundaries:
        group.append(wb)
        if len(group) >= 3:
            start_ms = group[0]["offset_ms"]
            end_ms = group[-1]["offset_ms"] + group[-1]["duration_ms"]
            # Ensure minimum display time of 400ms
            if end_ms - start_ms < 400:
                end_ms = start_ms + 400
            caption_text = " ".join(w["text"] for w in group)
            lines.append(str(caption_index))
            lines.append(f"{_format_srt_time(start_ms)} --> {_format_srt_time(end_ms)}")
            lines.append(caption_text)
            lines.append("")
            caption_index += 1
            group = []

    # Flush remaining words
    if group:
        start_ms = group[0]["offset_ms"]
        end_ms = group[-1]["offset_ms"] + group[-1]["duration_ms"]
        if end_ms - start_ms < 400:
            end_ms = start_ms + 400
        caption_text = " ".join(w["text"] for w in group)
        lines.append(str(caption_index))
        lines.append(f"{_format_srt_time(start_ms)} --> {_format_srt_time(end_ms)}")
        lines.append(caption_text)
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("SRT written: %s (%d captions)", output_path.name, caption_index - 1)


# ------------------------------------------------------------------ #
# Submodule 5.4 — Seamless Audio Concatenator
# ------------------------------------------------------------------ #

def _concatenate_audio(turn_files: list[Path], output_path: Path) -> float:
    """
    Concatenate multiple audio turn files into a single narration MP3.
    Returns total duration in seconds.
    """
    if not turn_files:
        return 0.0

    if len(turn_files) == 1:
        # Single file — just copy
        import shutil
        shutil.copy2(str(turn_files[0]), str(output_path))
        return _get_audio_duration(output_path)

    # Build FFmpeg concat filter
    concat_list = output_path.parent / f"concat_list_{output_path.stem}.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for tf in turn_files:
            safe_path = str(tf).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        log.error("Audio concatenation failed: %s", result.stderr[:500])
        raise RuntimeError(f"FFmpeg concat failed: {result.stderr[:300]}")

    # Cleanup temp list
    concat_list.unlink(missing_ok=True)

    duration = _get_audio_duration(output_path)
    log.info("Concatenated %d turns -> %s (%.2fs)", len(turn_files), output_path.name, duration)
    return duration


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

async def synthesize_dialogue(
    dialogue: list[dict[str, str]],
    run_id: str
) -> tuple[Path, Path, float]:
    """
    Synthesize all dialogue turns, generate cumulative .srt subtitles,
    and concatenate into a single narration file.

    Args:
        dialogue: List of {"speaker": "...", "text": "..."} dicts.
        run_id: Unique identifier for this pipeline run.

    Returns:
        (narration_path, srt_path, total_duration_seconds)
    """
    _CACHE_AUDIO.mkdir(parents=True, exist_ok=True)
    _CACHE_SUBS.mkdir(parents=True, exist_ok=True)

    turn_files: list[Path] = []
    all_boundaries: list[dict[str, Any]] = []
    cumulative_offset_ms: float = 0.0

    for i, turn in enumerate(dialogue):
        speaker = turn.get("speaker", "Narrator")
        text = turn.get("text", "").strip()
        if not text:
            continue

        turn_path = _CACHE_AUDIO / f"turn_{run_id}_{i:02d}.mp3"
        duration, boundaries = await _synthesize_turn(
            speaker, text, turn_path, cumulative_offset_ms
        )
        turn_files.append(turn_path)
        all_boundaries.extend(boundaries)
        cumulative_offset_ms += duration * 1000.0  # Convert seconds to ms

    # Build SRT
    srt_path = _CACHE_SUBS / f"captions_{run_id}.srt"
    _build_srt(all_boundaries, srt_path)

    # Concatenate all turns
    narration_path = _CACHE_AUDIO / f"narration_raw_{run_id}.mp3"
    total_duration = _concatenate_audio(turn_files, narration_path)

    # Cleanup individual turn files
    for tf in turn_files:
        tf.unlink(missing_ok=True)

    log.info(
        "Voice synthesis complete: %s (%.2fs), subtitles: %s",
        narration_path.name, total_duration, srt_path.name
    )
    return narration_path, srt_path, total_duration


class VoiceSynthesizer:
    """Class wrapper for multi-speaker async voice synthesis."""
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else _CACHE_AUDIO

    async def synthesize_script(self, script_data: dict[str, Any], run_id: str) -> dict[str, Any]:
        dialogue = script_data.get("dialogue", [])
        narration_path, srt_path, duration = await synthesize_dialogue(dialogue, run_id)
        return {
            "audio_path": narration_path,
            "srt_path": srt_path,
            "duration_sec": duration
        }

