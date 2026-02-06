from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
import easyocr
import os
import uuid
import shutil
from PIL import Image

from app.docx_reader import docx_to_text

reader = easyocr.Reader(['en'], gpu=False)
TEMP_DIR = "temp_images"


def image_to_text(image_path):
    result = reader.readtext(image_path, detail=0, paragraph=True)
    return " ".join(result)


def pdf_to_text(pdf_path):
    try:
        text = extract_text(pdf_path)
        if text and len(text.strip()) > 100:
            return text
    except:
        pass

    os.makedirs(TEMP_DIR, exist_ok=True)
    text = ""

    images = convert_from_path(pdf_path, dpi=300)

    for img in images:
        img_name = f"{TEMP_DIR}/{uuid.uuid4()}.jpg"
        img.save(img_name, "JPEG")

        text += image_to_text(img_name) + " "
        os.remove(img_name)

    if not os.listdir(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)

    return text


def file_to_text(path):

    path = path.lower()

    if path.endswith(".pdf"):
        return pdf_to_text(path)

    if path.endswith(".docx"):
        return docx_to_text(path)

    if path.endswith((".jpg", ".jpeg", ".png")):
        return image_to_text(path)

    raise ValueError("Unsupported file format")
