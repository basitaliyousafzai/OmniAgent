"""
Sub-Module 4.2: Local Speech-to-Text (offline faster-whisper).

Models are downloaded once into ./.cache/models/whisper and then run fully
offline on CPU (int8) or CUDA (float16) if available. Accepts any container
PyAV can decode (webm/opus from the browser, wav, mp3, ogg ...) or raw
16 kHz float32 numpy arrays from the VAD microphone listener.
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Any

from config import AUDIO_TMP_DIR, WHISPER_CACHE_DIR

log = logging.getLogger("omniagent.stt")

VALID_MODELS = ("tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "medium.en", "large-v3", "distil-large-v3")


class SpeechToText:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._model: Any = None
        self._model_name = ""
        self.loading = False

    def _device(self) -> tuple[str, str]:
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                return "cuda", "float16"
        except Exception:  # noqa: BLE001
            pass
        return "cpu", "int8"

    def _ensure_model(self, model_name: str) -> Any:
        if model_name not in VALID_MODELS:
            model_name = "base"
        if self._model is not None and self._model_name == model_name:
            return self._model
        from faster_whisper import WhisperModel

        self.loading = True
        try:
            device, compute = self._device()
            log.info("Loading Whisper model '%s' on %s (%s) from %s", model_name, device, compute, WHISPER_CACHE_DIR)
            self._model = WhisperModel(
                model_name, device=device, compute_type=compute, download_root=str(WHISPER_CACHE_DIR),
                cpu_threads=max(1, (os.cpu_count() or 4) // 2),
            )
            self._model_name = model_name
            return self._model
        finally:
            self.loading = False

    def status(self) -> dict[str, Any]:
        return {"loaded": self._model is not None, "model": self._model_name, "loading": self.loading}

    def unload(self) -> None:
        with self._lock:
            self._model = None
            self._model_name = ""

    def _run(self, audio: Any, model_name: str, language: str | None) -> dict[str, Any]:
        start = time.time()
        with self._lock:
            model = self._ensure_model(model_name)
            segments, info = model.transcribe(
                audio, language=language, vad_filter=True, beam_size=5,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
        return {
            "text": text,
            "language": getattr(info, "language", None),
            "duration": round(getattr(info, "duration", 0.0) or 0.0, 2),
            "elapsed": round(time.time() - start, 2),
            "model": self._model_name,
        }

    def transcribe_bytes(self, data: bytes, suffix: str = ".webm", model_name: str = "base", language: str | None = None) -> dict[str, Any]:
        if not data:
            return {"text": "", "language": None, "duration": 0.0, "elapsed": 0.0, "model": model_name}
        tmp = AUDIO_TMP_DIR / f"rec_{uuid.uuid4().hex}{suffix if suffix.startswith('.') else '.' + suffix}"
        tmp.write_bytes(data)
        try:
            return self._run(str(tmp), model_name, language)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass

    def transcribe_array(self, samples: Any, model_name: str = "base", language: str | None = None) -> dict[str, Any]:
        return self._run(samples, model_name, language)


stt = SpeechToText()
