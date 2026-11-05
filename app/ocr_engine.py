from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
import easyocr
import os
import uuid
import shutil

from app.docx_reader import docx_to_text


# Initialize EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

TEMP_DIR = "temp_images"


#  IMAGE TO TEXT 

def image_to_text(image_path):

    try:
        result = reader.readtext(
            image_path,
            detail=0,
            paragraph=True,
            contrast_ths=0.05,
            adjust_contrast=0.7,
            text_threshold=0.4
            )

        # MUST be inside function
        return " ".join(result)

    except Exception:
        return ""


#  PDF TO TEXT 

def pdf_to_text(pdf_path):

    try:

        text = extract_text(pdf_path)

        if text and len(text.strip()) > 100:
            return text

    except Exception:
        pass

    os.makedirs(TEMP_DIR, exist_ok=True)

    text = ""

    try:

        images = convert_from_path(pdf_path, dpi=300)

        for img in images:

            img_path = f"{TEMP_DIR}/{uuid.uuid4()}.jpg"

            img.save(img_path)

            text += image_to_text(img_path) + "\n"

            os.remove(img_path)

    except Exception:
        pass

    if os.path.exists(TEMP_DIR) and not os.listdir(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)

    return text


#  FILE ROUTER 

def file_to_text(path):

    path = path.lower()

    if path.endswith(".pdf"):
        return pdf_to_text(path)

    if path.endswith(".docx"):
        return docx_to_text(path)

    if path.endswith((".jpg", ".jpeg", ".png")):
        return image_to_text(path)

    raise ValueError("Unsupported file format")
