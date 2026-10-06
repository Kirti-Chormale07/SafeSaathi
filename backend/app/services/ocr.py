"""Screenshot text extraction: local Tesseract -> vision LLM -> None."""
import io

from .llm import vision_ocr


async def extract_text(file_bytes: bytes, content_type: str) -> tuple[str, str]:
    """Returns (text, engine). Engine is 'tesseract' | 'llm-vision' | 'none'."""
    # 1) Local OCR (free, offline) - works if Tesseract binary is installed.
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        # Grow tiny screenshots so OCR reads them better
        if img.width < 1000:
            scale = 1000 / img.width
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        for lang in ("eng+hin", "eng"):
            try:
                txt = pytesseract.image_to_string(img, lang=lang)
                if txt and txt.strip():
                    return txt.strip(), "tesseract"
            except Exception:
                continue
    except Exception:
        pass

    # 2) Vision model (Claude / GPT-4o) - needs an API key but no install.
    txt = await vision_ocr(file_bytes, content_type)
    if txt:
        return txt, "llm-vision"

    return "", "none"
