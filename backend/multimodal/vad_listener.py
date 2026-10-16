"""
Sub-Module 4.1: Audio Streaming & Voice-Activity-Detection (offline).

Captures the host microphone at 16 kHz via `sounddevice`, detects speech start/end
with an adaptive-noise-floor energy detector, then confirms each candidate
utterance with the Silero VAD ONNX model bundled inside faster-whisper (no torch
required). Confirmed utterances are passed to a callback as float32 arrays.
"""
from __future__ import annotations

import collections
import logging
import threading
import time
from typing import Any, Callable, Optional

import numpy as np

log = logging.getLogger("omniagent.vad")

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000


class VADListener:
    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._callback: Optional[Callable[[np.ndarray], None]] = None
        self._on_state: Optional[Callable[[str], None]] = None
        self.active = False
        self.last_error = ""
        self.start_frames = 4           # ~120 ms of voiced frames to open a segment
        self.end_silence_ms = 900       # silence needed to close a segment
        self.max_segment_s = 30.0
        self.min_segment_s = 0.4
        self.pre_roll_ms = 300

    @staticmethod
    def _silero_confirms(samples: np.ndarray) -> bool:
        try:
            from faster_whisper.vad import VadOptions, get_speech_timestamps

            stamps = get_speech_timestamps(samples, VadOptions(min_silence_duration_ms=300))
            return len(stamps) > 0
        except Exception as exc:  # noqa: BLE001 - Silero optional, energy VAD already gated
            log.debug("Silero confirmation unavailable: %s", exc)
            return True

    def start(self, callback: Callable[[np.ndarray], None], on_state: Optional[Callable[[str], None]] = None,
              device: Any = None) -> None:
        if self.active:
            return
        self._callback = callback
        self._on_state = on_state
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, args=(device,), name="omniagent-vad", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._thread = None
        self.active = False

    def _emit_state(self, state: str) -> None:
        if self._on_state:
            try:
                self._on_state(state)
            except Exception:  # noqa: BLE001
                pass

    def _run(self, device: Any) -> None:
        try:
            import sounddevice as sd
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"sounddevice unavailable: {exc}"
            log.error(self.last_error)
            self._emit_state("error")
            return

        frames: "collections.deque[np.ndarray]" = collections.deque()
        lock = threading.Lock()
        ready = threading.Event()

        def on_audio(indata, _frames, _time, status) -> None:  # noqa: ANN001
            if status:
                log.debug("Audio status: %s", status)
            with lock:
                frames.append(indata[:, 0].copy())
            ready.set()

        pre_roll: "collections.deque[np.ndarray]" = collections.deque(maxlen=max(1, self.pre_roll_ms // FRAME_MS))
        noise_floor = 0.005
        voiced_run = 0
        silence_ms = 0
        in_speech = False
        segment: list[np.ndarray] = []
        seg_start = 0.0

        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                                blocksize=FRAME_SAMPLES, device=device, callback=on_audio):
                self.active = True
                self.last_error = ""
                self._emit_state("listening")
                while not self._stop.is_set():
                    if not ready.wait(timeout=0.2):
                        continue
                    with lock:
                        batch = list(frames)
                        frames.clear()
                        ready.clear()
                    for frame in batch:
                        rms = float(np.sqrt(np.mean(frame * frame)) + 1e-9)
                        threshold = max(noise_floor * 3.0, 0.012)
                        voiced = rms > threshold
                        if not in_speech:
                            noise_floor = 0.95 * noise_floor + 0.05 * min(rms, 0.05)
                            pre_roll.append(frame)
                            voiced_run = voiced_run + 1 if voiced else 0
                            if voiced_run >= self.start_frames:
                                in_speech = True
                                segment = list(pre_roll)
                                silence_ms = 0
                                seg_start = time.time()
                                self._emit_state("speech")
                        else:
                            segment.append(frame)
                            silence_ms = 0 if voiced else silence_ms + FRAME_MS
                            too_long = time.time() - seg_start > self.max_segment_s
                            if silence_ms >= self.end_silence_ms or too_long:
                                in_speech = False
                                voiced_run = 0
                                pre_roll.clear()
                                audio = np.concatenate(segment) if segment else np.zeros(0, dtype=np.float32)
                                segment = []
                                self._emit_state("processing")
                                if audio.size / SAMPLE_RATE >= self.min_segment_s and self._silero_confirms(audio):
                                    if self._callback:
                                        try:
                                            self._callback(audio.astype(np.float32))
                                        except Exception as exc:  # noqa: BLE001
                                            log.error("VAD callback failed: %s", exc)
                                self._emit_state("listening")
        except Exception as exc:  # noqa: BLE001
            self.last_error = str(exc)
            log.error("Microphone listener failed: %s", exc)
            self._emit_state("error")
        finally:
            self.active = False
            self._emit_state("stopped")

    def status(self) -> dict[str, Any]:
        return {"active": self.active, "error": self.last_error}


vad_listener = VADListener()
