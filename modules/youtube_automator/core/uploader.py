"""
Module 9: Resumable YouTube Data API v3 Publisher (core/uploader.py).

Submodule 9.1 — Silent Token Refresher: Refreshes expired OAuth tokens via token.json without user interaction.
Submodule 9.2 — SEO Metadata & Compliance Injector: Sets title, description, tags, categoryId="28", privacy="public", selfDeclaredMadeForKids=False.
Submodule 9.3 — Chunked Resumable Uploader: 5 MB chunked upload with exponential backoff retries.
"""
from __future__ import annotations

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

log = logging.getLogger("omniagent.youtube.uploader")

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

GOOGLE_API_AVAILABLE = True

YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# Resumable upload chunk size: 5 MB (must be multiple of 256 KB)
CHUNK_SIZE = 5 * 1024 * 1024
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
MAX_RETRIES = 5


class YouTubeUploader:
    """
    Submodule 9.1 & 9.3 — Resumable YouTube Data API v3 Publisher with automatic token refresh.
    """

    def __init__(
        self,
        token_path: Optional[Path] = None,
        client_secret_path: Optional[Path] = None
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.token_path = Path(token_path) if token_path else base_dir / "token.json"
        self.client_secret_path = Path(client_secret_path) if client_secret_path else base_dir / "client_secret.json"

    def get_authenticated_service(self):
        """
        Submodule 9.1 — Silent Token Refresher.
        Loads existing token.json, refreshes if expired, and returns the YouTube service.
        """
        if not GOOGLE_API_AVAILABLE:
            raise RuntimeError("google-api-python-client / google-auth packages not installed.")

        creds = None
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), YOUTUBE_UPLOAD_SCOPE)
            except Exception as e:
                log.error(f"Failed to load credentials from {self.token_path}: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                log.info("Refreshing expired YouTube OAuth credentials...")
                creds.refresh(Request())
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
                log.info("Successfully refreshed and saved token.json.")
            else:
                if not self.client_secret_path.exists():
                    raise FileNotFoundError(
                        f"client_secret.json not found at {self.client_secret_path}. "
                        "Run setup_wizard.py to configure YouTube OAuth credentials."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secret_path), YOUTUBE_UPLOAD_SCOPE
                )
                creds = flow.run_local_server(port=0)
                with open(self.token_path, "w", encoding="utf-8") as token_file:
                    token_file.write(creds.to_json())
                log.info("Saved new token.json credentials.")

        return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=creds)

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: list[str],
        privacy_status: str = "public",
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Dict[str, Any]:
        """
        Submodule 9.2 & 9.3 — SEO Metadata & Resumable Chunked Uploader.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file does not exist: {video_path}")

        file_size = video_path.stat().st_size
        log.info(f"Preparing upload for {video_path.name} ({file_size / (1024*1024):.2f} MB)...")

        # Submodule 9.2 — SEO Metadata & Compliance Injector
        # Standardize tags: ensure Shorts tags are present
        std_tags = list(tags)
        for tag in ["Shorts", "YouTubeShorts"]:
            if tag not in std_tags:
                std_tags.append(tag)

        # Append default hashtags to description if not present
        if "#shorts" not in description.lower():
            description = f"{description.strip()}\n\n#shorts #youtubeshorts"

        body = {
            "snippet": {
                "title": title[:100],  # YouTube title limit 100 chars
                "description": description[:5000],
                "tags": std_tags[:30],
                "categoryId": "28",  # Science & Technology (High CPM)
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
                "embeddable": True,
                "license": "youtube"
            }
        }

        # Check if dry-run / simulation needed (e.g. no credentials present)
        if not self.token_path.exists():
            log.warning(
                "token.json not present! Upload skipped (dry-run mode). "
                "Simulating successful upload for pipeline validation."
            )
            simulated_id = f"sim_{int(time.time())}"
            if progress_callback:
                progress_callback(100.0)
            return {
                "id": simulated_id,
                "url": f"https://www.youtube.com/shorts/{simulated_id}",
                "simulated": True,
                "title": title,
                "status": privacy_status
            }

        youtube = self.get_authenticated_service()

        media = MediaFileUpload(
            str(video_path),
            chunksize=CHUNK_SIZE,
            resumable=True,
            mimetype="video/mp4"
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        log.info("Starting chunked resumable upload to YouTube...")
        response = None
        retry_count = 0

        while response is None:
            try:
                status, response = request.next_chunk()
                if status:
                    pct = float(status.progress() * 100)
                    log.info(f"Upload progress: {pct:.1f}%")
                    if progress_callback:
                        progress_callback(pct)
            except HttpError as ex:
                if ex.resp.status in RETRIABLE_STATUS_CODES:
                    retry_count += 1
                    if retry_count > MAX_RETRIES:
                        raise RuntimeError(f"YouTube upload failed after {MAX_RETRIES} retries: {ex}")
                    sleep_sec = (2 ** retry_count) + random.random()
                    log.warning(f"Retrying upload in {sleep_sec:.2f}s due to HTTP {ex.resp.status}...")
                    time.sleep(sleep_sec)
                else:
                    raise

        video_id = response.get("id", "")
        log.info(f"✅ Video successfully published! Video ID: {video_id}")
        if progress_callback:
            progress_callback(100.0)

        return {
            "id": video_id,
            "url": f"https://www.youtube.com/shorts/{video_id}",
            "simulated": False,
            "title": title,
            "status": privacy_status,
            "raw_response": response
        }
