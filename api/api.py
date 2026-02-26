from fastapi import FastAPI, UploadFile, File
import shutil, os, re, time
import fitz  # PyMuPDF
import numpy as np
from PIL import Image

from api.ocr_engine import extract_single_page
from api.parsers import parse_by_type, detect_doc_type

app = FastAPI(title="OCR Extraction API", version="4.0.0", docs_url="/docs")

UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)
SCANNED_THRESHOLD = 50


# ── PyMuPDF table → items ─────────────────────────────────────────────────────
def pymupdf_table_to_items(page) -> list:
    items = []
    try:
        finder = page.find_tables()
        for tbl in finder.tables:
            df = tbl.to_pandas()
            if df.empty or len(df) < 2:
                continue
            for _, row in df.iterrows():
                item = {str(k).strip(): str(v).strip()
                        for k, v in row.items()
                        if str(v) not in ("nan", "None", "")}
                vals_lower = str(list(item.values())).lower()
                if any(h in vals_lower for h in ["description","item","hsn","qty","amount","rate"]):
                    continue
                if item:
                    items.append(item)
    except Exception:
        pass
    return items


# ── PDF endpoint ──────────────────────────────────────────────────────────────
@app.post("/extract/pdf")
async def extract_pdf_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    start = time.time()
    doc   = fitz.open(file_path)
    pages_output = []
    confidence = 1.0

    for page_num, page in enumerate(doc, start=1):
        native_text = page.get_text("text").strip()
        is_scanned  = len(native_text) < SCANNED_THRESHOLD

        if not is_scanned:
            # ── Digital PDF: PyMuPDF native ──
            page_text  = native_text
            confidence = 1.0
            doc_type   = detect_doc_type(page_text)
            fields     = parse_by_type(doc_type, page_text)

            # Invoice / PO → use PyMuPDF table finder for items
            if doc_type in ("invoice", "purchase_order"):
                pymupdf_items = pymupdf_table_to_items(page)
                if pymupdf_items:
                    fields["items"] = pymupdf_items

        else:
            # ── Scanned PDF: PaddleOCR ──
            mat = fitz.Matrix(150/72, 150/72)
            pix = page.get_pixmap(matrix=mat)
            import cv2
            arr     = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
            img     = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

            res        = extract_single_page(pil_img)
            page_text  = res["formatted_text"]
            confidence = res["confidence_score"]
            doc_type   = detect_doc_type(page_text)
            fields     = parse_by_type(doc_type, page_text, res.get("line_items"))

        pages_output.append({
            "page":     page_num,
            "doc_type": doc_type,
            "fields":   fields,
            "text":     page_text,
        })

    doc.close()
    elapsed = round(time.time() - start, 2)

    return {
        "status":      "success",
        "total_pages": len(pages_output),
        "confidence":  round(confidence, 3),
        "pages":       pages_output,
        "meta": {
            "file_name":           file.filename,
            "processing_time_sec": elapsed,
        },
    }


# ── Image endpoint ────────────────────────────────────────────────────────────
@app.post("/extract/image")
async def extract_image_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Unsupported file type"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image    = Image.open(file_path)
    result   = extract_single_page(image)
    text     = result["formatted_text"]
    doc_type = detect_doc_type(text)
    fields   = parse_by_type(doc_type, text, result.get("line_items"))

    return {
        "status":     "success",
        "doc_type":   doc_type,
        "confidence": round(result["confidence_score"], 3),
        "fields":     fields,
        "raw_text":   text,
    }


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy", "version": "4.0.0", "mode": "offline"}