"""SafeSaathi API - FastAPI backend.

Run:  uvicorn app.main:app --port 8010   (avoid 8000: it is vLLM's default port
      and OpenCode's local discovery probes it every 30 seconds)
All endpoints are prefixed with /api so the Next.js dev proxy can forward them.
"""
import datetime as dt
import re
import threading

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .schemas import AnalyzeTextRequest, GuardianRequest, TTSRequest
from .services import alerts, heuristics, llm, ocr, rag, stt, tts, urlcheck

app = FastAPI(title="SafeSaathi API", version="1.0.0",
              description="AI scam guardian: text, screenshot and voice analysis.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS or ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- in-memory event log (powers the impact dashboard; resets on restart) ----
_events: list[dict] = []
_lock = threading.Lock()
MAX_EVENTS = 500


def _record(kind: str, analysis: dict) -> None:
    with _lock:
        _events.append({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "kind": kind,
            "label": analysis["risk_label"],
            "category": analysis["category"],
            "score": analysis["risk_score"],
            "amount": analysis.get("amount_detected", 0),
        })
        if len(_events) > MAX_EVENTS:
            _events[: len(_events) - MAX_EVENTS] = []


# --------------------------------------------------------------------------- #
#  Core analysis pipeline
# --------------------------------------------------------------------------- #
async def run_analysis(text: str, lang: str, kind: str) -> dict:
    """text -> playbooks -> URL checks -> LLM (or heuristics) -> unified JSON."""
    playbooks = rag.retrieve(text)
    urls = await urlcheck.check_urls(text)

    analysis = await llm.analyze_with_llm(text, playbooks, lang)
    engine = "llm"
    if analysis is None:
        analysis = heuristics.classify(text, url_count=len(urls))
        engine = "heuristic"

    # Enrich with URL verdicts: a dangerous link can only raise the risk.
    danger = [u for u in urls if u["verdict"] == "dangerous"]
    suspect = [u for u in urls if u["verdict"] == "suspicious"]
    if danger or suspect:
        bump = 18 if danger else 8
        analysis["risk_score"] = min(99, analysis["risk_score"] + bump)
        old = analysis["risk_label"]
        analysis["risk_label"] = (
            "scam" if analysis["risk_score"] >= 70
            else "suspicious" if analysis["risk_score"] >= 40 else "safe"
        )
        if analysis["risk_label"] != old:
            analysis["indicators"].append("Link reputation check changed the verdict")
            analysis["next_steps"] = heuristics.next_steps(analysis["risk_label"], analysis["category"])
            analysis["guardian_alert"] = analysis["risk_label"] == "scam"

    # Category fallback from the RAG store when the engine returns nothing useful.
    if analysis["category"] in ("None", "General", "Unknown", "") and playbooks:
        analysis["category"] = playbooks[0]["category"]

    # Always detect amounts ourselves so the dashboard "money saved" works.
    analysis.setdefault("amount_detected", 0)
    analysis["amount_detected"] = max(analysis["amount_detected"], heuristics._amount(text))

    result = {
        "input": {"kind": kind, "lang": lang, "original": text.strip()[:4000]},
        "analysis": analysis,
        "playbooks": [
            {"title": p["title"], "category": p["category"], "matched": p["matched"][:4],
             "why": p["explanation"].get(lang) or p["explanation"]["en"],
             "do": p["do"], "dont": p["dont"]}
            for p in playbooks
        ],
        "urls": urls,
        "engine": engine,
        "meta": {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "hotline": "1930",
            "report_url": "https://cybercrime.gov.in",
        },
    }
    _record(kind, analysis)
    return result


# --------------------------------------------------------------------------- #
#  Routes
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health_root():
    """Alias used by health checkers."""
    return await health()


@app.get("/api/health")
async def health():
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        ocr_engine = "tesseract"
    except Exception:
        ocr_engine = "llm-vision" if (config.ANTHROPIC_API_KEY or config.OPENAI_API_KEY) else "unavailable"
    return {
        "status": "ok",
        "llm": config.llm_info(),
        "ocr": ocr_engine,
        "tts_langs": tts.available_langs(),
        "playbooks": len(rag.all_playbooks()),
        "events": len(_events),
    }


@app.post("/api/analyze")
async def analyze_text(req: AnalyzeTextRequest):
    return await run_analysis(req.text, req.lang, "text")


@app.post("/api/analyze/screenshot")
async def analyze_screenshot(file: UploadFile = File(...), lang: str = "en"):
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Image too large (max 8 MB).")
    text, engine = await ocr.extract_text(data, file.content_type or "image/png")
    if not text:
        raise HTTPException(
            422,
            "Could not read text from this screenshot. Add a FREE key to "
            "backend\\.env (OPENAI_API_KEY - see the Groq note inside the file), "
            "or install Tesseract OCR - or paste the message as text.",
        )
    result = await run_analysis(text, lang, "screenshot")
    result["input"]["ocr_engine"] = engine
    return result


@app.post("/api/analyze/voice")
async def analyze_voice(file: UploadFile = File(...), lang: str = "en"):
    data = await file.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Audio too large (max 15 MB).")
    transcript, engine = await stt.transcribe(data, file.filename or "snippet.webm",
                                              file.content_type or "audio/webm")
    if not transcript:
        raise HTTPException(
            422,
            "Speech-to-text needs OPENAI_API_KEY (Whisper API) or a local "
            "'pip install faster-whisper'. Meanwhile, type what was said or use a sample.",
        )
    result = await run_analysis(transcript, lang, "voice")
    result["input"]["transcript"] = transcript
    result["input"]["stt_engine"] = engine
    return result


@app.post("/api/tts")
async def text_to_speech(req: TTSRequest):
    try:
        fname = await run_in_threadpool(tts.speak, req.text, req.lang)
    except Exception as exc:
        raise HTTPException(503, f"TTS unavailable (needs internet for gTTS): {exc}")
    return {"audio_url": f"/api/tts/audio/{fname}", "lang": req.lang}


app.mount("/api/tts/audio", StaticFiles(directory=str(config.TTS_DIR)), name="tts_audio")


@app.post("/api/guardian")
async def guardian_alert(req: GuardianRequest):
    return await alerts.send_guardian(req.message, req.to)


@app.get("/api/dashboard")
async def dashboard():
    with _lock:
        events = list(_events)
    by_label = {"scam": 0, "suspicious": 0, "safe": 0}
    by_category: dict[str, int] = {}
    money_saved = 0
    for e in events:
        by_label[e["label"]] = by_label.get(e["label"], 0) + 1
        if e["label"] in ("scam", "suspicious"):
            by_category[e["category"]] = by_category.get(e["category"], 0) + 1
            money_saved += e.get("amount", 0) if e["label"] == "scam" else 0
    return {
        "total": len(events),
        "by_label": by_label,
        "by_category": dict(sorted(by_category.items(), key=lambda kv: -kv[1])),
        "money_saved": money_saved,
        "recent": list(reversed(events[-12:])),
    }


@app.get("/api/samples")
async def samples():
    """Ready-made demo inputs so the stage demo never depends on typing."""
    return {
        "digital_arrest": {
            "label": "📞 Digital arrest call transcript",
            "text": ("This is Inspector Raj Kumar from CBI. Your identity is involved in a money "
                     "laundering case. You are under digital arrest - do not disconnect this video "
                     "call for 48 hours. To clear your name you must transfer Rs. 50,000 immediately "
                     "as verification. If you tell anyone, your account will be frozen and you will "
                     "be jailed. Stay on the call NOW."),
            "lang": "en",
        },
        "fake_kyc": {
            "label": "🏦 Fake bank KYC SMS",
            "text": ("Dear Customer, your SBI KYC has expired. Your account will be BLOCKED today. "
                     "Update KYC immediately: http://sbi-kyc-verify.xyz/update Your OTP is required "
                     "to confirm. - Bank Update Team"),
            "lang": "en",
        },
        "upi_collect": {
            "label": "📲 UPI collect request message",
            "text": ("Your refund of Rs. 2,499 is ready. Approve the payment request of Re 1 sent to "
                     "your UPI to receive the refund, and share the OTP you just received within "
                     "10 minutes or the offer expires."),
            "lang": "en",
        },
        "safe_message": {
            "label": "✅ Normal message (should be SAFE)",
            "text": "Hi, running 10 minutes late to dinner. Shall I pick up the cake on the way?",
            "lang": "en",
        },
    }
