"""Central configuration for SafeSaathi backend.

Every API key is OPTIONAL. With no keys the app still runs using the
built-in heuristic engine (perfect for a hackathon demo with no Wi-Fi).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ folder (one level above app/)
BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BACKEND_DIR / "app"
DATA_DIR = APP_DIR / "data"
EVAL_DIR = BACKEND_DIR / "data"
TTS_DIR = BACKEND_DIR / "static" / "audio"

load_dotenv(BACKEND_DIR / ".env")


def _s(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


# --- LLM -------------------------------------------------------------------
ANTHROPIC_API_KEY = _s("ANTHROPIC_API_KEY")
OPENAI_API_KEY = _s("OPENAI_API_KEY")
LLM_MODEL = _s("LLM_MODEL")
# Any OpenAI-compatible endpoint works here (Groq, OpenRouter, Ollama, LM Studio...)
# so the whole AI stack can run on a FREE key.
OPENAI_BASE_URL = _s("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
VISION_MODEL = _s("VISION_MODEL")           # must support image input
STT_MODEL = _s("STT_MODEL", "whisper-1")    # whisper-1 (OpenAI) | whisper-large-v3 (Groq)

# --- Link reputation -------------------------------------------------------
SAFE_BROWSING_KEY = _s("GOOGLE_SAFE_BROWSING_KEY")
VIRUSTOTAL_KEY = _s("VIRUSTOTAL_API_KEY")

# --- Guardian alerts -------------------------------------------------------
TWILIO_SID = _s("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = _s("TWILIO_AUTH_TOKEN")
TWILIO_FROM = _s("TWILIO_FROM")
GUARDIAN_DEFAULT = _s("GUARDIAN_DEFAULT")

# --- Server ----------------------------------------------------------------
CORS_ORIGINS = [o.strip() for o in _s("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

TTS_DIR.mkdir(parents=True, exist_ok=True)


def llm_info() -> dict:
    """Which engine is available right now (shown on the health endpoint)."""
    if ANTHROPIC_API_KEY:
        return {"engine": "anthropic", "model": LLM_MODEL or "claude-3-5-sonnet-latest"}
    if OPENAI_API_KEY:
        engine = "openai" if "api.openai.com" in OPENAI_BASE_URL else "openai-compatible"
        return {"engine": engine, "model": LLM_MODEL or "gpt-4o-mini"}
    return {"engine": "heuristic", "model": "safesaathi-rules-v1"}
