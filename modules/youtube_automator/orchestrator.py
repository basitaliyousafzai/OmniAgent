"""
Module 1: Master Pipeline Orchestrator (modules/youtube_automator/orchestrator.py).

Submodule 1.1 — Pre-Flight & Dependency Verifier (ffmpeg, ffprobe, config, database).
Submodule 1.2 — Daily Idempotency Gatekeeper (<100ms exit if today's upload completed).
Submodule 1.3 — Stage Coordinator & Fault Barrier (Modules 4 -> 5 -> 6 -> 7 -> 8 -> 9).
Submodule 1.4 — Ephemeral Cache Cleaner (purges cache on success to save disk).
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# Ensure project root is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.youtube_automator.core.audio_master import AudioMaster
from modules.youtube_automator.core.db_manager import DatabaseManager
from modules.youtube_automator.core.media_retriever import MediaRetriever
from modules.youtube_automator.core.script_engine import ScriptEngine
from modules.youtube_automator.core.uploader import YouTubeUploader
from modules.youtube_automator.core.video_compositor import VideoCompositor
from modules.youtube_automator.core.voice_synthesizer import VoiceSynthesizer

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [orchestrator]: %(message)s"
)
log = logging.getLogger("omniagent.youtube.orchestrator")


class MasterOrchestrator:
    """
    Submodule 1.1 - 1.4 — Autonomous Pipeline Controller.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        db_path: Optional[Path] = None
    ) -> None:
        self.config_path = Path(config_path) if config_path else PROJECT_ROOT / "config" / "youtube_config.json"
        self.base_dir = SCRIPT_DIR
        self.storage_dir = self.base_dir / "storage"
        self.cache_dir = self.storage_dir / "cache"
        self.rendered_dir = self.storage_dir / "rendered"
        self.db_path = Path(db_path) if db_path else self.storage_dir / "db" / "youtube_agent.db"

        # Initialize State & Database Engine
        self.db: DatabaseManager = DatabaseManager(self.db_path)

        # Ensure directories
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.rendered_dir.mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "audio").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "raw_clips").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "images").mkdir(parents=True, exist_ok=True)
        (self.cache_dir / "subtitles").mkdir(parents=True, exist_ok=True)

    def load_config(self) -> Dict[str, Any]:
        """Loads and returns the YouTube automator config."""
        if not self.config_path.exists():
            log.warning(f"Config not found at {self.config_path}. Using system defaults.")
            return {
                "niche": "AI Innovations & Breakthroughs",
                "production_mode": "solo",
                "llm_provider": "gemini",
                "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
                "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
                "ollama_model": "llama3.2:1b",
                "pexels_api_key": os.getenv("PEXELS_API_KEY", ""),
                "privacy_status": "public",
                "auto_cleanup_cache": True
            }
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Error reading config: {e}. Falling back to default.")
            return {}

    def preflight_check(self) -> bool:
        """
        Submodule 1.1 — Pre-Flight & Dependency Verifier.
        Verifies FFmpeg, FFprobe, and essential system dependencies.
        """
        log.info("Running Submodule 1.1 Pre-Flight Check...")
        ffmpeg_bin = shutil.which("ffmpeg")
        ffprobe_bin = shutil.which("ffprobe")

        if not ffmpeg_bin or not ffprobe_bin:
            local_appdata = os.getenv("LOCALAPPDATA", "")
            candidates = [
                Path(r"C:\ffmpeg\bin"),
                Path(r"C:\Program Files\ffmpeg\bin"),
                Path(local_appdata) / "Microsoft" / "WinGet" / "Links",
                Path(local_appdata) / "Programs" / "ffmpeg" / "bin",
            ]
            winget_pkg = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
            if winget_pkg.exists():
                for found in winget_pkg.glob("**/ffmpeg.exe"):
                    candidates.append(found.parent)

            for cand in candidates:
                if (cand / "ffmpeg.exe").exists():
                    os.environ["PATH"] = f"{cand};{os.environ.get('PATH', '')}"
                    log.info(f"Discovered FFmpeg at: {cand}")
                    ffmpeg_bin = shutil.which("ffmpeg")
                    ffprobe_bin = shutil.which("ffprobe")
                    break

        if not ffmpeg_bin:
            log.error("FFmpeg binary not found in system PATH. Video composition requires FFmpeg.")
            return False
        if not ffprobe_bin:
            log.error("FFprobe binary not found in system PATH. Audio analysis requires FFprobe.")
            return False

        log.info(f"FFmpeg verified: {ffmpeg_bin}")
        log.info(f"FFprobe verified: {ffprobe_bin}")
        return True

    def check_daily_idempotency(self, today_date: str, force: bool = False) -> bool:
        """
        Submodule 1.2 — Daily Idempotency Gatekeeper.
        Returns True if we can proceed, False if today's upload already completed.
        """
        if force:
            log.info("Force flag passed. Bypassing daily idempotency check.")
            return True

        if self.db.is_today_uploaded(today_date):
            log.info(f"⚡ Daily Idempotency Active: Upload for {today_date} already marked COMPLETED. Exiting gracefully in <100ms.")
            return False
        return True

    def cleanup_ephemeral_cache(self, run_id: str) -> None:
        """
        Submodule 1.4 — Ephemeral Cache Cleaner.
        Removes temporary visual assets, raw turns, and subtitles generated for this run.
        """
        log.info(f"Running Submodule 1.4: Ephemeral Cache Cleaner for run {run_id}...")
        try:
            for subfolder in ["audio", "raw_clips", "images", "subtitles"]:
                target_folder = self.cache_dir / subfolder
                if target_folder.exists():
                    for item in target_folder.glob(f"*{run_id}*"):
                        try:
                            if item.is_file():
                                item.unlink(missing_ok=True)
                            elif item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                        except Exception as e:
                            log.debug(f"Could not delete {item}: {e}")
            log.info("Cache successfully purged.")
        except Exception as e:
            log.warning(f"Cache cleanup encountered a non-fatal error: {e}")

    async def run_pipeline(
        self,
        force: bool = False,
        dry_run: bool = False,
        custom_topic: Optional[str] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Submodule 1.3 — Stage Coordinator & Fault Barrier.
        Executes Modules 4 through 9 sequentially with execution telemetry.
        """
        today_date = datetime.date.today().isoformat()
        run_id = f"{today_date.replace('-', '')}_{uuid.uuid4().hex[:6]}"

        def emit(stage: str, percent: int, detail: str):
            log.info(f"[{percent}%] Stage: {stage} - {detail}")
            self.db.log_event(run_id, stage, "RUNNING" if percent < 100 else "SUCCESS", detail)
            if progress_callback:
                try:
                    progress_callback(stage, percent, detail)
                except Exception:
                    pass

        emit("PREFLIGHT", 2, "Checking binaries and database health")

        # Preflight
        if not self.preflight_check():
            self.db.log_event(run_id, "PREFLIGHT", "FAILED", "FFmpeg/FFprobe binaries missing")
            raise RuntimeError("Pre-flight check failed: FFmpeg/FFprobe binaries not found in PATH.")

        # Idempotency Gatekeeper
        emit("IDEMPOTENCY_CHECK", 5, f"Checking daily ledger for {today_date}")
        if not self.check_daily_idempotency(today_date, force=force):
            emit("IDEMPOTENCY_CHECK", 100, "Already completed for today. Exiting.")
            return {"status": "SKIPPED", "reason": "Already uploaded today", "date": today_date}

        config = self.load_config()
        niche = config.get("niche", "AI Innovations & Breakthroughs")
        production_mode = config.get("production_mode", "solo")

        # Determine alternating mode if configured
        if production_mode == "alternating":
            day_num = datetime.date.today().toordinal()
            production_mode = "podcast" if day_num % 2 == 0 else "solo"

        # Record daily upload initialization
        self.db.record_daily_upload_start(
            upload_date=today_date,
            production_mode=production_mode
        )

        try:
            # ==============================================================
            # STAGE 1: SCRIPT ENGINE (Module 4)
            # ==============================================================
            emit("SCRIPT_ENGINE", 12, "Consulting LLM and generating high-retention script...")
            recent_topics = self.db.get_recent_topics(limit=30)

            script_engine = ScriptEngine(
                llm_provider=config.get("llm_provider", "gemini"),
                gemini_api_key=config.get("gemini_api_key"),
                openrouter_api_key=config.get("openrouter_api_key"),
                ollama_model=config.get("ollama_model", "llama3.2:1b")
            )

            script_data = await script_engine.generate_script(
                niche=niche,
                mode=production_mode,
                topic=custom_topic,
                past_topics=recent_topics
            )

            title = script_data.get("title", f"The {niche} Breakthrough")
            hook = script_data.get("dialogue", [{}])[0].get("text", "")[:120]
            self.db.record_topic(title, niche, hook)
            emit("SCRIPT_ENGINE", 25, f"Generated script: '{title}'")

            # ==============================================================
            # STAGE 2: VOICE SYNTHESIZER (Module 5)
            # ==============================================================
            emit("VOICE_SYNTHESIS", 30, f"Synthesizing neural voice ({production_mode} mode)...")
            voice_synth = VoiceSynthesizer(output_dir=self.cache_dir / "audio")
            voice_result = await voice_synth.synthesize_script(
                script_data=script_data,
                run_id=run_id
            )
            raw_audio_path = voice_result["audio_path"]
            srt_path = voice_result["srt_path"]
            emit("VOICE_SYNTHESIS", 45, f"Speech synthesized. Duration: {voice_result['duration_sec']:.2f}s")

            # ==============================================================
            # STAGE 3: VISUAL RETRIEVAL (Module 6)
            # ==============================================================
            emit("MEDIA_RETRIEVAL", 50, "Fetching vertical b-roll clips & high-res images...")
            retriever = MediaRetriever(
                cache_dir=self.cache_dir,
                pexels_api_key=config.get("pexels_api_key")
            )
            visual_assets = await retriever.retrieve_visual_assets(
                visual_prompts=script_data.get("visual_prompts", []),
                run_id=run_id
            )
            emit("MEDIA_RETRIEVAL", 62, f"Retrieved {len(visual_assets)} visual media segments.")

            # ==============================================================
            # STAGE 4: AUDIO MASTERING (Module 7)
            # ==============================================================
            emit("AUDIO_MASTERING", 68, "Applying EBU R128 loudness normalization & music ducking...")
            audio_master = AudioMaster(
                assets_dir=self.storage_dir / "assets",
                cache_dir=self.cache_dir
            )
            master_audio_path = audio_master.master_soundtrack(
                raw_speech_path=raw_audio_path,
                run_id=run_id
            )
            emit("AUDIO_MASTERING", 75, "Master audio track finalized.")

            # ==============================================================
            # STAGE 5: VIDEO COMPOSITION & RENDERING (Module 8)
            # ==============================================================
            emit("VIDEO_COMPOSITION", 80, "Composing Ken Burns motion, burning subtitles & CPU encoding...")
            compositor = VideoCompositor(
                output_dir=self.rendered_dir,
                cache_dir=self.cache_dir
            )
            final_mp4 = compositor.render_short(
                visual_assets=visual_assets,
                audio_path=master_audio_path,
                srt_path=srt_path,
                run_id=run_id
            )
            file_size_mb = final_mp4.stat().st_size / (1024 * 1024)
            emit("VIDEO_COMPOSITION", 90, f"Rendered 1080x1920 MP4: {final_mp4.name} ({file_size_mb:.2f} MB)")

            # ==============================================================
            # STAGE 6: RESUMABLE YOUTUBE UPLOADER (Module 9)
            # ==============================================================
            emit("YOUTUBE_UPLOAD", 92, "Publishing to YouTube Data API v3...")
            uploader = YouTubeUploader()

            if dry_run:
                log.info("Dry-run active. Skipping actual YouTube upload call.")
                upload_res = {
                    "id": f"dry_run_{run_id}",
                    "url": f"https://www.youtube.com/shorts/dry_run_{run_id}",
                    "simulated": True
                }
            else:
                upload_res = uploader.upload_video(
                    video_path=final_mp4,
                    title=title,
                    description=script_data.get("description", ""),
                    tags=script_data.get("tags", []),
                    privacy_status=config.get("privacy_status", "public")
                )

            youtube_id: str = str(upload_res.get("id") or "")
            emit("YOUTUBE_UPLOAD", 98, f"Successfully uploaded: {upload_res.get('url')}")

            # Mark in database as COMPLETED
            self.db.complete_daily_upload(
                upload_date=today_date,
                title=title,
                description=script_data.get("description", ""),
                tags=json.dumps(script_data.get("tags", [])),
                video_path=str(final_mp4),
                youtube_id=youtube_id,
                duration_sec=voice_result["duration_sec"],
                file_size_bytes=final_mp4.stat().st_size
            )

            # Ephemeral Cache Purge (Submodule 1.4)
            if config.get("auto_cleanup_cache", True):
                self.cleanup_ephemeral_cache(run_id)

            emit("PIPELINE_COMPLETE", 100, f"Shorts production finished. Video ID: {youtube_id}")

            return {
                "status": "COMPLETED",
                "date": today_date,
                "run_id": run_id,
                "title": title,
                "video_path": str(final_mp4),
                "youtube_id": youtube_id,
                "youtube_url": upload_res.get("url"),
                "duration_sec": voice_result["duration_sec"],
                "file_size_mb": file_size_mb,
                "mode": production_mode
            }

        except Exception as ex:
            log.error(f"❌ Pipeline failed: {ex}", exc_info=True)
            self.db.fail_daily_upload(today_date, str(ex))
            self.db.log_event(run_id, "FATAL_ERROR", "FAILED", str(ex))
            raise


def main():
    parser = argparse.ArgumentParser(description="OmniAgent YouTube Production Orchestrator")
    parser.add_argument("--force", action="store_true", help="Bypass daily idempotency check")
    parser.add_argument("--dry-run", action="store_true", help="Render video without YouTube upload")
    parser.add_argument("--topic", type=str, default=None, help="Custom topic to override LLM selection")
    args = parser.parse_args()

    orchestrator = MasterOrchestrator()
    try:
        result = asyncio.run(orchestrator.run_pipeline(
            force=args.force,
            dry_run=args.dry_run,
            custom_topic=args.topic
        ))
        print("\n" + json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nPipeline execution failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
