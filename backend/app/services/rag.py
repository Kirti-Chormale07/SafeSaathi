"""Tiny RAG layer over SafeSaathi's scam-playbook store.

No vector database needed for a hackathon: we do keyword/phrase retrieval
over scam_patterns.json and hand the top matches to the LLM (or show them
directly in heuristic mode).
"""
import json
import re
from functools import lru_cache

from ..config import DATA_DIR

STOP = {"the", "a", "an", "to", "of", "and", "or", "is", "in", "on", "for", "you", "your", "my"}


@lru_cache(maxsize=1)
def _load() -> list:
    path = DATA_DIR / "scam_patterns.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def all_playbooks() -> list:
    return _load()


def _tokens(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9₹]+", text.lower()) if t not in STOP and len(t) > 1}


def retrieve(text: str, top_k: int = 3) -> list:
    """Return playbooks whose keywords/signals appear in the message."""
    low = (text or "").lower()
    toks = _tokens(text)
    scored = []
    for pb in _load():
        score = 0
        matched = []
        for kw in pb["keywords"]:
            if kw in low:                # phrase hit (strong)
                score += 3
                matched.append(kw)
        kw_toks = set()
        for kw in pb["keywords"]:
            kw_toks |= _tokens(kw)
        overlap = toks & kw_toks
        score += len(overlap)            # token hit (weak)
        if score:
            scored.append({
                "id": pb["id"],
                "title": pb["title"],
                "category": pb["category"],
                "score": score,
                "matched": matched or sorted(overlap),
                "explanation": pb["explanation"],
                "do": pb["do"],
                "dont": pb["dont"],
            })
    scored.sort(key=lambda p: -p["score"])
    return scored[:top_k]


def best_category(text: str, fallback: str) -> str:
    """Category from the strongest playbook match, else the heuristic's."""
    hits = retrieve(text, top_k=1)
    return hits[0]["category"] if hits else fallback
