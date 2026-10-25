"""
YouTube Automator Core — Pipeline processing modules.

Submodules:
    db_manager        — SQLite WAL state & idempotency engine
    script_engine     — Multi-modal LLM script & prompt architect
    voice_synthesizer — Neural dual-voice TTS & subtitle aligner
    media_retriever   — Stock video, image & procedural asset engine
    audio_master      — EBU R128 loudness & music ducking engine
    video_compositor  — CPU FFmpeg Ken Burns & subtitle renderer
    uploader          — Resumable YouTube Data API v3 publisher
"""
