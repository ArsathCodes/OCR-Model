from fastapi import FastAPI, UploadFile, File
import shutil
import os
from PIL import Image

from ocr_engine import extract_pdf, extract_single_page
from parsers import parse_by_type

app = FastAPI()

UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =============================
# DOCUMENT TYPE DETECTION
# =============================
def detect_document_type(text: str):

    import re

    t = text.lower()

    score = {
        "invoice": 0,
        "resume": 0,
        "id": 0
    }

    # ---------- invoice ----------
    if "invoice" in t: score["invoice"] += 2
    if "gst" in t: score["invoice"] += 1
    if "total" in t: score["invoice"] += 1

    # ---------- resume ----------
    if "education" in t: score["resume"] += 1
    if "skills" in t: score["resume"] += 1
    if "experience" in t: score["resume"] += 1

    # ---------- id (STRONGER) ----------
    id_keywords = [
        "id",
        "identity",
        "card",
        "student",
        "college",
        "university",
        "department",
        "roll",
        "register",
        "valid",
        "principal"
    ]

    for k in id_keywords:
        if k in t:
            score["id"] += 1

    # strong pattern → year range
    if re.search(r"20\d{2}\s*-\s*20\d{2}", t):
        score["id"] += 2

    doc_type = max(score, key=score.get)

    if score[doc_type] == 0:
        return "general"

    return doc_type


# =============================
# PDF ENDPOINT
# =============================
@app.post("/extract/pdf")
async def extract_pdf_api(file: UploadFile = File(...)):

    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF allowed"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = extract_pdf(file_path)

    doc_type = detect_document_type(result["formatted_text"])
    fields = parse_by_type(doc_type, result["formatted_text"])

    return {
        "status": "success",
        "doc_type": doc_type,
        "fields": fields,
        "confidence": round(result["confidence_score"], 3),
        "meta": {
            "file_name": file.filename,
            "pages": result["metadata"]["pages"],
            "processing_time_sec": result["metadata"]["processing_time_sec"]
        }
    }


# =============================
# IMAGE ENDPOINT
# =============================
@app.post("/extract/image")
async def extract_image_api(file: UploadFile = File(...)):

    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Unsupported file type"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image = Image.open(file_path)

    result = extract_single_page(image)

    doc_type = detect_document_type(result["formatted_text"])

    fields = parse_by_type(
        doc_type,
        result["formatted_text"],
        result.get("line_items")
    )

    return {
        "doc_type": doc_type,
        "fields": fields,
        "confidence": round(result["confidence_score"], 3),
        "meta": {
            "processing_time_sec": result["processing_time_sec"],
            "lines_detected": len(result.get("line_items", []))
        }
    }
