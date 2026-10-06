"""Guardian alerts.

Two paths:
  1. Twilio (WhatsApp/SMS) if credentials are configured - fully automated.
  2. Zero-setup fallback: build a wa.me link with the warning pre-filled so
     the user sends it with ONE TAP. Works everywhere, needs no keys.
"""
from .. import config

HOTLINES = {"india_cybercrime": "1930", "women_helpline": "1091", "emergency": "112"}


def build_message(risk_label: str, category: str, snippet: str, explanation: str) -> str:
    head = {
        "scam": "ALERT from SafeSaathi: a scam message was detected!",
        "suspicious": "SafeSaathi check: this message looks suspicious.",
    }.get(risk_label, "SafeSaathi check update.")
    clean = " ".join((snippet or "").split())[:180]
    return (f"{head}\nType: {category}\nWhy: {explanation}\n"
            f"Message: \"{clean}\"\nPlease call and check on them. "
            f"Report cyber fraud on 1930 / cybercrime.gov.in.")


def guardian_link(message: str) -> str:
    """WhatsApp share link - the free, always-working alert path."""
    return "https://wa.me/?text=" + __import__("urllib.parse", fromlist=["quote"]).quote(message)


async def send_guardian(message: str, to: str | None = None) -> dict:
    """Try Twilio; otherwise return the wa.me one-tap link."""
    to = (to or config.GUARDIAN_DEFAULT or "").strip()
    if config.TWILIO_SID and config.TWILIO_TOKEN and config.TWILIO_FROM and to:
        try:
            import httpx

            auth = (config.TWILIO_SID, config.TWILIO_TOKEN)
            url = f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_SID}/Messages.json"
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    url, auth=auth,
                    data={
                        "To": to,
                        "From": config.TWILIO_FROM,
                        "Body": message[:1500],
                    },
                )
            if r.status_code < 300:
                return {"status": "sent", "channel": "twilio", "to": to, "preview": message[:120]}
        except Exception:
            pass  # fall through to wa.me

    return {
        "status": "ready",
        "channel": "whatsapp-link",
        "to": to,
        "link": guardian_link(message),
        "preview": message[:120],
        "note": "One-tap: opens WhatsApp with the warning pre-filled (no API key needed).",
    }
