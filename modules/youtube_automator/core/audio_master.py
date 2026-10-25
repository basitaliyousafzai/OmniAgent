"""
Module 7: Broadcast Audio Master & Ducking Mixer (core/audio_master.py).

Submodule 7.1 — EBU R128 Loudness Normalizer (loudnorm I=-14.0:LRA=7.0:tp=-1.5).
Submodule 7.2 — Background Music Loop & Auto-Ducker (volume=0.08 / -22 dB).
Submodule 7.3 — Master Track Mixer (amix with dropout_transition).
"""
from __future__ import annotations

import logging
import random
import subprocess
from pathlib import Path
from typing import Optional

log = logging.getLogger("youtube.audio_master")

_MODULE_ROOT = Path(__file__).resolve().parent.parent
_CACHE_AUDIO = _MODULE_ROOT / "storage" / "cache" / "audio"
_MUSIC_DIR = _MODULE_ROOT / "storage" / "assets" / "music"


def _get_duration(audio_path: Path) -> float:
    """Get audio file duration in seconds via ffprobe."""
    import json as _json
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
        data = _json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0.0))
    except Exception as exc:
        log.warning("ffprobe duration failed for %s: %s", audio_path, exc)
        return 0.0


# ------------------------------------------------------------------ #
# Submodule 7.1 — EBU R128 Loudness Normalizer
# ------------------------------------------------------------------ #

def normalize_loudness(
    input_path: Path,
    output_path: Path,
    target_i: float = -14.0,
    target_lra: float = 7.0,
    target_tp: float = -1.5
) -> Path:
    """
    Apply EBU R128 two-pass loudness normalization to the narration audio.

    Pass 1: Measure current loudness levels.
    Pass 2: Apply correction to reach target integrated loudness.
    """
    log.info("Normalizing loudness: %s -> target I=%.1f LUFS", input_path.name, target_i)

    # Pass 1 — Measure
    measure_cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", f"loudnorm=I={target_i}:LRA={target_lra}:tp={target_tp}:print_format=json",
        "-f", "null", "-"
    ]
    measure_result = subprocess.run(
        measure_cmd, capture_output=True, text=True, timeout=60
    )

    # Extract measured values from stderr (loudnorm prints to stderr)
    stderr = measure_result.stderr
    measured_i = -24.0
    measured_lra = 7.0
    measured_tp = -2.0
    measured_thresh = -34.0

    import re
    for line in stderr.split("\n"):
        line = line.strip()
        if '"input_i"' in line:
            match = re.search(r'"input_i"\s*:\s*"([^"]+)"', line)
            if match:
                try:
                    measured_i = float(match.group(1))
                except ValueError:
                    pass
        elif '"input_lra"' in line:
            match = re.search(r'"input_lra"\s*:\s*"([^"]+)"', line)
            if match:
                try:
                    measured_lra = float(match.group(1))
                except ValueError:
                    pass
        elif '"input_tp"' in line:
            match = re.search(r'"input_tp"\s*:\s*"([^"]+)"', line)
            if match:
                try:
                    measured_tp = float(match.group(1))
                except ValueError:
                    pass
        elif '"input_thresh"' in line:
            match = re.search(r'"input_thresh"\s*:\s*"([^"]+)"', line)
            if match:
                try:
                    measured_thresh = float(match.group(1))
                except ValueError:
                    pass

    # Pass 2 — Apply correction
    normalize_filter = (
        f"loudnorm=I={target_i}:LRA={target_lra}:tp={target_tp}"
        f":measured_I={measured_i}:measured_LRA={measured_lra}"
        f":measured_tp={measured_tp}:measured_thresh={measured_thresh}"
        f":linear=true"
    )

    apply_cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-af", normalize_filter,
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ]
    result = subprocess.run(apply_cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log.error("Loudness normalization failed: %s", result.stderr[:300])
        raise RuntimeError(f"Loudness normalization failed: {result.stderr[:200]}")

    log.info("Loudness normalized: measured_I=%.1f -> target_I=%.1f", measured_i, target_i)
    return output_path


# ------------------------------------------------------------------ #
# Submodule 7.2 — Background Music Loop & Auto-Ducker
# ------------------------------------------------------------------ #

def _find_music_track() -> Optional[Path]:
    """Select a random royalty-free music track from the assets folder."""
    if not _MUSIC_DIR.exists():
        return None
    tracks = list(_MUSIC_DIR.glob("*.mp3")) + list(_MUSIC_DIR.glob("*.wav"))
    if not tracks:
        return None
    chosen = random.choice(tracks)
    log.info("Selected background music: %s", chosen.name)
    return chosen


def _duck_music(
    music_path: Path,
    target_duration: float,
    output_path: Path,
    volume: float = 0.08
) -> Path:
    """
    Loop music to match narration duration and attenuate to -22 dB (volume=0.08).
    """
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(music_path),
        "-t", str(target_duration),
        "-af", f"volume={volume},afade=t=out:st={max(0, target_duration - 2)}:d=2",
        "-c:a", "libmp3lame", "-q:a", "4",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log.error("Music ducking failed: %s", result.stderr[:300])
        raise RuntimeError(f"Music ducking failed: {result.stderr[:200]}")

    log.info("Ducked music: volume=%.2f, duration=%.1fs", volume, target_duration)
    return output_path


# ------------------------------------------------------------------ #
# Submodule 7.3 — Master Track Mixer
# ------------------------------------------------------------------ #

def mix_master(
    voice_path: Path,
    output_path: Path,
    music_volume: float = 0.08
) -> Path:
    """
    Blend normalized voice and ducked background music into a master track.

    If no music files are available, outputs the normalized voice as-is.
    """
    voice_duration = _get_duration(voice_path)

    music_track = _find_music_track()
    if music_track is None:
        log.info("No background music found. Using voice-only master.")
        # Just copy the normalized voice
        import shutil
        shutil.copy2(str(voice_path), str(output_path))
        return output_path

    # Duck the music
    ducked_path = _CACHE_AUDIO / f"music_ducked_{output_path.stem}.mp3"
    _duck_music(music_track, voice_duration, ducked_path, volume=music_volume)

    # Mix voice + ducked music
    cmd = [
        "ffmpeg", "-y",
        "-i", str(voice_path),
        "-i", str(ducked_path),
        "-filter_complex", "amix=inputs=2:duration=first:dropout_transition=2",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log.error("Master mix failed: %s", result.stderr[:300])
        raise RuntimeError(f"Master mix failed: {result.stderr[:200]}")

    # Cleanup ducked temp file
    ducked_path.unlink(missing_ok=True)

    log.info("Master audio mixed: %s (%.2fs)", output_path.name, _get_duration(output_path))
    return output_path


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #

def master_audio(narration_raw_path: Path, run_id: str) -> Path:
    """
    Full audio mastering pipeline:
    1. EBU R128 normalize the raw narration.
    2. Select and duck background music.
    3. Mix into the final master track.

    Returns the path to master_audio_{run_id}.mp3.
    """
    _CACHE_AUDIO.mkdir(parents=True, exist_ok=True)

    # Step 1: Normalize
    normalized_path = _CACHE_AUDIO / f"narration_normalized_{run_id}.mp3"
    normalize_loudness(narration_raw_path, normalized_path)

    # Step 2+3: Mix with music
    master_path = _CACHE_AUDIO / f"master_audio_{run_id}.mp3"
    mix_master(normalized_path, master_path)

    # Cleanup normalized intermediate
    normalized_path.unlink(missing_ok=True)

    return master_path


class AudioMaster:
    """Class wrapper for EBU R128 loudness normalization and background music ducking."""
    def __init__(self, assets_dir: Optional[Path] = None, cache_dir: Optional[Path] = None):
        self.assets_dir = Path(assets_dir) if assets_dir else _MUSIC_DIR.parent
        self.cache_dir = Path(cache_dir) if cache_dir else _CACHE_AUDIO.parent

    def master_soundtrack(self, raw_speech_path: Path, run_id: str) -> Path:
        return master_audio(Path(raw_speech_path), run_id)

