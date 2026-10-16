"""
Sub-Module 4.3: Local Text-to-Speech (offline pyttsx3 / SAPI5 / NSSpeech / eSpeak).

pyttsx3 engines are not thread-safe and on Windows require COM to be initialised
per thread, so all synthesis runs on one dedicated worker thread fed by a queue.
Two modes:
  * synthesize(text) -> WAV bytes (streamed to the browser for playback)
  * speak(text)      -> plays directly on the host speakers
"""
from __future__ import annotations

import logging
import queue
import threading
import uuid
from concurrent.futures import Future
from typing import Any, Optional

from config import AUDIO_TMP_DIR, IS_WINDOWS

log = logging.getLogger("omniagent.tts")


class TextToSpeech:
    def __init__(self) -> None:
        self._queue: "queue.Queue[tuple[str, str, int, Future]]" = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.available: Optional[bool] = None
        self.last_error = ""

    def _ensure_worker(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._worker, name="omniagent-tts", daemon=True)
        self._thread.start()

    def _worker(self) -> None:
        com_initialised = False
        if IS_WINDOWS:
            try:
                import pythoncom

                pythoncom.CoInitialize()
                com_initialised = True
            except Exception as exc:  # noqa: BLE001
                log.debug("COM init failed: %s", exc)
        try:
            while not self._stop.is_set():
                try:
                    mode, text, rate, fut = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if fut.set_running_or_notify_cancel() is False:
                    continue
                try:
                    import pyttsx3

                    engine = pyttsx3.init()
                    engine.setProperty("rate", rate)
                    if mode == "file":
                        out = AUDIO_TMP_DIR / f"tts_{uuid.uuid4().hex}.wav"
                        engine.save_to_file(text, str(out))
                        engine.runAndWait()
                        data = out.read_bytes() if out.exists() else b""
                        try:
                            out.unlink()
                        except OSError:
                            pass
                        fut.set_result(data)
                    else:
                        engine.say(text)
                        engine.runAndWait()
                        fut.set_result(b"")
                    engine.stop()
                    del engine
                    self.available = True
                except Exception as exc:  # noqa: BLE001
                    self.available = False
                    self.last_error = str(exc)
                    log.error("TTS failed: %s", exc)
                    fut.set_exception(exc)
        finally:
            if com_initialised:
                try:
                    import pythoncom

                    pythoncom.CoUninitialize()
                except Exception:  # noqa: BLE001
                    pass

    def _submit(self, mode: str, text: str, rate: int) -> "Future[bytes]":
        self._ensure_worker()
        fut: "Future[bytes]" = Future()
        self._queue.put((mode, text[:5000], rate, fut))
        return fut

    def synthesize(self, text: str, rate: int = 185, timeout: float = 60.0) -> bytes:
        return self._submit("file", text, rate).result(timeout=timeout)

    def speak(self, text: str, rate: int = 185) -> "Future[bytes]":
        return self._submit("speak", text, rate)

    def status(self) -> dict[str, Any]:
        return {"available": self.available, "error": self.last_error}

    def shutdown(self) -> None:
        self._stop.set()


tts = TextToSpeech()
