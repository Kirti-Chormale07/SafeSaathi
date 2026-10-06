"""Text-to-speech via gTTS (Google Translate voice) in en / hi / mr.

Audio files are cached in backend/static/audio so repeated demo runs are
instant and work even if gTTS is briefly unreachable.
"""
import hashlib

from gtts import gTTS
from gtts.lang import tts_langs

from ..config import TTS_DIR

SUPPORTED = {"en", "hi", "mr"}


def available_langs() -> list:
    try:
        ok = set(tts_langs().keys())
    except Exception:
        ok = set()
    return sorted(SUPPORTED & ok) or sorted(SUPPORTED)


def speak(text: str, lang: str = "en") -> str:
    """Generate (or reuse) an mp3 and return its filename."""
    lang = lang if lang in SUPPORTED else "en"
    key = hashlib.md5(f"{lang}:{text}".encode("utf-8")).hexdigest()[:20]
    fname = f"tts_{lang}_{key}.mp3"
    path = TTS_DIR / fname
    if not path.exists():
        gTTS(text=text, lang=lang, slow=False).save(str(path))
    return fname
