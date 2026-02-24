"""
Hugging Face Space — OCR Extraction API
Upload PDF or Image → Get structured JSON output
"""

import gradio as gr
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from api.pdf_ex import extract_pdf
from api.ocr_engine import extract_single_page
from api.llm_parser import extract_with_llm
from PIL import Image
import re


def detect_type(text):
    t = text.lower()
    score = {"invoice": 0}
    if "invoice" in t: score["invoice"] += 3
    if "bill to" in t: score["invoice"] += 2
    if "gst"     in t: score["invoice"] += 2
    if "total"   in t: score["invoice"] += 1
    if "amount"  in t: score["invoice"] += 1
    return "invoice" if score["invoice"] >= 3 else "general"


def process_file(file):
    if file is None:
        return "Please upload a file."

    path = file.name
    ext  = path.lower().split(".")[-1]

    try:
        if ext == "pdf":
            result    = extract_pdf(path)
            page      = result["pages"][0]
            text      = page["text"]
            doc_type  = detect_type(text)
            method    = page["method"]
            pages     = result["total_pages"]
            conf      = result["summary"]["avg_confidence"]

        elif ext in ("jpg", "jpeg", "png"):
            image    = Image.open(path)
            result   = extract_single_page(image)
            text     = result["formatted_text"]
            doc_type = detect_type(text)
            method   = "ocr"
            pages    = 1
            conf     = result["confidence_score"]
        else:
            return "Unsupported file type. Upload PDF, JPG, or PNG."

        if doc_type == "invoice":
            llm_result = extract_with_llm(text)
            fields     = llm_result.get("fields", {})
        else:
            fields = {"message": "Not an invoice. Raw text extracted.", "text": text[:500]}

        output = {
            "status":     "success",
            "doc_type":   doc_type,
            "method":     method,
            "pages":      pages,
            "confidence": round(conf, 3),
            "fields":     fields,
        }
        return json.dumps(output, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, indent=2)


# ── Gradio UI ─────────────────────────────────────────────────────────────────
demo = gr.Interface(
    fn=process_file,
    inputs=gr.File(label="Upload PDF or Image (JPG/PNG)"),
    outputs=gr.Textbox(label="Extracted JSON Output", lines=30),
    title="OCR Extraction API",
    description="Upload an invoice PDF or image to extract structured data using PaddleOCR + LLM.",
    examples=[],
    theme=gr.themes.Soft(),
)

if __name__ == "__main__":
    demo.launch()