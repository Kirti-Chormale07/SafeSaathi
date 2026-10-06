"""Rule-based scam detector.

This is SafeSaathi's always-available fallback engine. It needs no API key,
no internet and no model download - so the demo never dies on stage.

Scoring model (tuned against data/eval_samples.json, see scripts/eval.py):
  * category rules      - each known scam playbook has a weight
  * pressure modifiers  - money / threats / urgency / credential ask / fee / link
  * combo bonus         - a playbook + any pressure tactic = coordinated attack
  * protective cap      - genuine safety advice ("do not share OTP") stays SAFE

Labels: score >= 70 -> scam, >= 30 -> suspicious, else safe.
"""
import re

# Money: Rs. 500 / ₹500 / INR 500 / Re 1
MONEY_RE = re.compile(r"(?:₹|rs\.?|inr|re\.?)\s*([\d][\d,]*)(?:\.\d+)?", re.I)
OTP_RE = re.compile(r"\b(otp|one[\s-]?time\s+password|cvv|atm\s+pin|upi\s+pin|login\s+password|"
                    r"net\s+banking\s+password|pin)\b")
URGENCY_RE = re.compile(
    r"(immediately|urgent(?:ly)?|within\s+\d+\s*(?:min|minute|hour|day)|last\s+warning|"
    r"\btoday\b|\btonight\b|\bright\s+now\b|\bnow\b|midnight|limited\s+time|expire[sd]?\b|"
    r"right\s+away|before\s+the\s+deadline|turant|abhi|fauran|lavar)"
)
THREAT_RE = re.compile(
    r"(arrest|block(?:ed|ing)?\s+(?:your\s+)?account|suspend(?:ed)?|freeze|legal\s+action|"
    r"case\s+(?:filed|registered)|police\s+(?:case|action)|report(?:ed)?\s+to\s+(?:the\s+)?police|"
    r"forward\s+(?:to|your)|blackmail|publish|shame|jaanch|giraftar|jailed|jail\b|"
    r"account\s+will\s+be\s+clos)"
)
FEE_RE = re.compile(r"\b(?:processing|registration|training|clearance|advance|joining|activation|"
                    r"verification|insurance|recharge)\s+(?:fee|charge)s?\b", re.I)
# Genuine safety advice - never flag it as a scam
PROTECTIVE_RE = re.compile(r"\b(?:do\s+not|don['\u2019]t|never)\s+(?:share|click|give|disclose)\b", re.I)


class Rule:
    def __init__(self, category, weight, indicator, patterns):
        self.category = category
        self.weight = weight
        self.indicator = indicator
        self.patterns = patterns


RULES = [
    Rule(
        "Digital Arrest", 48,
        "Claims to be police/CBI/NCB and threatens 'digital arrest' - police never do this",
        [r"\bdigital\s+arrest\b",
         r"\bvideo\s+(?:call|court)\b.{0,60}\b(?:court|judge|warrant)\b",
         r"\b(?:cbi|ncb|cyber\s+cell|crime\s+branch)\b.{0,60}\b(?:arrest|warrant|case|notice)\b",
         r"\b(?:arrest|warrant|giraftar).{0,60}\b(?:video|online|digital)\b",
         r"\bstay\s+on\s+(?:this\s+)?(?:video\s+)?call\b", r"\bjud(?:ge|icial)\s+(?:order|custody)\b"],
    ),
    Rule(
        "Fake KYC / Account Block", 40,
        "Fake KYC / account-suspension scare to steal your credentials",
        [r"\bkyc\b", r"\baadhaar\b.{0,50}\b(?:suspend|block|expire|deactivat|verify|update)\b",
         r"\b(?:bank|account|subscription|number)\b.{0,40}\b(?:block|freeze|suspend|deactivat|clos(?:e|ed))\b",
         r"\bupdate\s+(?:your\s+)?(?:kyc|profile|records|details)\b"],
    ),
    Rule(
        "UPI Collect / Refund Fraud", 40,
        "Fake UPI collect-request or refund trick - you must never approve a request to receive money",
        [r"\bcollect\s+request\b", r"\b(?:approve|accept)\s+(?:the\s+)?(?:request|payment)\b.{0,40}\b(?:receive|refund|credit)\b",
         r"\brefund\b.{0,60}\b(?:upi|wallet|share|send|approve|request|claim)\b",
         r"\bcashback\b.{0,60}\b(?:claim|share|verify)\b",
         r"\bpay\s*[₹]?\s*1\b.{0,40}\b(?:verify|activate|receive)\b",
         r"\bpayment\s+request\b.{0,40}\b(?:approve|accept)\b"],
    ),
    Rule(
        "OTP / Password Theft", 50,
        "Directly asks for OTP, PIN, CVV or password - the biggest red flag of all",
        [r"\bshare\s+(?:your\s+|the\s+)?(?:otp|code|password|pin|cvv)\b",
         r"\bsend\s+(?:me\s+)?(?:your\s+)?(?:otp|cvv|pin|password)\b",
         r"\botp\b.{0,50}\b(?:share|send|enter|verify|confirm)\b",
         r"\b(?:share|send|verify|confirm)\b.{0,40}\b(?:otp|cvv|atm\s+pin|upi\s+pin)\b"],
    ),
    Rule(
        "Fake Job Offer", 38,
        "Too-good job offer that asks for a 'registration/training fee'",
        [r"\bwork\s+from\s+home\b.{0,60}\b(?:₹|rs\.?|inr|fee|payment|income)\b",
         r"\b(?:job|vacancy|hiring)\b.{0,60}\b(?:registration|fee|deposit|payment)\b",
         r"\bdaily\s+income\b", r"\bper\s+day\s+(?:earning|income|payment)\b",
         r"\bpart[\s-]?time\s+job\b.{0,60}\b(?:earn|income|₹)\b",
         r"\bdata\s+entry\s+job\b.{0,60}\b(?:fee|advance)\b",
         r"\b(?:task\s+earnings?|daily\s+task|credited\s+per\s+day|salary\s+will\s+be\s+credited)\b"],
    ),
    Rule(
        "Lottery / Prize Scam", 38,
        "Fake lottery or prize win designed to extract 'processing fees'",
        [r"\byou\s+(?:have\s+)?won\b", r"\blottery\b", r"\bjackpot\b", r"\blucky\s+draw\b",
         r"\bprize\s+money\b", r"\bwinner\b.{0,40}\b(?:₹|rs\.?|lakh|crore)\b",
         r"\bclaim\s+your\s+(?:gift|bonus|reward|coupon)\b", r"\bgift\s+card\b.{0,40}\b(?:claim|free|win)\b"],
    ),
    Rule(
        "Investment / Doubling Scam", 40,
        "'Guaranteed returns' or money-doubling investment scheme",
        [r"\bdouble\s+your\s+money\b", r"\bguaranteed\s+returns?\b",
         r"\b\d{2,3}\s*%\s*(?:profit|return|gain)s?\b",
         r"\b(?:earn|profit)\s+daily\b", r"\binvestment\s+plan\b.{0,40}\b(?:guarantee|daily|fixed)\b",
         r"\bcrypto\s+(?:trading|signal)s?\s+(?:group|plan)\b"],
    ),
    Rule(
        "Money Doubling / Ransom", 45,
        "Promises to double money, or demands ransom for a family member",
        [r"\bdouble\s+your\s+(?:money|amount|funds)\b", r"\bransom\b", r"\bkidnap",
         r"\bhostage\b", r"\b(?:daughter|son|child|wife|husband)\s+is\s+with\s+us\b"],
    ),
    Rule(
        "Sextortion", 45,
        "Sextortion: recorded/edited video used for blackmail",
        [r"\b(?:your\s+)?(?:private|obscene|explicit)\s+(?:video|clip|photo|image)\b",
         r"\b(?:morphed|edited)\s+(?:video|photo|clip)\b", r"\bblackmail\b",
         r"\bforward\s+(?:to|your)\s+(?:family|friends|contacts)\b",
         r"\brecorded\s+(?:your\s+)?(?:private|obscene)\b"],
    ),
    Rule(
        "Fake Electricity / Utility Bill", 38,
        "Fake disconnection notice for electricity/water/gas bill",
        [r"\b(?:electricity|electric|power|water|gas)\s+bill\b.{0,60}\b(?:disconn|final\s+notice|overdue|unpaid)\b",
         r"\b(?:electricity|power|water|gas)\b.{0,60}\b(?:disconn|cut\s+off)\b.{0,40}\b(?:today|tonight|hours)\b",
         r"\bdisconnected?\b.{0,40}\b(?:today|tonight|within)\b",
         r"\bsmart\s+(?:meter|card)\b.{0,40}\b(?:recharge|expired|blocked)\b"],
    ),
    Rule(
        "Fake Parcel / Customs", 32,
        "Fake parcel/customs seizure story to steal money or data",
        [r"\b(?:parcel|package|courier)\b.{0,60}\b(?:seized|held|blocked|drug|narcotic|customs)\b",
         r"\bcustoms\s+(?:department|clearance|fee)\b", r"\bdelivery\s+(?:failed|held|pending|attempted)\b",
         r"\bdelivery\b.{0,25}\b(?:held|failed|pending|attempted|blocked|stuck)\b"],
    ),
    Rule(
        "Instant Loan Scam", 38,
        "Instant/pre-approved loan fraud that demands upfront fees",
        [r"\b(?:instant|pre[\s-]?approved|approved)\s+loan\b",
         r"\bloan\b.{0,50}\b(?:processing\s+fee|advance\s+fee|gst\s+refund)\b",
         r"\bwithout\s+(?:salary\s+slip|documents|collateral)\b"],
    ),
    Rule(
        "Bank / Govt Impersonation", 35,
        "Caller pretends to be from a bank, RBI, IRDA or a government dept",
        [r"\bwe\s+are\s+(?:calling|writing)\s+from\b",
         r"\b(?:rbi|irda|irctc|income\s+tax|insurance\s+regulator|customs)\b.{0,50}\b(?:notice|refund|update|verify|department)\b",
         r"\b(?:bank|loan|credit\s+card)\s+(?:officer|representative|department|help\s*desk|team)\b",
         r"\brepresentative\s+from\b"],
    ),
    Rule(
        "Personal Data Ask", 30,
        "Asks you to send bank details, ID proofs or screenshots to a stranger",
        [r"\bshare\s+(?:your\s+)?(?:bank|account|balance|ifsc|id|card|card\s+number)\b",
         r"\bshare\b.{0,25}\bscreenshot\b", r"\bsend\s+me\s+your\b.{0,30}\b(?:id|documents?|proofs?)\b",
         r"\breply\s+with\s+your\b.{0,20}\b(?:account|bank|card)\b",
         r"\bsend\b.{0,20}\b(?:id\s+proof|documents?|passbook)\b"],
    ),
]

SAFE_PATTERNS = [
    r"\b(?:how\s+are\s+you|thanks|thank\s+you|good\s+morning|see\s+you|let(?:'|’)?s\s+(?:meet|call)\b)",
]


def _amount(text: str):
    hits = MONEY_RE.findall(text)
    vals = []
    for h in hits:
        try:
            vals.append(int(h.replace(",", "")))
        except ValueError:
            pass
    return max(vals) if vals else 0


def _spoken(label: str, category: str, lang: str) -> str:
    """Short, speakable warning in the user's language (used by TTS)."""
    bank = {
        "scam": {
            "en": "Warning! This looks like a scam message. Do not pay money or share any OTP. Report it on 1930.",
            "hi": "सावधान! यह संदेश धोखाधड़ी वाला लगता है। कोई पैसा या OTP साझा न करें। 1930 पर रिपोर्ट करें।",
            "mr": "सावधान! हा संदेश बनावट आहे. पैसे किंवा OTP देऊ नका. 1930 वर तक्रार नोंदवा.",
        },
        "suspicious": {
            "en": "This message looks suspicious. Do not click any link or share details. Verify first with family.",
            "hi": "यह संदेश संदिग्ध लगता है। किसी लिंक पर क्लिक न करें और जानकारी साझा न करें। पहले परिवार से पूछें।",
            "mr": "हा संदेश संशयास्पद आहे. कोणत्याही लिंकवर क्लिक करू नका, माहिती देऊ नका. आधी कुटुंबाशी विचारा.",
        },
        "safe": {
            "en": "This message looks safe. Still, never share your OTP or password with anyone.",
            "hi": "यह संदेश सुरक्षित लगता है। फिर भी अपना OTP या पासवर्ड किसी से साझा न करें।",
            "mr": "हा संदेश सुरक्षित आहे. तरीही OTP किंवा पासवर्ड कोणाशीही शेअर करू नका.",
        },
    }
    text = bank.get(label, bank["suspicious"]).get(lang) or bank[label]["en"]
    extra = {
        "Digital Arrest": {
            "hi": " असली पुलिस कभी वीडियो कॉल पर गिरफ्तारी या पैसे की बात नहीं करती।",
            "en": " Real police never arrest you or demand money on a video call.",
            "mr": " खरी पोलिस व्हिडिओ कॉलवर अटक किंवा पैसे मागत नाही.",
        },
        "Fake KYC / Account Block": {
            "hi": " बैंक कभी लिंक से KYC अपडेट नहीं मांगता।",
            "en": " Your bank never asks for KYC updates through a link.",
            "mr": " बँक कधीही लिंकद्वारे KYC अपडेट मागत नाही.",
        },
    }
    return text + extra.get(category, {}).get(lang, "")


def next_steps(label: str, category: str) -> list:
    if label == "scam":
        steps = [
            "Do NOT pay any money and do NOT share OTP/PIN/CVV.",
            "Stop replying and block the sender right away.",
            "Report at cybercrime.gov.in or call the helpline 1930.",
            "Tell a trusted family member now (use the Alert button).",
        ]
        if category == "Digital Arrest":
            steps.insert(1, "Hang up: real police never arrest anyone over a video call.")
        return steps
    if label == "suspicious":
        return [
            "Do not click the link or download any file.",
            "Verify independently: call the official number on the back of your card.",
            "Ask a family member or a trusted person before acting.",
        ]
    return [
        "Looks okay - but never share OTP, PIN or password with anyone.",
        "If anything feels odd, ask someone you trust before replying.",
    ]


def classify(text: str, url_count: int = 0) -> dict:
    """Return an analysis dict shaped exactly like the LLM engine's output."""
    low = (text or "").lower()
    score = 0
    indicators = []
    cat_scores = {}
    rule_matched = False

    for rule in RULES:
        if any(re.search(p, low, re.I | re.S) for p in rule.patterns):
            score += rule.weight
            rule_matched = True
            indicators.append(rule.indicator)
            cat_scores[rule.category] = cat_scores.get(rule.category, 0) + rule.weight

    pressure = False
    if OTP_RE.search(low):
        score += 20
        pressure = True
        indicators.append("Asks for OTP / PIN / CVV / password")
    if MONEY_RE.search(text):
        score += 15
        pressure = True
        indicators.append("Mentions money transfer or an amount to pay")
    if FEE_RE.search(low):
        score += 10
        pressure = True
        indicators.append("Demands a fee (processing/registration/registration) before benefit")
    if THREAT_RE.search(low):
        score += 15
        pressure = True
        indicators.append("Uses threats (arrest, block, freeze, shame) to pressure you")
    if URGENCY_RE.search(low):
        score += 10
        pressure = True
        indicators.append("Creates urgency - 'act immediately or else'")
    if url_count:
        score += 10
        pressure = True
        indicators.append("Contains a link - links in unsolicited messages are risky")

    # A playbook + pressure tactics = coordinated attack, not coincidence.
    if rule_matched and pressure:
        score += 10
        indicators.append("Scam playbook + pressure tactics used together")

    score = min(99, score)

    # Genuine safety advice ("do not share your OTP") must never be flagged.
    if PROTECTIVE_RE.search(low):
        score = min(score, 20)

    if score == 0:
        for p in SAFE_PATTERNS:
            if re.search(p, low, re.I):
                score = 5
                break

    label = "scam" if score >= 70 else ("suspicious" if score >= 30 else "safe")
    category = max(cat_scores, key=cat_scores.get) if cat_scores else ("General" if label != "safe" else "None")

    if not indicators:
        indicators.append("No known scam pattern matched - always verify unexpected messages anyway")

    explanation = _explanation(label, category)
    return {
        "risk_score": score,
        "risk_label": label,
        "category": category,
        "explanation": explanation,
        "indicators": indicators,
        "next_steps": next_steps(label, category),
        "guardian_alert": label == "scam",
        "spoken_warning": {
            "en": _spoken(label, category, "en"),
            "hi": _spoken(label, category, "hi"),
            "mr": _spoken(label, category, "mr"),
        },
        "amount_detected": _amount(text),
    }


def _explanation(label: str, category: str) -> str:
    if label == "safe":
        return ("Nothing dangerous matched: no fake-urgency, no credential ask, no money demand. "
                "Keep normal caution with unknown senders.")
    if label == "suspicious":
        return (f"Parts of this match a known {category} pattern. It is trying to pressure you without "
                "giving you time to verify. Do not act on it yet.")
    return (f"This matches the {category} playbook almost completely: "
            "it pressures you, demands action, and asks for money or credentials. "
            "Treat it as a scam until proven otherwise.")
