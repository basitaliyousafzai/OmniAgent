"""Master Module 4: Multimodal Sensory Subsystem."""
from multimodal.coordinate_mapper import mapper, enable_dpi_awareness, list_monitors, Region
from multimodal.screen_capture import screen_capture, CaptureResult
from multimodal.stt import stt
from multimodal.tts import tts
from multimodal.vad_listener import vad_listener

__all__ = [
    "mapper", "enable_dpi_awareness", "list_monitors", "Region",
    "screen_capture", "CaptureResult", "stt", "tts", "vad_listener",
]
