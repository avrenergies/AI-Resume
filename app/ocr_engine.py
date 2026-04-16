import os
import uuid
import shutil
import logging
from functools import lru_cache

from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
from PIL import Image

from app.docx_reader import docx_to_text

logger = logging.getLogger("resume_api.ocr")

TEMP_DIR = "/tmp/resume_ocr_images"


@lru_cache(maxsize=1)
def _get_reader():
    """Lazy-load EasyOCR only when OCR is actually needed."""
    import easyocr  # deferred import — avoids loading 2 GB on startup
    logger.info("Initialising EasyOCR reader (first use)...")
    return easyocr.Reader(["en"], gpu=False)


def _image_to_text(image_path: str) -> str:
    reader = _get_reader()
    result = reader.readtext(image_path, detail=0, paragraph=True)
    return " ".join(result)


def _pdf_to_text(pdf_path: str) -> str:
    # Try pdfminer first (fast, text-layer PDFs)
    try:
        text = extract_text(pdf_path)
        if text and len(text.strip()) > 100:
            logger.info("PDF extracted via pdfminer (text layer)")
            return text
    except Exception as exc:
        logger.warning("pdfminer failed: %s", exc)

    # Fallback: render pages → EasyOCR
    logger.info("Falling back to EasyOCR for scanned PDF")
    os.makedirs(TEMP_DIR, exist_ok=True)
    text = ""

    try:
        images = convert_from_path(pdf_path, dpi=300)
        for img in images:
            img_path = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.jpg")
            img.save(img_path, "JPEG")
            try:
                text += _image_to_text(img_path) + " "
            finally:
                os.remove(img_path)
    finally:
        # Clean up temp dir if empty
        try:
            if not os.listdir(TEMP_DIR):
                shutil.rmtree(TEMP_DIR, ignore_errors=True)
        except Exception:
            pass

    return text


def file_to_text(path: str) -> str:
    """
    Convert a resume file (PDF / DOCX / image) to plain text.

    IMPORTANT: we check the extension on the *original* path.
    Do NOT lower-case the full path before the check — that would break
    on mixed-case OS paths (e.g. /tmp/Resume.PDF).
    """
    ext = os.path.splitext(path)[-1].lower()   # only the extension is lowercased

    if ext == ".pdf":
        return _pdf_to_text(path)
    if ext == ".docx":
        return docx_to_text(path)
    if ext in {".jpg", ".jpeg", ".png"}:
        return _image_to_text(path)

    raise ValueError(f"Unsupported file format: {ext!r}")
