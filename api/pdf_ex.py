"""
pdf_ex.py — PyMuPDF based PDF extractor
Digital PDF  → native text + built-in table finder
Scanned PDF  → PaddleOCR fallback
"""

import re
import fitz  # PyMuPDF
import numpy as np

SCANNED_THRESHOLD = 50


def clean_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'\s{3,}', '  ', line)
        lines.append(line)
    return "\n".join(lines)


def page_to_image(page: fitz.Page, dpi: int = 150):
    import cv2
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    arr = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def run_paddle_ocr(img):
    from paddleocr import PaddleOCR
    ocr = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
    result = ocr.ocr(img, cls=False)
    if not result or not result[0]:
        return "", 0.0
    lines, confs = [], []
    for item in result[0]:
        text, conf = item[1]
        if conf > 0.5:
            lines.append(text)
            confs.append(conf)
    return "\n".join(lines), float(np.mean(confs)) if confs else 0.0


def extract_tables_native(page: fitz.Page) -> list:
    """Use PyMuPDF built-in table finder — perfect for digital PDFs."""
    tables = []
    try:
        finder = page.find_tables()
        for tbl in finder.tables:
            df = tbl.to_pandas()
            if df.empty:
                continue
            # Clean up None/empty values
            rows = []
            for _, row in df.iterrows():
                clean_row = {str(k): str(v) if v else "" for k, v in row.items()}
                rows.append(clean_row)
            tables.append({
                "headers":    list(df.columns),
                "line_items": rows,
                "row_count":  len(rows),
            })
    except Exception:
        pass
    return tables


def extract_page(page: fitz.Page, page_num: int) -> dict:
    native_text = page.get_text("text")
    is_scanned  = len(native_text.strip()) < SCANNED_THRESHOLD

    if not is_scanned:
        clean   = clean_text(native_text)
        tables  = extract_tables_native(page)
        conf    = 1.0
        method  = "native"
    else:
        img             = page_to_image(page)
        ocr_text, conf  = run_paddle_ocr(img)
        clean           = clean_text(ocr_text)
        tables          = []
        method          = "ocr"

    return {
        "page":       page_num,
        "method":     method,
        "confidence": round(conf, 4),
        "text":       clean,
        "tables":     tables,
        "has_tables": len(tables) > 0,
    }


def extract_pdf(pdf_path: str) -> dict:
    doc        = fitz.open(pdf_path)
    pages_data = [extract_page(page, i) for i, page in enumerate(doc, start=1)]
    doc.close()

    avg_conf = round(sum(p["confidence"] for p in pages_data) / len(pages_data), 4) if pages_data else 0.0

    return {
        "total_pages": len(pages_data),
        "pages":       pages_data,
        "summary": {
            "digital_pages":     sum(1 for p in pages_data if p["method"] == "native"),
            "scanned_pages":     sum(1 for p in pages_data if p["method"] == "ocr"),
            "pages_with_tables": sum(1 for p in pages_data if p["has_tables"]),
            "avg_confidence":    avg_conf,
        },
    }