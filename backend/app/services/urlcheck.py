"""URL reputation: heuristics first (offline), then Google Safe Browsing /
VirusTotal if keys are configured."""
import re
from urllib.parse import urlparse

import httpx

from .. import config

URL_RE = re.compile(
    r"https?://[^\s<>\"')\]]+|(?:www\.)?[a-z0-9][a-z0-9-]*\.(?:com|in|net|org|co|xyz|top|info|biz|"
    r"online|site|live|me|tv|click|store|app|dev|cc|ru|tk|ml|ga|gq)(?:/[^\s<>\"')\]]*)?",
    re.I,
)

SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy", "shorturl.at"}
SUSPICIOUS_TLDS = {"xyz", "top", "info", "biz", "online", "site", "click", "store", "tk", "ml", "ga", "gq", "cc", "ru"}
BRANDS = ["sbi", "hdfc", "icici", "axis", "kotak", "paytm", "phonepe", "gpay", "googlepay", "whatsapp",
          "amazon", "irctc", "rbi", "aadhaar", "uidai", "netflix", "meta", "instagram"]
OFFICIAL = {
    "sbi.co.in", "onlinesbi.com", "sbi.com", "hdfcbank.com", "icicibank.com", "axisbank.com",
    "kotak.com", "paytm.com", "phonepe.com", "google.com", "gpay.com", "whatsapp.com",
    "irctc.co.in", "uidai.gov.in", "rbi.org.in", "gov.in", "cybercrime.gov.in", "amazon.in",
    "netflix.com", "meta.com", "instagram.com",
}


def extract_urls(text: str) -> list:
    seen, out = set(), []
    for m in URL_RE.findall(text or ""):
        u = m.rstrip(".,;:!?")
        if u.lower() not in seen:
            seen.add(u.lower())
            out.append(u)
    return out[:10]


def _host(url: str) -> str:
    raw = url if "://" in url else "http://" + url
    try:
        host = urlparse(raw).netloc.lower()
    except Exception:
        return ""
    return host.split("@")[-1].split(":")[0]


def _heuristic_check(url: str) -> dict:
    host = _host(url)
    reasons = []
    verdict = "clean"

    if not host:
        return {"url": url, "verdict": "suspicious", "reasons": ["Could not parse the link"]}

    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        verdict = "dangerous"
        reasons.append("Link points to a raw IP address instead of a real website")
    if "xn--" in host:
        verdict = "dangerous"
        reasons.append("Uses look-alike (punycode) domain characters")

    label = host.split(".")[0]
    tld = host.rsplit(".", 1)[-1]
    if tld in SUSPICIOUS_TLDS:
        verdict = "dangerous" if verdict != "dangerous" else verdict
        reasons.append(f"Free/low-trust domain ending .{tld}")
    if host in SHORTENERS or host.split(".")[-2] + "." + tld in SHORTENERS:
        reasons.append("Shortened link hides the real destination")
        verdict = verdict if verdict == "dangerous" else "suspicious"
    if label.count("-") >= 2:
        reasons.append("Domain name is stuffed with hyphens (classic fake-site trick)")
        verdict = verdict if verdict == "dangerous" else "suspicious"

    for brand in BRANDS:
        if brand in host:
            root = ".".join(host.split(".")[-2:])
            if root not in OFFICIAL and not any(root.endswith(o) for o in OFFICIAL):
                reasons.append(f"Uses the name '{brand.upper()}' but is not the official {brand.upper()} website")
                verdict = "dangerous"
            break

    if len(host) > 40:
        reasons.append("Very long domain, often used to hide the real site")
        verdict = verdict if verdict == "dangerous" else "suspicious"

    return {"url": url, "verdict": verdict, "reasons": reasons or ["No obvious red flags in the address"]}


async def _safe_browsing(urls: list) -> dict:
    if not config.SAFE_BROWSING_KEY or not urls:
        return {}
    payload = {
        "client": {"clientId": "safesaathi", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": u if "://" in u else "http://" + u} for u in urls],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={config.SAFE_BROWSING_KEY}",
                json=payload,
            )
            r.raise_for_status()
            matches = r.json().get("matches", [])
        out = {}
        for m in matches:
            out[m.get("threat", {}).get("url", "").lower()] = m.get("threatType", "THREAT")
        return out
    except Exception:
        return {}


async def _virustotal(url: str) -> str | None:
    if not config.VIRUSTOTAL_KEY:
        return None
    import hashlib

    full = url if "://" in url else "http://" + url
    rid = hashlib.sha256(full.encode()).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/urls/{rid}",
                headers={"x-apikey": config.VIRUSTOTAL_KEY},
            )
            if r.status_code != 200:
                return None
            stats = r.json()["data"]["attributes"]["last_analysis_stats"]
            if stats.get("malicious", 0) + stats.get("suspicious", 0) > 0:
                return f"Flagged by {stats.get('malicious', 0)} security vendors on VirusTotal"
    except Exception:
        return None
    return "Clean according to VirusTotal"


async def check_urls(text: str) -> list:
    urls = extract_urls(text)
    if not urls:
        return []
    sb = await _safe_browsing(urls)
    results = []
    for u in urls:
        r = _heuristic_check(u)
        key = (u if "://" in u else "http://" + u).lower().rstrip("/")
        for mk, mv in sb.items():
            if mk.rstrip("/") == key:
                r["verdict"] = "dangerous"
                r["reasons"].append(f"Google Safe Browsing: {mv}")
        vt = await _virustotal(u)
        if vt:
            r["reasons"].append(vt)
            if "Flagged" in vt:
                r["verdict"] = "dangerous"
        results.append(r)
    return results
