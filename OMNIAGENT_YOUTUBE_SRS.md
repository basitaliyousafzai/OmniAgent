# Software Requirements Specification (SRS)
## Autonomous YouTube Content Production & Publishing Subsystem for OmniAgent

- **Document Identifier:** `SRS-OMNI-YT-2026-V2`
- **Target Repository:** `https://github.com/basitaliyousafzai/OmniAgent`
- **Subsystem Namespace:** `modules/youtube_automator`
- **Target Execution Host:** Windows 10/11 x64 (Standard CPU-Only Environment, 0 MB VRAM)
- **Operational Cost Mandate:** $0.00 (100% Free Tier / Local Execution)

---

## 1. Executive Summary & System Purpose
The Autonomous YouTube Subsystem is an unattended, self-governing media production pipeline integrated into the `OmniAgent` ecosystem. Upon operating system boot, the subsystem wakes silently in the background, verifies daily publication state, mines high-retention niche topics, synthesizes human-grade multi-speaker or solo scripts, generates neural voiceovers, retrieves high-definition stock videos and photography, applies broadcast loudness normalization, renders a dynamic vertical video using pure CPU software encoding, and publishes the deliverable to YouTube via official Google APIs.

---

## 2. Global Hardware, Cost & Compliance Constraints

### 2.1 Zero-GPU / CPU-Only Enforcement
1. **No Hardware Acceleration:** The host hardware lacks a dedicated GPU (0 MB VRAM). The subsystem must never invoke NVIDIA CUDA, NVENC, Intel QSV, or AMD AMF hardware encoders.
2. **Software Transcoding:** All video processing must utilize the `libx264` software encoder configured with the `ultrafast` preset and `fastdecode` tuning.
3. **Thread & Memory Ceiling:** Every subprocess invocation must explicitly cap CPU utilization at `4 threads` (`-threads 4`) and keep total system RAM consumption strictly below `3.5 GB` so the host computer remains responsive for normal daily use.

### 2.2 Anti-Plagiarism & Anti-Spam Guardrails (YouTube Partner Program Compliance)
1. **Dynamic Narrative Architecture:** Every generated script must follow a strict **Hook (0–3s) ➔ Retention Body (3–35s) ➔ Payoff (35–45s)** structure.
2. **Banned Clichés:** The LLM prompt contract must explicitly forbid robotic AI openings such as *"Did you know?"*, *"Welcome back to the channel"*, *"In today's video"*, or *"Hey guys"*.
3. **Visual Pacing Rule:** No static image or single video clip may remain frozen on screen. Visual cuts must occur every `3.5 to 4.5 seconds`. Still photography must undergo continuous mathematical motion (Ken Burns zoom/pan transformation).
4. **Audio Authenticity:** Voiceovers must use high-prosody neural voices normalized to broadcast standards (`-14.0 LUFS`) layered over ducked royalty-free background music (`-22.0 dB`).

---

## 3. Complete Directory & File Hierarchy

```text
OmniAgent/
├── config/
│   └── youtube_config.json               # Persistent JSON configuration store
├── modules/
│   └── youtube_automator/
│       ├── __init__.py                   # Package initializer
│       ├── orchestrator.py               # Module 1: Master Pipeline Controller
│       ├── setup_wizard.py               # Module 2: First-Run Interactive Setup & OAuth
│       ├── requirements.txt              # Python dependency manifest
│       ├── client_secret.json            # Google Cloud OAuth 2.0 Client Credentials
│       ├── token.json                    # Cached & auto-refreshed OAuth 2.0 Bearer Token
│       ├── core/
│       │   ├── __init__.py               # Core subpackage initializer
│       │   ├── db_manager.py             # Module 3: SQLite WAL State & Idempotency Engine
│       │   ├── script_engine.py          # Module 4: Multi-Modal LLM Script & Prompt Architect
│       │   ├── voice_synthesizer.py      # Module 5: Neural TTS & Word-Boundary Subtitle Engine
│       │   ├── media_retriever.py        # Module 6: Stock Video, Image & Procedural Asset Engine
│       │   ├── audio_master.py           # Module 7: EBU R128 Acoustic Normalizer & Ducking Mixer
│       │   ├── video_compositor.py       # Module 8: CPU FFmpeg Filter-Graph & Subtitle Renderer
│       │   └── uploader.py               # Module 9: Resumable YouTube Data API v3 Publisher
│       └── storage/
│           ├── assets/
│           │   ├── fonts/                # Bold typography (Montserrat-Black.ttf)
│           │   └── music/                # Pre-cleared royalty-free MP3 background tracks
│           ├── cache/
│           │   ├── audio/                # Ephemeral turn audio and unmastered WAV/MP3 files
│           │   ├── raw_clips/            # Ephemeral downloaded Pexels MP4 clips
│           │   ├── images/               # Ephemeral downloaded Pexels JPG photography
│           │   └── subtitles/            # Ephemeral generated .srt / .ass caption files
│           ├── db/
│           │   └── youtube_agent.db      # Persistent SQLite database file
│           └── rendered/                 # Final 1080x1920 MP4 output archive
├── scripts/
│   ├── start_youtube.bat                 # Module 10.1: Environment & CLI Bootstrapper
│   └── run_youtube_silent.vbs            # Module 10.2: Zero-Window COM Background Wrapper
└── OMNIAGENT_YOUTUBE_SRS.md              # This specification document
```

---

## 4. Detailed Module & Submodule Specifications

---

### Module 1: Master Pipeline Orchestrator (`orchestrator.py`)
**Role:** Root lifecycle controller responsible for sequential execution, fault isolation, and resource cleanup.

#### Submodule 1.1: Pre-Flight Validator
- **Inputs:** File paths to `config/youtube_config.json`, `token.json`, and `storage/db/youtube_agent.db`.
- **Working Logic:** Verifies that initial setup has been completed and that FFmpeg is accessible on the system `PATH`. If unconfigured, logs a warning and terminates cleanly with exit code `0`.

#### Submodule 1.2: Idempotency Gatekeeper
- **Inputs:** Current local system date (`YYYY-MM-DD`).
- **Working Logic:** Queries Module 3 (`db_manager.py`) prior to initializing any LLM or network connections. If a video record for the current calendar date already has a status of `COMPLETED`, the orchestrator immediately aborts execution. This guarantees that rebooting the PC 10 times a day still results in only 1 daily upload.

#### Submodule 1.3: Sequential Workflow Dispatcher
- **Working Logic:** Executes Modules 4 through 9 in strict synchronous order, passing a unique `run_id` (`YYYYMMDD_HHMMSS`) and strongly-typed data dictionaries between stages.

#### Submodule 1.4: Ephemeral Cache Sanitizer
- **Working Logic:** Upon successful confirmation of YouTube publication, recursively deletes all temporary scratch files inside `storage/cache/audio/`, `storage/cache/raw_clips/`, `storage/cache/images/`, and `storage/cache/subtitles/` to prevent disk bloat while preserving the final video in `storage/rendered/`.

---

### Module 2: First-Run Interactive Setup Wizard (`setup_wizard.py`)
**Role:** One-time interactive console utility executed by the user during initial installation.

#### Submodule 2.1: AI Niche & CPM Consultant
- **Working Logic:** Connects to the user's chosen LLM provider (Google Gemini API Free Tier, OpenRouter Free Tier, or Local CPU Ollama) and generates 4 high-CPM, high-retention faceless YouTube niches with 1-sentence monetization explanations.

#### Submodule 2.2: Configuration Serializer
- **Working Logic:** Prompts the user once for:
  1. Target Niche Name
  2. Default Production Format (`solo` vs `podcast` vs `alternating`)
  3. LLM Provider (`gemini`, `openrouter`, or `ollama`)
  4. Free API Keys (Gemini/OpenRouter Key and Pexels API Key)
- Saves the validated structure to `config/youtube_config.json`.

#### Submodule 2.3: OAuth 2.0 Browser Handshake
- **Working Logic:** Reads `client_secret.json`, spins up a temporary local loopback listener (`InstalledAppFlow`), launches the user's default web browser for Google Account consent (`youtube.upload` scope), captures the authorization code, and writes the persistent `refresh_token` and `access_token` to `token.json`.

---

### Module 3: Database & State Ledger Manager (`core/db_manager.py`)
**Role:** Thread-safe SQLite persistence layer enforcing transactional integrity and audit logging.

#### Submodule 3.1: WAL Connection Manager
- **Working Logic:** Initializes `storage/db/youtube_agent.db` and executes `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;` to prevent database locking.

#### Submodule 3.2: Upload History Ledger (`daily_uploads` Table)
- **Schema Specification:**
  - `id` (INTEGER, Primary Key, Auto-Increment)
  - `upload_date` (TEXT, Unique, Not Null — Format: `YYYY-MM-DD`)
  - `title` (TEXT, Not Null)
  - `description` (TEXT, Not Null)
  - `tags` (TEXT, Not Null — JSON array serialized as string)
  - `production_mode` (TEXT, Not Null — `solo` or `podcast`)
  - `video_path` (TEXT, Not Null)
  - `youtube_id` (TEXT, Not Null)
  - `duration_sec` (REAL, Not Null)
  - `file_size_bytes` (INTEGER, Not Null)
  - `status` (TEXT, Not Null — `PENDING`, `COMPLETED`, `FAILED`)
  - `created_at` (TIMESTAMP, Default Current Timestamp)

#### Submodule 3.3: Topic Deduplication Registry (`topic_history` Table)
- **Working Logic:** Stores every previously generated video title and core hook concept. Provides the last 30 titles to Module 4 so the LLM never repeats the same topic or fact twice.

#### Submodule 3.4: Diagnostic Telemetry Logger (`execution_logs` Table)
- **Working Logic:** Records timestamped `INFO`, `WARNING`, `ERROR`, and `CRITICAL` events per submodule for headless troubleshooting.

---

### Module 4: Multi-Modal LLM Script & Prompt Architect (`core/script_engine.py`)
**Role:** Generates original, plagiarism-free scripts, metadata, and synchronized visual search cues.

#### Submodule 4.1: Provider Router
- **Working Logic:** Supports three zero-cost backends:
  1. **Google Gemini API (Free Tier):** Connects to `gemini-2.5-flash` / `gemini-2.0-flash`.
  2. **OpenRouter API (Free Tier):** Connects to `:free` endpoints.
  3. **Local CPU Ollama:** Connects to `http://127.0.0.1:11434` using ultra-lightweight 4-bit quantized CPU models (`llama3.2:1b` or `qwen2.5:1.5b`).

#### Submodule 4.2: Solo vs. Podcast Mode Formatter
- **Working Logic:**
  - **Solo Mode (`solo`):** Writes a fast-paced 80–95 word monologue assigned to a single authoritative speaker (`Narrator` using voice `en-US-ChristopherNeural`).
  - **Podcast Mode (`podcast`):** Writes a conversational back-and-forth debate/interview (4 to 6 turns total, 80–95 words combined) between two distinct personas:
    - `Host` (`en-US-ChristopherNeural`): Asks sharp, provocative questions or states common myths.
    - `Expert` (`en-US-JennyNeural`): Counters with counter-intuitive scientific, historical, or technical realities.

#### Submodule 4.3: Visual Cue & Asset Type Mapper
- **Working Logic:** Breaks the script timeline into 4 to 5 visual scenes. For each scene, selects whether it is best represented by a **Dynamic Video Clip (`video`)** or a **High-Resolution Still Photograph with Ken Burns Motion (`image`)**, and outputs a concrete 2–3 word physical search query (e.g., `"ancient roman coin"`, `"server room cables"`).

#### Submodule 4.4: Strict JSON Output Validator
- **Working Logic:** Enforces a strict JSON schema containing `mode`, `title` (max 50 chars), `description` (with 3 niche hashtags), `tags` (list of 5–8 SEO keywords), `dialogue` (array of speaker/voice/text objects), and `visual_prompts` (array of type/query objects). Includes regex sanitization and 3 automatic retries if the LLM outputs malformed JSON.

---

### Module 5: Neural Voice & Subtitle Aligner (`core/voice_synthesizer.py`)
**Role:** Converts script dialogue turns into natural human-like speech and generates word-accurate subtitle timing files.

#### Submodule 5.1: Multi-Voice Asynchronous Streamer
- **Working Logic:** Iterates through the `dialogue` array and invokes Microsoft `edge-tts` asynchronously for each turn using its assigned neural voice (`en-US-ChristopherNeural` or `en-US-JennyNeural`).

#### Submodule 5.2: Cumulative Timeline & Word-Boundary Calculator
- **Working Logic:** Captures real-time `WordBoundary` events emitted by `edge-tts`. Uses `ffprobe` to measure the exact millisecond duration of each completed speaker turn and adds a cumulative time offset to subsequent turns so multi-speaker podcast conversations maintain frame-accurate subtitle synchronization from start to finish.

#### Submodule 5.3: Short-Form Caption Chunker (`.srt` Generator)
- **Working Logic:** Groups word boundaries into punchy 2-to-4 word visual phrases so subtitles pop on screen dynamically like professional high-retention Shorts. Prefixes speaker turns in podcast mode and writes the output to `storage/cache/subtitles/captions_{run_id}.srt`.

#### Submodule 5.4: Raw Dialogue Concatenator
- **Working Logic:** Joins all individual turn `.mp3` files via FFmpeg's `concat` demuxer into a single continuous vocal track (`narration_raw_{run_id}.mp3`).

---

### Module 6: Stock Video, Image & Procedural Asset Engine (`core/media_retriever.py`)
**Role:** Downloads royalty-free vertical video footage and high-resolution still photography matching the script's visual prompts.

#### Submodule 6.1: Pexels Vertical Video Downloader
- **Working Logic:** Queries `https://api.pexels.com/videos/search` with `orientation=portrait`. Inspects the returned video file variants and selects the stream where `width <= height` and `height >= 1280` (HD vertical). Streams binary chunks to `storage/cache/raw_clips/`.

#### Submodule 6.2: Pexels High-Res Photography Downloader
- **Working Logic:** When a visual prompt specifies `type == "image"`, queries `https://api.pexels.com/v1/search` with `orientation=portrait` and downloads the high-resolution `large2x` JPG asset to `storage/cache/images/` for Ken Burns animation in Module 8.

#### Submodule 6.3: Offline / Zero-Result Procedural Fallback Generator
- **Working Logic:** If a search query returns zero results or the Pexels API experiences a timeout, automatically generates a 5-second procedural vertical animation canvas (`1080x1920` @ `30fps`) using FFmpeg's `lavfi` cellular automaton/gradient generator so the pipeline never crashes due to missing media.

---

### Module 7: Broadcast Audio Master & Ducking Mixer (`core/audio_master.py`)
**Role:** Polishes raw TTS audio into a studio-grade master soundtrack with balanced volume and background ambiance.

#### Submodule 7.1: EBU R128 Loudness Normalizer
- **Working Logic:** Passes `narration_raw_{run_id}.mp3` through FFmpeg's `loudnorm` acoustic filter configured to international broadcast standards:
  - Integrated Loudness Target (`I`): `-14.0 LUFS`
  - Loudness Range (`LRA`): `7.0 LU`
  - Maximum True Peak (`tp`): `-1.5 dBFS`
  - Sampling Rate: `44,100 Hz` stereo.

#### Submodule 7.2: Background Music Selector & Auto-Ducker
- **Working Logic:** Scans `storage/assets/music/` for pre-cleared `.mp3` or `.wav` tracks. Randomly selects one track, loops it infinitely (`-stream_loop -1`), and attenuates its gain to `volume=0.08` (`-22.0 dB` below the normalized voiceover) so the background score adds emotional weight without ever overpowering the spoken words.

#### Submodule 7.3: Master Soundtrack Combiner
- **Working Logic:** Blends the normalized voice track and ducked music track using FFmpeg's `amix` filter (`duration=first:dropout_transition=2`), exporting `storage/cache/audio/master_audio_{run_id}.mp3`. If the music folder is empty, cleanly outputs the normalized voice track alone.

---

### Module 8: CPU FFmpeg Video Compositor & Renderer (`core/video_compositor.py`)
**Role:** Transforms raw videos, still images, mastered audio, and subtitles into a cohesive, high-retention 9:16 vertical MP4 using strictly CPU-bound software rendering.

#### Submodule 8.1: Ken Burns Image Motion Engine (`zoompan`)
- **Working Logic:** Converts every downloaded static image (`.jpg`) into a smooth 4-second `1080x1920` (`30fps`) video segment by applying a continuous center-weighted zoom-in transformation from `100%` to `118%` scale:
  - Formula: `zoompan=z='min(zoom+0.0015,1.18)':d=120:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,format=yuv420p`

#### Submodule 8.2: Video Clip Geometry Standardizer
- **Working Logic:** Normalizes all downloaded video clips to exact `1080x1920` resolution, `1:1` pixel aspect ratio (`setsar=1`), `30fps` constant frame rate, and `yuv420p` color space using aspect-ratio-preserving scaling and center cropping (`scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920`).

#### Submodule 8.3: Dynamic Subtitle Burner
- **Working Logic:** Hardcodes the synchronized `.srt` captions onto the video canvas using the FFmpeg `subtitles` filter with custom ASS styling:
  - Typography: Bold (`Bold=1`), Size `20`
  - Primary Fill Color: High-contrast Yellow (`&H0000FFFF`)
  - Outline Stroke: Solid Black (`&H00000000`), Thickness `3px` (`BorderStyle=1,Outline=3`)
  - Placement: Bottom-center safe zone (`Alignment=2,MarginV=140`)—positioned high enough to never collide with YouTube Shorts title/channel overlays.

#### Submodule 8.4: CPU-Capped Final Muxer
- **Working Logic:** Concatenates the standardized video and Ken Burns segments, loops the visual sequence to match the exact length of `master_audio_{run_id}.mp3` (`-shortest`), applies the subtitle filter, and encodes the final `.mp4` to `storage/rendered/short_{run_id}.mp4` using:
  - `-c:v libx264 -preset ultrafast -tune fastdecode -threads 4 -c:a aac -b:a 192k`

---

### Module 9: Resumable YouTube Data API v3 Publisher (`core/uploader.py`)
**Role:** Authenticates with Google servers and uploads the finished MP4 with full SEO metadata.

#### Submodule 9.1: Silent OAuth Token Refresher
- **Working Logic:** Loads credentials from `token.json`. If the access token is expired, automatically invokes `credentials.refresh(Request())` using the stored refresh token and updates `token.json` on disk without prompting the user.

#### Submodule 9.2: Metadata & Compliance Builder
- **Working Logic:** Constructs the YouTube `videos.insert` request payload:
  - `snippet.title`: Script title (strictly capped at 100 chars; optimized for <50 chars).
  - `snippet.description`: Script description + hashtags.
  - `snippet.tags`: Script SEO tag array.
  - `snippet.categoryId`: `"28"` (Science & Technology) or user-configured category.
  - `status.privacyStatus`: `"public"` (or `"unlisted"` / `"private"` via config).
  - `status.selfDeclaredMadeForKids`: `False` (Mandatory COPPA flag).

#### Submodule 9.3: Chunked Resumable Upload Engine
- **Working Logic:** Streams the video file in `5 MB` resumable chunks (`MediaFileUpload(chunksize=5242880, resumable=True)`). Implements exponential backoff retry logic (`max_retries=5`) for HTTP `500`, `502`, `503`, and `504` transient network errors, returning the official YouTube `video_id` upon completion.

---

### Module 10: Windows Boot & Silent Background Daemon (`scripts/`)
**Role:** Ensures the entire pipeline executes automatically and invisibly when the user turns on their PC.

#### Submodule 10.1: Environment Bootstrapper (`scripts/start_youtube.bat`)
- **Working Logic:** Sets console encoding to UTF-8 (`chcp 65001`), changes the working directory to `modules/youtube_automator`, activates the local Python virtual environment (`venv\Scripts\activate.bat`) if present, and executes `python orchestrator.py`.

#### Submodule 10.2: Invisible COM Shell Wrapper (`scripts/run_youtube_silent.vbs`)
- **Working Logic:** Uses `WScript.Shell.Run` with window style `0` (`vbHide`) and `bWaitOnReturn = False` to invoke `start_youtube.bat`. When registered in Windows Task Scheduler with an **At Log On** trigger (delayed by 2 minutes for Wi-Fi initialization), the entire daily production run happens completely unseen in the background.

---

## 5. Failure Recovery & Fallback Matrix

| Failure Scenario | Affected Module | Automated Recovery Action |
| :--- | :--- | :--- |
| **Primary LLM Rate-Limited / Offline** | Module 4 (`script_engine.py`) | Automatically retries 3 times with 2s backoff; if local Ollama is offline, falls back to Gemini Free API if key is present. |
| **Malformed LLM JSON Response** | Module 4 (`script_engine.py`) | Extracts JSON block via regex `\{[\s\S]*\}`; if still invalid, re-prompts LLM up to 3 times. |
| **Pexels API Timeout / No Search Hits** | Module 6 (`media_retriever.py`) | Generates a 1080x1920 30fps procedural animated background clip via FFmpeg `lavfi` so video rendering never halts. |
| **Empty Background Music Folder** | Module 7 (`audio_master.py`) | Skips `amix` filter and outputs the EBU R128 normalized voiceover directly. |
| **Subtitle Filter Path Escaping Error** | Module 8 (`video_compositor.py`) | Escapes Windows drive colons and backslashes; if subtitle burn still fails, falls back to rendering clean video + audio without crashing. |
| **OAuth Access Token Expired** | Module 9 (`uploader.py`) | Silently exchanges `refresh_token` for a new `access_token` and overwrites `token.json`. |
| **Multiple PC Reboots in Same Day** | Module 1 (`orchestrator.py`) | Detects `COMPLETED` row for `CURRENT_DATE` in SQLite and exits in `<100ms` before any API or CPU work begins. |

---

## 6. Acceptance & Verification Criteria
1. **Zero Popups:** Running `wscript.exe scripts\run_youtube_silent.vbs` must spawn zero visible terminal or command prompt windows.
2. **CPU Thermal & Load Safety:** During Module 8 FFmpeg composition, `ffmpeg.exe` must never exceed `4 threads` and system RAM usage for the pipeline must remain under `3.5 GB`.
3. **Broadcast Audio Quality:** Final rendered MP4 audio stream must measure `-14.0 LUFS` (±1.0 LU) with background music cleanly ducked behind speech.
4. **Visual Quality:** Final rendered MP4 must be `1080x1920` resolution, `30.0 fps`, `yuv420p` pixel format, featuring alternating video b-roll and smooth Ken Burns moving photography with centered yellow/black subtitles.