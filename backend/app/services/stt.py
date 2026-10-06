"""Speech-to-text for call snippets / voice notes.

Order of preference:
  1. OpenAI-compatible Whisper endpoint (api.openai.com or any other
     OPENAI_BASE_URL such as Groq's free whisper-large-v3)
  2. Local faster-whisper (pip install faster-whisper, ~460MB model)
  3. None -> the API returns a friendly error and the UI offers typed input
"""
import httpx

from .. import config


async def transcribe(audio_bytes: bytes, filename: str, content_type: str) -> tuple[str | None, str]:
    """Returns (transcript, engine) or (None, reason)."""
    if config.OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(
                    f"{config.OPENAI_BASE_URL}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
                    data={"model": config.STT_MODEL},
                    files={"file": (filename or "snippet.ogg", audio_bytes, content_type or "audio/webm")},
                )
                r.raise_for_status()
                txt = (r.json().get("text") or "").strip()
                if txt:
                    return txt, "openai-whisper"
        except Exception:
            pass  # fall through to local whisper

    try:
        from faster_whisper import WhisperModel  # type: ignore
        import asyncio

        def _run() -> str:
            model = WhisperModel("small", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_bytes, language=None)
            return " ".join(s.text for s in segments).strip()

        txt = await asyncio.to_thread(_run)
        if txt:
            return txt, "local-whisper"
    except Exception:
        pass

    return None, "no-engine"
