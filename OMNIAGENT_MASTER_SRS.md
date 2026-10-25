# Master Software Requirements Specification (SRS) & Phased Implementation Plan
## Existing OmniAgent Stabilization + Autonomous YouTube Production Subsystem

- **Document ID:** `SRS-OMNI-MASTER-2026-V3`
- **Target Repository:** `https://github.com/basitaliyousafzai/OmniAgent`
- **Target Host Environment:** Windows 10/11 x64 (Standard CPU-Only System, 0 MB VRAM, <3.5 GB Peak RAM)
- **Operational Cost Mandate:** $0.00 (100% Free Cloud Tiers / Local CPU Execution)

---

## 1. Executive Summary & Dual Scope
This specification governs two synchronized engineering objectives inside the `OmniAgent` repository:
1. **Objective A — Existing System Audit, Stabilization & Refactoring:** Inspect the existing `OmniAgent` codebase (backend services, agent routers, dependency manifests, frontend UI components, and configuration loaders), diagnose and eliminate any broken imports, path mismatches, unhandled async exceptions, CORS/socket bottlenecks, or database lock issues, and unify its architecture.
2. **Objective B — Autonomous YouTube Production Engine Integration:** Build and embed a 100% autonomous, CPU-only YouTube Shorts & Podcast production subsystem (`modules/youtube_automator`) with full backend API hooks, a frontend control tab inside the OmniAgent UI, and silent Windows boot execution.

---

## 2. Global Hardware, Audio-Visual & Compliance Mandates

### 2.1 Hardware Ceiling (Zero VRAM / Pure CPU Mode)
- **No GPU Dependencies:** The host machine has no dedicated graphics card. Hardware encoders (`h264_nvenc`, `cuda`, `qsv`, `amf`) are strictly prohibited.
- **CPU Encoding Standard:** All video compilation must use FFmpeg software encoding (`-c:v libx264 -preset ultrafast -tune fastdecode -threads 4 -pix_fmt yuv420p`).
- **Memory & Thermal Protection:** Subprocesses must never exceed `4 CPU threads` or `3.5 GB RAM` so the host PC never lags during daily work.

### 2.2 Studio-Grade Audio & Visual Quality (Anti-AI / Anti-Strike Compliance)
- **Zero Robotic Clichés:** Scripts must never begin with *"Did you know"*, *"Welcome back"*, or *"In this video"*. Every script must open with a pattern-interrupt hook in the first 1.5 seconds.
- **Dual Production Formats:**
  - **Professional Solo Short (`solo`):** Fast-paced authoritative narrator (`en-US-ChristopherNeural`).
  - **2-Person Podcast (`podcast`):** Dynamic conversational exchange between `Host` (`en-US-ChristopherNeural`) and `Expert` (`en-US-JennyNeural`).
- **Broadcast Volume Mastering:** All speech must be normalized to EBU R128 broadcast standards (`-14.0 LUFS` integrated loudness, `-1.5 dBFS` true peak) and mixed with royalty-free background music ducked to `-22.0 dB` (`volume=0.08`).
- **Dynamic Visual Motion:** Never display frozen static images. Combine vertical HD video b-roll (`9:16`) with high-resolution still images animated via mathematical Ken Burns zoom/pan filters (`zoompan`), cutting scenes every `3.5 to 4.5 seconds` with burned lower-middle yellow/black bold subtitles.

---

## 3. Target Repository Architecture & Module Map

```text
OmniAgent/
├── config/
│   ├── system_config.json                # Core OmniAgent settings (audited & unified)
│   └── youtube_config.json               # YouTube subsystem configuration store
├── backend/                              # (Or existing OmniAgent server root)
│   ├── main.py / server.py               # Audited entrypoint with YouTube API routes mounted
│   └── routers/
│       └── youtube_router.py             # REST & SSE endpoints for YouTube UI management
├── frontend/                             # (Existing OmniAgent UI — audited & extended)
│   └── src/
│       └── components/
│           └── YouTubeDashboard.jsx      # Integrated UI panel for niche config, logs & preview
├── modules/
│   └── youtube_automator/
│       ├── __init__.py
│       ├── orchestrator.py               # Module 1: Master Pipeline Controller
│       ├── setup_wizard.py               # Module 2: First-Run Interactive Setup & OAuth
│       ├── requirements.txt              # Unified & conflict-free dependency manifest
│       ├── client_secret.json            # Google Cloud OAuth 2.0 Client Secret
│       ├── token.json                    # Persistent auto-refreshed OAuth Token
│       ├── core/
│       │   ├── __init__.py
│       │   ├── db_manager.py             # Module 3: SQLite WAL State & Idempotency Engine
│       │   ├── script_engine.py          # Module 4: Multi-Modal LLM Script & Prompt Architect
│       │   ├── voice_synthesizer.py      # Module 5: Neural Dual-Voice TTS & Subtitle Aligner
│       │   ├── media_retriever.py        # Module 6: Stock Video, Image & Procedural Engine
│       │   ├── audio_master.py           # Module 7: EBU R128 Loudness & Music Ducking Engine
│       │   ├── video_compositor.py       # Module 8: CPU FFmpeg Ken Burns & Subtitle Renderer
│       │   └── uploader.py               # Module 9: Resumable YouTube Data API v3 Publisher
│       └── storage/
│           ├── assets/
│           │   ├── fonts/                # Bold typography (Montserrat-Black.ttf)
│           │   └── music/                # Pre-cleared royalty-free MP3 tracks
│           ├── cache/
│           │   ├── audio/                # Temporary voice turns & unmastered audio
│           │   ├── raw_clips/            # Temporary downloaded portrait MP4 clips
│           │   ├── images/               # Temporary downloaded portrait JPG images
│           │   └── subtitles/            # Temporary synchronized .srt files
│           ├── db/
│           │   └── youtube_agent.db      # Persistent SQLite WAL database
│           └── rendered/                 # Final 1080x1920 MP4 output archive
├── scripts/
│   ├── start_youtube.bat                 # Module 10.1: Environment & CLI Bootstrapper
│   └── run_youtube_silent.vbs            # Module 10.2: Invisible Windows Boot Daemon
└── OMNIAGENT_MASTER_SRS.md               # This master specification document
```

---

## 4. Detailed Specifications of All Modules & Submodules

### Module 0: Existing OmniAgent Diagnostic & Remediation Layer
- **Submodule 0.1 — Dependency & Environment Harmonizer:** Audits existing `requirements.txt` / `package.json` files across `OmniAgent`, resolves version conflicts, removes dead imports, and ensures cross-platform Windows path safety (`pathlib.Path`).
- **Submodule 0.2 — Backend Route & Exception Hardening:** Fixes any unhandled promise/async rejections, broken tool bindings, or CORS misconfigurations in the existing `OmniAgent` core server, and mounts the new `/api/youtube/*` routes cleanly.
- **Submodule 0.3 — Frontend Dashboard Integration:** Fixes any existing UI state or layout bugs and adds a dedicated **YouTube Automator** view inside the OmniAgent interface displaying daily upload status, niche configuration, live pipeline logs, and rendered video previews.

### Module 1: Master Pipeline Orchestrator (`orchestrator.py`)
- **Submodule 1.1 — Pre-Flight & Dependency Verifier:** Confirms `youtube_config.json`, `token.json`, SQLite tables, and system `ffmpeg` / `ffprobe` binaries are ready before starting.
- **Submodule 1.2 — Daily Idempotency Gatekeeper:** Queries `db_manager.py` for today's local date (`YYYY-MM-DD`). If a `COMPLETED` upload already exists for today, exits in `<100ms` so multiple PC reboots never create duplicate videos.
- **Submodule 1.3 — Stage Coordinator & Fault Barrier:** Runs Modules 4 through 9 sequentially, capturing structured telemetry at every step.
- **Submodule 1.4 — Ephemeral Cache Cleaner:** Purges `storage/cache/*` after a confirmed YouTube upload so hard drive space is never wasted.

### Module 2: First-Run Interactive Setup Wizard (`setup_wizard.py`)
- **Submodule 2.1 — AI Niche & Monetization Advisor:** Connects to the user's chosen free LLM (Gemini Free API, OpenRouter Free Tier, or Local CPU Ollama) to recommend 4 high-CPM evergreen niches.
- **Submodule 2.2 — Preference & Key Serializer:** Captures target niche, production style (`solo`, `podcast`, or `alternating`), LLM provider, and free API keys (Gemini/OpenRouter + Pexels), saving them to `config/youtube_config.json`.
- **Submodule 2.3 — One-Time OAuth 2.0 Handshake:** Runs local browser authorization against `client_secret.json` (`youtube.upload` scope) and saves the auto-refreshing `token.json`.

### Module 3: SQLite WAL State & Idempotency Engine (`core/db_manager.py`)
- **Submodule 3.1 — Concurrent WAL Engine:** Configures SQLite with `PRAGMA journal_mode=WAL;` so the background daemon and OmniAgent UI can read/write simultaneously without `database is locked` errors.
- **Submodule 3.2 — Daily Upload Ledger (`daily_uploads`):** Tracks `id`, `upload_date` (UNIQUE), `title`, `description`, `tags`, `production_mode`, `video_path`, `youtube_id`, `duration_sec`, `file_size_bytes`, `status`, and `created_at`.
- **Submodule 3.3 — Anti-Repetition Topic Memory (`topic_history`):** Stores past titles and hooks, injecting the last 30 topics as negative constraints into Module 4 so the agent never repeats an idea.
- **Submodule 3.4 — Execution Telemetry Table (`execution_logs`):** Logs granular step-by-step progress for the OmniAgent UI log viewer.

### Module 4: Multi-Modal LLM Script & Prompt Architect (`core/script_engine.py`)
- **Submodule 4.1 — Multi-Provider Free LLM Router:** Supports Google Gemini Free Tier (`gemini-2.5-flash` / `gemini-2.0-flash`), OpenRouter Free Models, and Local CPU Ollama (`llama3.2:1b` / `qwen2.5:1.5b`).
- **Submodule 4.2 — Solo & Podcast Dialogue Generator:**
  - `solo`: 80–95 word rapid-fire monologue (`Narrator` -> `en-US-ChristopherNeural`).
  - `podcast`: 80–95 word conversational debate (`Host` -> `en-US-ChristopherNeural` asking sharp questions; `Expert` -> `en-US-JennyNeural` delivering counter-intuitive insights).
- **Submodule 4.3 — Scene Visual Mapper:** Generates 4 to 5 scene cues alternating between `video` (portrait b-roll) and `image` (high-res portrait photo for Ken Burns motion) with concrete 2–3 word search queries.
- **Submodule 4.4 — Strict JSON Schema Validator:** Enforces valid JSON output (`mode`, `title`, `description`, `tags`, `dialogue`, `visual_prompts`) with automatic regex extraction and 3-attempt self-healing retries.

### Module 5: Neural Dual-Voice TTS & Subtitle Aligner (`core/voice_synthesizer.py`)
- **Submodule 5.1 — Multi-Speaker Async Synthesizer:** Streams each dialogue turn through `edge-tts` using its assigned voice profile.
- **Submodule 5.2 — Cumulative Turn Offset Calculator:** Measures exact turn duration via `ffprobe` and shifts `WordBoundary` timestamps across speaker changes so multi-voice podcast subtitles never drift out of sync.
- **Submodule 5.3 — Retention Caption Formatter (`.srt`):** Groups word boundaries into 2-to-4 word punchy captions and writes `storage/cache/subtitles/captions_{run_id}.srt`.
- **Submodule 5.4 — Seamless Audio Concatenator:** Joins individual turn audio files into `narration_raw_{run_id}.mp3`.

### Module 6: Stock Video, Image & Procedural Asset Engine (`core/media_retriever.py`)
- **Submodule 6.1 — Pexels HD Portrait Video Fetcher:** Downloads 9:16 vertical video clips (`width <= height`, `height >= 1280`) matching `video` prompts.
- **Submodule 6.2 — Pexels High-Res Portrait Image Fetcher:** Downloads `large2x` vertical JPG photographs matching `image` prompts.
- **Submodule 6.3 — Zero-Failure Procedural Fallback:** If offline or if a search returns zero results, automatically synthesizes a 1080x1920 30fps animated background via FFmpeg `lavfi` so rendering never fails.

### Module 7: Broadcast Audio Master & Ducking Mixer (`core/audio_master.py`)
- **Submodule 7.1 — EBU R128 Loudness Normalizer:** Applies FFmpeg `loudnorm=I=-14.0:LRA=7.0:tp=-1.5` to `narration_raw_{run_id}.mp3` so speech volume is crisp, consistent, and never clips.
- **Submodule 7.2 — Background Music Loop & Auto-Ducker:** Selects a royalty-free track from `storage/assets/music/`, loops it (`-stream_loop -1`), and attenuates its volume to `volume=0.08` (`-22.0 dB` below speech).
- **Submodule 7.3 — Master Track Mixer:** Blends normalized voice and ducked music via `amix=inputs=2:duration=first:dropout_transition=2` into `master_audio_{run_id}.mp3` (or outputs normalized speech cleanly if no music file is present).

### Module 8: CPU FFmpeg Video Compositor & Renderer (`core/video_compositor.py`)
- **Submodule 8.1 — Ken Burns Image Motion Engine:** Animates every static `.jpg` into a smooth 4-second `1080x1920` (`30fps`) video clip using `zoompan=z='min(zoom+0.0015,1.18)':d=120:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p`.
- **Submodule 8.2 — B-Roll Clip Standardizer:** Scales, center-crops, and normalizes all video clips to `1080x1920`, `30fps`, `setsar=1`, `yuv420p`.
- **Submodule 8.3 — Safe-Zone Subtitle Burner:** Burns `.srt` captions onto the video canvas using bold yellow/white typography with a 3px black stroke (`FontSize=20,Bold=1,PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Alignment=2,MarginV=140`).
- **Submodule 8.4 — CPU-Capped Master Encoder:** Concatenates all visual segments, syncs `master_audio_{run_id}.mp3` (`-shortest`), and outputs `storage/rendered/short_{run_id}.mp4` using `-c:v libx264 -preset ultrafast -tune fastdecode -threads 4 -c:a aac -b:a 192k`.

### Module 9: Resumable YouTube Data API v3 Publisher (`core/uploader.py`)
- **Submodule 9.1 — Silent Token Refresher:** Automatically refreshes expired OAuth tokens via `token.json` without user interaction.
- **Submodule 9.2 — SEO Metadata & Compliance Injector:** Populates title, description, tags, `categoryId="28"`, `privacyStatus="public"`, and `selfDeclaredMadeForKids=False`.
- **Submodule 9.3 — Chunked Resumable Uploader:** Uploads the MP4 in 5 MB resumable chunks with exponential backoff retry handling.

### Module 10: Silent Windows Boot Automation (`scripts/`)
- **Submodule 10.1 — Batch Bootstrapper (`scripts/start_youtube.bat`):** Activates the Python environment and triggers `orchestrator.py`.
- **Submodule 10.2 — Invisible COM Daemon (`scripts/run_youtube_silent.vbs`):** Wraps `start_youtube.bat` in `WScript.Shell.Run(..., 0, False)` so Windows Task Scheduler runs the pipeline at boot with zero popups or command windows.

---

## 5. Phased Implementation Plan (Execution Roadmap for AI Agent)

### Phase 1: Existing OmniAgent Codebase Audit & Stabilization
1. Scan the entire repository (`OmniAgent`) for syntax errors, broken imports, missing environment variables, outdated dependencies, or path bugs.
2. Fix any identified backend, agent-loop, or frontend issues so the base `OmniAgent` platform starts and runs cleanly.

### Phase 2: Database Layer, Configuration & Setup Wizard
1. Create the directory hierarchy under `modules/youtube_automator/` and `config/`.
2. Implement `core/db_manager.py` with SQLite WAL mode, `daily_uploads`, `topic_history`, and `execution_logs` tables.
3. Implement `setup_wizard.py` for one-time niche consultation, config creation, and Google OAuth `token.json` generation.

### Phase 3: Intelligence & Audio Engineering Pipeline
1. Implement `core/script_engine.py` supporting both `solo` and `podcast` modes with strict JSON validation and topic deduplication.
2. Implement `core/voice_synthesizer.py` with dual-speaker `edge-tts` synthesis and cumulative `.srt` subtitle timestamp alignment.
3. Implement `core/audio_master.py` with EBU R128 (`-14 LUFS`) normalization and `-22 dB` background music ducking.

### Phase 4: Visual Retrieval & CPU-Only Video Composition
1. Implement `core/media_retriever.py` for Pexels portrait videos, high-res portrait images, and FFmpeg `lavfi` procedural fallbacks.
2. Implement `core/video_compositor.py` with `zoompan` Ken Burns image motion, 1080x1920 30fps standardization, burned subtitles, and `-preset ultrafast -threads 4` CPU encoding.

### Phase 5: YouTube Publisher, Orchestrator & OmniAgent UI Integration
1. Implement `core/uploader.py` (resumable OAuth2 upload) and `orchestrator.py` (daily idempotency check, full pipeline execution, and cache cleanup).
2. Create `scripts/start_youtube.bat` and `scripts/run_youtube_silent.vbs` for invisible Windows startup execution.
3. Mount `/api/youtube` endpoints in the `OmniAgent` backend and add the YouTube status/control panel to the `OmniAgent` frontend UI.

### Phase 6: End-to-End Verification & Self-Test
1. Verify all Python imports, syntax, SQLite table creation, and FFmpeg filter syntax.
2. Run a dry-run health check across the entire codebase to confirm zero unresolved errors.