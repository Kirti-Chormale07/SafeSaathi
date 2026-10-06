"""LLM engine: scam reasoning with Claude (or OpenAI), plus vision OCR.

All calls go through plain httpx - no SDK dependency, no version surprises.
If no key is configured (or a call fails), every function returns None and
the caller falls back to the heuristic engine, so the demo never breaks.
"""
import json
import re

import httpx

from .. import config

SYSTEM_PROMPT = (
    "You are SafeSaathi, a friendly scam guardian for India. You protect senior "
    "citizens and first-time smartphone users from digital-arrest, fake-KYC, UPI, "
    "job, lottery and utility scams. Analyze the message the user gives you. "
    "Be strict: pressure tactics, money demands or credential asks mean it is a scam. "
    "Reply with ONLY a JSON object, no markdown fences, with exactly these keys: "
    "risk_score (integer 0-100), risk_label ('safe'|'suspicious'|'scam'), "
    "category (short scam-type name or 'None'), explanation (one clear sentence "
    "a grandparent understands), indicators (array of short strings, the specific "
    "clues in THIS message), next_steps (array of 3-4 concrete actions), "
    "guardian_alert (boolean, true only for scams), spoken_warning "
    "(object with 'en', 'hi', 'mr' - one short spoken sentence each warning the user)."
)


def _playbook_block(playbooks: list) -> str:
    if not playbooks:
        return ""
    lines = ["Known scam playbooks that may match (use them to explain better):"]
    for p in playbooks:
        lines.append(f"- {p['category']}: {p['explanation']['en']}")
    return "\n" + "\n".join(lines)


def _parse_json(raw: str) -> dict:
    """Pull the first JSON object out of an LLM reply, tolerating fences/prose."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in LLM reply")
    return json.loads(text[start:end + 1])


def _normalize(data: dict) -> dict:
    """Validate/repair whatever the model returned."""
    label = str(data.get("risk_label", "suspicious")).lower().strip()
    if label not in ("safe", "suspicious", "scam"):
        label = "scam" if label in ("danger", "dangerous", "fraud") else "suspicious"
    try:
        score = int(round(float(data.get("risk_score", 50))))
    except (TypeError, ValueError):
        score = {"safe": 10, "suspicious": 55, "scam": 90}[label]
    score = max(0, min(100, score))
    label = "scam" if score >= 70 else ("suspicious" if score >= 40 else "safe")

    spoken = data.get("spoken_warning") or {}
    if not isinstance(spoken, dict):
        spoken = {}
    fallback = {
        "en": "Warning! This looks like a scam. Do not pay or share any OTP. Report on 1930.",
        "hi": "सावधान! यह संदेश धोखाधड़ी वाला लगता है। कोई पैसा या OTP साझा न करें। 1930 पर रिपोर्ट करें।",
        "mr": "सावधान! हा संदेश बनावट आहे. पैसे किंवा OTP देऊ नका. 1930 वर तक्रार नोंदवा.",
    } if label == "scam" else {
        "en": "This message looks suspicious. Do not click any link. Verify with family first.",
        "hi": "यह संदेश संदिग्ध लगता है। किसी लिंक पर क्लिक न करें। पहले परिवार से पूछें।",
        "mr": "हा संदेश संशयास्पद आहे. कोणत्याही लिंकवर क्लिक करू नका. आधी कुटुंबाशी विचारा.",
    } if label == "suspicious" else {
        "en": "This message looks safe. Still, never share your OTP or password.",
        "hi": "यह संदेश सुरक्षित लगता है। फिर भी अपना OTP या पासवर्ड किसी से साझा न करें।",
        "mr": "हा संदेश सुरक्षित आहे. तरीही OTP किंवा पासवर्ड कोणाशीही देऊ नका.",
    }
    for k in ("en", "hi", "mr"):
        if not str(spoken.get(k) or "").strip():
            spoken[k] = fallback[k]

    def _str_list(v, n=6):
        if isinstance(v, list):
            out = [str(x).strip() for x in v if str(x).strip()]
            return out[:n]
        return []

    return {
        "risk_score": score,
        "risk_label": label,
        "category": str(data.get("category") or "Unknown").strip()[:60],
        "explanation": str(data.get("explanation") or "").strip()[:500]
        or "The message shows signs of a scam pattern.",
        "indicators": _str_list(data.get("indicators"), 8) or ["Pattern matched by SafeSaathi"],
        "next_steps": _str_list(data.get("next_steps"), 5)
        or ["Do not pay or share OTP", "Report on 1930"],
        "guardian_alert": bool(data.get("guardian_alert", label == "scam")) and label == "scam",
        "spoken_warning": spoken,
    }


async def _anthropic(prompt: str) -> str:
    model = config.LLM_MODEL or "claude-3-5-sonnet-latest"
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []))


async def _post_chat(payload: dict, timeout: int = 45) -> str:
    """POST to {OPENAI_BASE_URL}/chat/completions.

    Works with OpenAI, Groq, OpenRouter, Ollama, LM Studio, ... If the endpoint
    rejects a parameter (HTTP 400), drop/replace it and retry so the demo never
    breaks on a provider that does not support that field.
    """
    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {config.OPENAI_API_KEY}"}
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code == 400:
            if "response_format" in r.text and "response_format" in payload:
                payload.pop("response_format")
                r = await client.post(url, headers=headers, json=payload)
            if r.status_code == 400 and "max_completion_tokens" in r.text and "max_completion_tokens" in payload:
                payload["max_tokens"] = payload.pop("max_completion_tokens")
                r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return (r.json()["choices"][0]["message"].get("content") or "").strip()


async def _openai(prompt: str) -> str:
    """Chat completion through any OpenAI-compatible endpoint (OpenAI/Groq/...)."""
    model = config.LLM_MODEL or "gpt-4o-mini"
    return await _post_chat({
        "model": model,
        "max_completion_tokens": 1024,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    })


async def analyze_with_llm(text: str, playbooks: list, lang: str) -> dict | None:
    """Returns normalized analysis dict, or None if no LLM is available/it failed."""
    if not (config.ANTHROPIC_API_KEY or config.OPENAI_API_KEY):
        return None
    prompt = (
        f"User language preference: {lang} (keep explanation simple; spoken_warning "
        f"must still be written in en, hi and mr).\n\n"
        f"Message to analyze:\n---\n{text[:6000]}\n---{_playbook_block(playbooks)}"
    )
    try:
        if config.ANTHROPIC_API_KEY:
            raw = await _anthropic(prompt)
        else:
            raw = await _openai(prompt)
        return _normalize(_parse_json(raw))
    except Exception:
        # Network down, quota, bad reply - fall back to heuristics silently.
        return None


async def vision_ocr(file_bytes: bytes, content_type: str) -> str | None:
    """Read screenshot text with a vision model if one is configured."""
    if not (config.ANTHROPIC_API_KEY or config.OPENAI_API_KEY):
        return None
    b64 = __import__("base64").b64encode(file_bytes).decode()
    media = content_type or "image/png"
    try:
        if config.ANTHROPIC_API_KEY:
            model = config.LLM_MODEL or "claude-3-5-sonnet-latest"
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": config.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": model,
                        "max_tokens": 1500,
                        "system": "You transcribe screenshot text exactly as written, "
                                  "preserving phone numbers, links and amounts. Output only the text.",
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}},
                                {"type": "text", "text": "Transcribe all text in this screenshot."},
                            ],
                        }],
                    },
                )
                r.raise_for_status()
                return "".join(b.get("text", "") for b in r.json().get("content", [])).strip() or None
        model = config.VISION_MODEL or config.LLM_MODEL or "gpt-4o-mini"
        return await _post_chat(
            {
                "model": model,
                "max_completion_tokens": 1500,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Transcribe all text in this screenshot, exactly as written."},
                        {"type": "image_url", "image_url": {"url": f"data:{media};base64,{b64}"}},
                    ],
                }],
            },
            timeout=60,
        ) or None
    except Exception:
        return None
