from fastapi import FastAPI, UploadFile, File
import shutil, os, re, time
from PIL import Image

from api.ocr_engine import extract_single_page
from api.pdf_ex import extract_pdf
from api.llm_parser import extract_with_llm

app = FastAPI(title="OCR Extraction API", version="4.0.0", docs_url="/docs")

UPLOAD_DIR = "temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def detect_document_type(text: str) -> str:
    t = text.lower()
    score = {"invoice": 0, "resume": 0, "id": 0}
    if "invoice"    in t: score["invoice"] += 3
    if "bill to"    in t: score["invoice"] += 2
    if "gst"        in t: score["invoice"] += 2
    if "total"      in t: score["invoice"] += 1
    if "amount"     in t: score["invoice"] += 1
    if "education"  in t: score["resume"] += 2
    if "experience" in t: score["resume"] += 2
    if "skills"     in t: score["resume"] += 2
    for k in ["student id","employee id","identity","card no",
              "roll","register","valid upto","principal"]:
        if k in t: score["id"] += 1
    if re.search(r"20\d{2}\s*-\s*20\d{2}", t): score["id"] += 2
    best = max(score, key=score.get)
    return best if score[best] > 0 else "general"


@app.post("/extract/pdf")
async def extract_pdf_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    start  = time.time()
    result = extract_pdf(file_path)

    pages_output = []
    for page_data in result["pages"]:
        page_text = page_data["text"]
        doc_type  = detect_document_type(page_text)

        # LLM extraction — works for ANY invoice format
        if doc_type == "invoice":
            llm_result = extract_with_llm(page_text)
            fields = llm_result.get("fields", {})
        else:
            fields = {"raw_text": page_text}

        pages_output.append({
            "page":     page_data["page"],
            "method":   page_data["method"],
            "doc_type": doc_type,
            "fields":   fields,
            "text":     page_text,
        })

    return {
        "status":      "success",
        "total_pages": result["total_pages"],
        "confidence":  round(result["summary"]["avg_confidence"], 3),
        "pages":       pages_output,
        "meta": {
            "file_name":           file.filename,
            "processing_time_sec": round(time.time() - start, 2),
        },
    }


@app.post("/extract/image")
async def extract_image_api(file: UploadFile = File(...)):
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        return {"error": "Unsupported file type. Use PNG / JPG."}

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image    = Image.open(file_path)
    result   = extract_single_page(image)
    doc_type = detect_document_type(result["formatted_text"])

    if doc_type == "invoice":
        llm_result = extract_with_llm(result["formatted_text"])
        fields = llm_result.get("fields", {})
    else:
        fields = {"raw_text": result["formatted_text"]}

    return {
        "status":     "success",
        "doc_type":   doc_type,
        "confidence": round(result["confidence_score"], 3),
        "fields":     fields,
        "raw_text":   result["formatted_text"],
    }


@app.get("/health")
def health():
    return {"status": "healthy", "version": "4.0.0"}