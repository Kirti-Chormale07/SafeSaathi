"""Accuracy check for SafeSaathi's detector.

Run from the backend/ folder:
    venv\\Scripts\\python.exe scripts\\eval.py

Prints accuracy, per-class precision/recall and a confusion matrix so you can
show REAL numbers on stage (judges love that). Add --llm to score the LLM
engine instead of the heuristic engine.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services import heuristics, llm, rag  # noqa: E402
from app.services.urlcheck import extract_urls  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "eval_samples.json"
CLASSES = ("safe", "suspicious", "scam")


async def predict(text: str, use_llm: bool) -> str:
    if use_llm:
        a = await llm.analyze_with_llm(text, rag.retrieve(text), "en")
        if a:
            return a["risk_label"]
    return heuristics.classify(text, url_count=len(extract_urls(text)))["risk_label"]


async def main() -> None:
    use_llm = "--llm" in sys.argv
    samples = json.loads(DATA.read_text(encoding="utf-8"))
    y_true, y_pred = [], []
    for s in samples:
        y_true.append(s["label"])
        y_pred.append(await predict(s["text"], use_llm))

    n = len(y_true)
    correct = sum(t == p for t, p in zip(y_true, y_pred))
    print(f"\nEngine : {'LLM' if use_llm else 'Heuristic (rules)'}")
    print(f"Samples: {n}")
    print(f"Accuracy: {correct}/{n} = {100 * correct / n:.1f}%\n")

    print("Per-class metrics:")
    print(f"{'class':<12}{'precision':>10}{'recall':>8}{'f1':>8}{'support':>9}")
    for c in CLASSES:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        sup = sum(1 for t in y_true if t == c)
        print(f"{c:<12}{prec:>10.2f}{rec:>8.2f}{f1:>8.2f}{sup:>9}")

    print("\nConfusion matrix (rows=true, cols=pred):")
    print(f"{'':<12}" + "".join(f"{c:>11}" for c in CLASSES))
    for t in CLASSES:
        row = "".join(f"{sum(1 for tt, pp in zip(y_true, y_pred) if tt == t and pp == c):>11}" for c in CLASSES)
        print(f"{t:<12}{row}")

    wrong = [(t, p, s["text"]) for t, p, s in zip(y_true, y_pred, samples) if t != p]
    if wrong:
        print(f"\nMisclassified ({len(wrong)}):")
        for t, p, txt in wrong:
            print(f"  [{t} -> {p}] {txt[:90]}...")


if __name__ == "__main__":
    asyncio.run(main())
