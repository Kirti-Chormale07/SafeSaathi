# SafeSaathi — AI Scam Guardian 🛡️

> *"We don't just detect scams, we protect the people technology forgot."*

SafeSaathi is a mobile-first PWA where anyone — senior citizens, first-time smartphone
users, non-English speakers — can **paste a message, upload a screenshot, or record a call**
and instantly get:

- ✅ A **risk score** (Safe / Suspicious / Scam) with plain-language reasons
- 🔗 **Link reputation** checks (fake-domain detection + optional Safe Browsing/VirusTotal)
- 📚 A matched **scam playbook** (RAG over known Indian scam patterns)
- 🔊 **Voice warning** in Hindi, Marathi or English (gTTS)
- 📲 **One-tap family guardian alert** (WhatsApp pre-filled message / Twilio)
- ☎️ One-tap **1930** helpline + cybercrime.gov.in reporting
- 📊 An **impact dashboard** (scams caught + "money saved" estimate)

Built for the hackathon problem statement **Digital Safety & Cybersecurity**
(with the secondary **Inclusive Technology** angle).

---

## Project structure

```
SafeSaathi/
├── backend/                      # FastAPI + AI layer
│   ├── app/
│   │   ├── main.py               # API routes + analysis pipeline
│   │   ├── config.py             # all keys are OPTIONAL (.env)
│   │   ├── schemas.py            # request models
│   │   ├── data/
│   │   │   └── scam_patterns.json# RAG store: 9 scam playbooks
│   │   └── services/
│   │       ├── heuristics.py     # rule-based engine (works offline!)
│   │       ├── llm.py            # Claude/OpenAI reasoning + vision OCR
│   │       ├── rag.py            # playbook retrieval
│   │       ├── ocr.py            # Tesseract -> vision LLM fallback
│   │       ├── stt.py            # Whisper API -> local faster-whisper
│   │       ├── tts.py            # gTTS (en/hi/mr) with caching
│   │       ├── urlcheck.py       # link reputation heuristics + APIs
│   │       └── alerts.py         # Twilio / wa.me guardian alerts
│   ├── data/eval_samples.json    # 41 labeled samples (13 safe / 10 susp / 18 scam)
│   ├── scripts/eval.py           # accuracy report for the judges
│   ├── static/audio/             # generated TTS mp3s (auto-created)
│   ├── requirements.txt
│   ├── .env.example
│   └── venv/                     # created in Step 1
└── frontend/                     # Next.js 14 PWA (JavaScript)
    ├── app/
    │   ├── layout.jsx            # metadata, PWA manifest, service worker
    │   ├── page.jsx              # 3-mode analyzer (text / image / voice)
    │   ├── dashboard/page.jsx    # live impact dashboard
    │   └── globals.css           # mobile-first, big-button styling
    ├── components/
    │   ├── Header.jsx            # logo + language switcher + bottom nav
    │   ├── RiskCard.jsx          # score hero, red flags, actions
    │   ├── VoiceRecorder.jsx     # MediaRecorder (60 s max)
    │   └── SWRegister.jsx        # PWA service worker registration
    ├── lib/
    │   ├── api.js                # API client (via /api proxy)
    │   └── i18n.js               # UI strings: हिंदी / मराठी / English
    ├── public/                   # manifest, sw.js, icons
    ├── next.config.mjs           # /api/* → http://127.0.0.1:8010 proxy
    └── package.json
```

---

## Step-by-step execution

### Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.10+ | `py -3 --version` |
| Node.js | 18+ | `node --version` |
| Internet | for gTTS voice + optional API keys | — |

> **No API key? No problem.** Every feature has an offline fallback: detection runs on the
> built-in rules engine (100% on our 41-sample test set), guardian alerts use WhatsApp's
> free pre-filled link, and screenshots can be typed in instead.

### ▶️ Step 1 — Backend (FastAPI, port 8010)

> Port **8010** is deliberate: port 8000 is vLLM's default, and OpenCode's
> built-in local discovery probes it every 30 s (harmless 404 noise in the logs).

Open **Terminal 1** (PowerShell):

```powershell
cd C:\Users\Kirti\SafeSaathi\backend

# create a virtual environment (first time only)
py -3 -m venv venv

# install dependencies (first time only)
venv\Scripts\python.exe -m pip install -r requirements.txt

# (optional) configure API keys
copy .env.example .env
notepad .env

# run the API
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Verify: <http://127.0.0.1:8010/health> → `{"status":"ok", ...}`

### ▶️ Step 2 — Frontend (Next.js, port 3000)

Open **Terminal 2**:

```powershell
cd C:\Users\Kirti\SafeSaathi\frontend
npm install          # first time only
npm run dev
```

Open **<http://localhost:3000>** 🎉 — that's the whole app.

*(macOS/Linux: use `./venv/bin/python -m uvicorn ...` and `python3 -m venv venv`.)*

### ▶️ Step 3 — Prove it works (30 seconds)

1. On the home page, tap a **sample chip** (e.g. *"📞 Digital arrest call transcript"*).
2. The result shows **SCAM 96-99/100** with red flags, playbook and next steps.
3. Tap **🔊 Listen to warning** — hear it speak in हिंदी/मराठी/English (switch language
   in the header first).
4. Tap **📲 Alert family** — WhatsApp opens with the warning pre-filled (one tap to send).
5. Open the **📊 Dashboard** tab — scams caught, scam types, money saved.

### ▶️ Step 4 — Show real accuracy numbers (judges love this)

```powershell
cd C:\Users\Kirti\SafeSaathi\backend
venv\Scripts\python.exe scripts\eval.py          # rules engine
venv\Scripts\python.exe scripts\eval.py --llm    # with an API key set
```

Current output:

```
Engine : Heuristic (rules)
Samples: 41
Accuracy: 41/41 = 100.0%

Per-class metrics:
class       precision  recall    f1  support
safe             1.00    1.00  1.00       13
suspicious       1.00    1.00  1.00       10
scam             1.00    1.00  1.00       18
```

---

## Enabling the optional "AI" features

Edit `backend/.env` (all optional, restart backend after):

### 🆓 Free AI key (recommended) — Groq Developer plan

One **free** key unlocks LLM analysis, screenshot OCR **and** voice transcription —
no credit card, rate-limited free tier:

1. Sign up at **https://console.groq.com** (Google/GitHub login works)
2. Open **API Keys** → **Create API Key** → copy the `gsk_...` key
3. Paste it in `backend/.env` (the Groq URL + free model IDs are already filled in):
   ```
   OPENAI_API_KEY=gsk_your_key_here
   ```
4. Restart the backend

Free models used (from Groq's [rate-limits](https://console.groq.com/docs/rate-limits) page):
`openai/gpt-oss-120b` (chat), `qwen/qwen3.8-27b` (vision OCR), `whisper-large-v3` (STT).

### All optional keys

| Key | Enables | Free alternative already built in |
|---|---|---|
| `OPENAI_API_KEY` + `OPENAI_BASE_URL` | Any OpenAI-compatible provider (Groq free tier, OpenRouter, Ollama...) → LLM explanations, **vision OCR**, **Whisper STT** | Rules engine / type the text |
| `ANTHROPIC_API_KEY` | Claude LLM explanations + vision OCR | Rules engine / type the text |
| *(none — just install)* | Local OCR: install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) + `pip install pytesseract` | Vision LLM |
| *(none — just install)* | Local STT: `pip install faster-whisper` (~460 MB model) | Whisper API / typing |
| `GOOGLE_SAFE_BROWSING_KEY` / `VIRUSTOTAL_API_KEY` | Link reputation APIs | Built-in fake-domain heuristics |
| `TWILIO_*` | Fully automated guardian SMS/WhatsApp | Free `wa.me` pre-filled link (works!) |

> Status check: `GET http://127.0.0.1:8010/health` tells you which engine is active
> (`heuristic` vs `anthropic`/`openai`), OCR availability and TTS languages.

---

## API reference

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` · `/api/health` | Engine status |
| POST | `/api/analyze` | `{text, lang}` → full analysis JSON |
| POST | `/api/analyze/screenshot` | multipart `file` + `?lang=` (OCR → analysis) |
| POST | `/api/analyze/voice` | multipart `file` + `?lang=` (STT → analysis) |
| POST | `/api/tts` | `{text, lang}` → `{audio_url}` (mp3) |
| GET | `/api/tts/audio/{file}` | Cached audio |
| POST | `/api/guardian` | `{message, to}` → Twilio send or `wa.me` link |
| GET | `/api/dashboard` | session stats (labels, categories, money saved) |
| GET | `/api/samples` | built-in demo inputs |

Analysis response shape (identical for both engines):

```jsonc
{
  "input":    { "kind": "text", "lang": "en", "original": "..." },
  "analysis": {
    "risk_score": 99, "risk_label": "scam", "category": "OTP / Password Theft",
    "explanation": "...", "indicators": ["..."], "next_steps": ["..."],
    "guardian_alert": true,
    "spoken_warning": { "en": "...", "hi": "...", "mr": "..." },
    "amount_detected": 50000
  },
  "playbooks": [ { "title": "...", "why": "...", "do": [...], "dont": [...] } ],
  "urls":      [ { "url": "...", "verdict": "dangerous", "reasons": ["..."] } ],
  "engine": "heuristic"   // or "llm"
}
```

---

## 3-minute demo script (from the pitch doc)

1. **Hook (15 s):** *"Every 7 minutes, someone in India loses money to a scam call.
   Let me show you one."*
2. **Voice mode (45 s):** play/receive a simulated digital-arrest call → SafeSaathi
   flags it live: **SCAM 96%** → 🔊 speaks the warning in Hindi → **📲 guardian alert**
   pops on a teammate's phone on stage.
3. **Screenshot (30 s):** upload a fake bank-KYC screenshot → caught, with the
   *fake-domain* clue highlighted (`sbi-kyc-verify.xyz` → dangerous).
4. **Dashboard (30 s):** scam types detected + "money saved" estimate.
5. **Close (20 s):** *"We don't just detect scams, we protect the people technology
   forgot."*

**Demo tips:** keep the rules engine active for the live run (zero network dependency),
use the 🎬 sample chips if Wi-Fi fails, and mention privacy — *"nothing leaves the
device unless you press send; the session log clears on restart."*

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `500` on localhost:3000 | Check Terminal 2 for compile errors; ensure backend is running |
| `ECONNREFUSED` from frontend | Backend not started (Step 1) — Next.js only proxies `/api/*` |
| Voice tab says STT needed | Add `OPENAI_API_KEY`, install `faster-whisper`, or type the message |
| Screenshot says OCR needed | Install Tesseract binary, add a vision LLM key, or paste the text |
| 🔊 button silent | gTTS needs internet; error text appears under the buttons |
| Port already in use | `netstat -ano | findstr :8010` then `taskkill /PID <pid> /F` |
| `/v1/models 404` lines in logs | Only appears on port 8000 (OpenCode's vLLM discovery). This project uses **8010** so it never happens. |
| Want a clean slate | Restart the backend — dashboard log & TTS cache reset (privacy) |

## Privacy & safety notes (say this on stage 🔊)

- No user data is stored server-side — the analysis log is **in-memory and clears on restart**.
- Voice/screenshot processing never touches storage; TTS files contain only the warning text.
- Guardian alerts are **opt-in, one tap** — the user always sees the message before sending.
"# SafeSaathi" 
"# SafeSaathi" 
