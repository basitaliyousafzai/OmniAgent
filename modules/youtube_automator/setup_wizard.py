"""
Module 2: First-Run Interactive Setup & OAuth Wizard (setup_wizard.py).

Submodule 2.1 — AI Niche & Monetization Advisor: Connects to free LLM to recommend high-CPM evergreen niches.
Submodule 2.2 — Preference & Key Serializer: Captures niche, production mode, LLM provider, API keys into config/youtube_config.json.
Submodule 2.3 — One-Time OAuth 2.0 Handshake: Local browser authorization against client_secret.json saving token.json.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project and module paths are in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.youtube_automator.core.script_engine import LLMProviderRouter, ScriptEngine

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("omniagent.youtube.setup")

CONFIG_PATH = PROJECT_ROOT / "config" / "youtube_config.json"
CLIENT_SECRET_PATH = SCRIPT_DIR / "client_secret.json"
TOKEN_PATH = SCRIPT_DIR / "token.json"


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "niche": "AI Innovations & Breakthroughs",
        "production_mode": "solo",
        "llm_provider": "gemini",
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "ollama_model": "llama3.2:1b",
        "pexels_api_key": os.getenv("PEXELS_API_KEY", ""),
        "upload_hour_utc": 14,
        "privacy_status": "public",
        "auto_cleanup_cache": True
    }


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    log.info(f"Configuration saved to {CONFIG_PATH}")


def consult_ai_niches(provider: str, api_key: str) -> List[Dict[str, str]]:
    """
    Submodule 2.1 — AI Niche & Monetization Advisor.
    Consults chosen free LLM for 4 top-earning evergreen niches suitable for Shorts.
    """
    router = LLMProviderRouter(
        provider=provider,
        gemini_api_key=api_key if provider == "gemini" else "",
        openrouter_api_key=api_key if provider == "openrouter" else ""
    )

    prompt = (
        "Suggest exactly 4 high-CPM evergreen YouTube Shorts niches. Return valid JSON only with this structure:\n"
        "[\n"
        "  {\"name\": \"AI & Tech Breakthroughs\", \"cpm_estimate\": \"$18-$32\", \"why\": \"Rapid technological change fuels viral retention.\"},\n"
        "  {\"name\": \"Psychology & Human Behavior\", \"cpm_estimate\": \"$14-$25\", \"why\": \"Universal curiosity and high shareability.\"},\n"
        "  {\"name\": \"Personal Wealth & Micro-Investing\", \"cpm_estimate\": \"$25-$45\", \"why\": \"High commercial advertiser intent.\"},\n"
        "  {\"name\": \"Hidden History & World Paradoxes\", \"cpm_estimate\": \"$12-$22\", \"why\": \"Binge-watch storytelling hooks.\"}\n"
        "]\n"
        "Only output the JSON array, no commentary."
    )

    try:
        raw = router.generate(prompt)
        # Parse JSON
        import re
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        log.warning(f"Could not fetch AI niches from LLM ({e}), using curated defaults.")

    return [
        {"name": "AI Tools & Productivity Hacks", "cpm_estimate": "$20-$35", "why": "Massive viral interest from professionals."},
        {"name": "Dark Psychology & Cognitive Biases", "cpm_estimate": "$15-$25", "why": "High curiosity and watch-to-end retention."},
        {"name": "Billionaire Decision Mental Models", "cpm_estimate": "$22-$40", "why": "High advertiser value in business and finance."},
        {"name": "Futuristic Science & Space Anomalies", "cpm_estimate": "$12-$20", "why": "Broad audience fascination and loopability."}
    ]


def run_oauth_flow() -> bool:
    """
    Submodule 2.3 — One-Time OAuth 2.0 Handshake.
    Runs local webserver authorization against client_secret.json.
    """
    if not CLIENT_SECRET_PATH.exists():
        log.warning(
            f"client_secret.json not found at {CLIENT_SECRET_PATH}.\n"
            "To enable YouTube automated uploads:\n"
            "1. Visit https://console.cloud.google.com/apis/credentials\n"
            "2. Create an OAuth 2.0 Client ID (Desktop Application)\n"
            "3. Download the JSON file and save it as modules/youtube_automator/client_secret.json"
        )
        return False

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRET_PATH),
            scopes=["https://www.googleapis.com/auth/youtube.upload"]
        )
        print("\nOpening web browser for Google Account authentication...")
        creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
        log.info(f"✅ Authorization complete. Saved credentials to {TOKEN_PATH}")
        return True
    except Exception as e:
        log.error(f"OAuth flow failed: {e}")
        return False


def run_wizard_interactive():
    """Interactive command-line setup wizard."""
    print("=" * 65)
    print("  🎬 OmniAgent YouTube Automator — Setup & Monetization Wizard")
    print("=" * 65)

    config = load_config()

    # 1. LLM Provider
    print("\n[Step 1/5] Select Free LLM Provider:")
    print("  1) Google Gemini (Free Tier: 15 RPM / gemini-2.5-flash) [Recommended]")
    print("  2) OpenRouter (Free Tier Models)")
    print("  3) Local Ollama (100% Offline CPU: llama3.2:1b / qwen2.5:1.5b)")
    choice = input(f"Select [1-3] (Default: 1): ").strip()
    if choice == "2":
        config["llm_provider"] = "openrouter"
    elif choice == "3":
        config["llm_provider"] = "ollama"
    else:
        config["llm_provider"] = "gemini"

    # API Keys
    if config["llm_provider"] == "gemini":
        current = config.get("gemini_api_key", "")
        key = input(f"Enter Gemini API Key [{current[:8]}... if keep]: ").strip()
        if key:
            config["gemini_api_key"] = key
    elif config["llm_provider"] == "openrouter":
        current = config.get("openrouter_api_key", "")
        key = input(f"Enter OpenRouter API Key [{current[:8]}... if keep]: ").strip()
        if key:
            config["openrouter_api_key"] = key

    # Pexels API Key
    print("\n[Step 2/5] Stock Media Provider (Pexels - 100% Free 200 req/hr):")
    current_pexels = config.get("pexels_api_key", "")
    pexels_key = input(f"Enter Pexels API Key [{current_pexels[:8]}... if keep]: ").strip()
    if pexels_key:
        config["pexels_api_key"] = pexels_key

    # 3. Niche Consultation
    print("\n[Step 3/5] AI Niche Consultation:")
    print("Fetching high-CPM evergreen niches...")
    active_key = config.get("gemini_api_key") if config["llm_provider"] == "gemini" else config.get("openrouter_api_key")
    niches = consult_ai_niches(config["llm_provider"], active_key or "")
    for i, n in enumerate(niches, 1):
        print(f"  {i}) {n['name']} (Est. CPM: {n['cpm_estimate']}) — {n['why']}")
    print(f"  5) Custom Niche")

    niche_choice = input(f"Select niche [1-5] (Current: {config.get('niche', 'AI Innovations')}): ").strip()
    if niche_choice in ["1", "2", "3", "4"]:
        config["niche"] = niches[int(niche_choice) - 1]["name"]
    elif niche_choice == "5":
        custom = input("Enter custom niche name: ").strip()
        if custom:
            config["niche"] = custom

    # 4. Production Mode
    print("\n[Step 4/5] Production Format:")
    print("  1) solo    — High-energy single narrator (ChristopherNeural)")
    print("  2) podcast — Dual-host conversational debate (Christopher + Jenny)")
    print("  3) alternating — Cycles solo and podcast daily")
    mode_choice = input(f"Select mode [1-3] (Default: solo): ").strip()
    if mode_choice == "2":
        config["production_mode"] = "podcast"
    elif mode_choice == "3":
        config["production_mode"] = "alternating"
    else:
        config["production_mode"] = "solo"

    # Save
    save_config(config)

    # 5. YouTube OAuth
    print("\n[Step 5/5] YouTube Data API v3 Authorization:")
    if TOKEN_PATH.exists():
        print(f"✅ Existing authorization found at {TOKEN_PATH}.")
        reauth = input("Do you want to re-authenticate with Google? [y/N]: ").strip().lower()
        if reauth == "y":
            run_oauth_flow()
    else:
        run_oauth_flow()

    print("\n" + "=" * 65)
    print("🎉 OmniAgent YouTube Automator Setup Complete!")
    print(f"  Target Niche:    {config['niche']}")
    print(f"  Format:          {config['production_mode']}")
    print(f"  LLM Provider:    {config['llm_provider']}")
    print("  Test run command: python modules/youtube_automator/orchestrator.py --dry-run")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OmniAgent YouTube Automator Setup Wizard")
    parser.add_argument("--oauth-only", action="store_true", help="Run only the YouTube OAuth2 handshake")
    parser.add_argument("--save-json", type=str, help="Save settings directly from a JSON string")
    args = parser.parse_args()

    if args.oauth_only:
        run_oauth_flow()
    elif args.save_json:
        data = json.loads(args.save_json)
        cfg = load_config()
        cfg.update(data)
        save_config(cfg)
    else:
        run_wizard_interactive()
