import time
import numpy as np
from paddleocr import PaddleOCR
from pdf2image import convert_from_path

# ---------- CONFIG ----------
POPPLER_PATH = r"C:\Users\Asus\Downloads\ocr-project\poppler\poppler-25.12.0\Library\bin"

ocr = PaddleOCR(
    lang="en",
    use_angle_cls=False,
    show_log=False
)

# ---------- SINGLE PAGE ----------
def extract_single_page(image):

    start = time.time()
    image = image.resize((1200, int(image.height * 1200 / image.width)))

    result = ocr.ocr(np.array(image))

    line_items = []
    lines = []
    confs = []

    if result and result[0]:
        for line in result[0]:
            bbox = line[0]
            text = line[1][0]
            conf = line[1][1]

            if conf > 0.5:
                lines.append(text)
                confs.append(conf)
                line_items.append({
                    "text": text,
                    "confidence": float(conf),
                    "bbox": [list(p) for p in bbox]
                })

    extracted_text = "\n".join(lines)
    confidence = float(np.mean(confs)) if confs else 0.0
    process_time = time.time() - start

    return {
        "extracted_text": extracted_text,
        "formatted_text": extracted_text,
        "confidence_score": confidence,
        "line_items": line_items,          # ← bbox data here
        "processing_time_sec": round(process_time, 2)
    }


# ---------- PDF ----------
def extract_pdf(pdf_path):

    pages = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

    all_text = []
    all_line_items = []   # ← FIX: collect line_items across all pages
    confs = []
    total_time = 0

    for page in pages:
        res = extract_single_page(page)
        all_text.append(res["formatted_text"])
        all_line_items.extend(res["line_items"])   # ← accumulate
        confs.append(res["confidence_score"])
        total_time += res["processing_time_sec"]

    raw_text = "\n\n".join(all_text)
    avg_conf = float(np.mean(confs)) if confs else 0.0

    return {
        "status": "success",
        "extracted_text": raw_text,
        "formatted_text": raw_text,
        "confidence_score": avg_conf,
        "line_items": all_line_items,       # ← FIX: now available for parser
        "metadata": {
            "pages": len(pages),
            "language_detected": "en",
            "processing_time_sec": round(total_time, 2)
        }
    }