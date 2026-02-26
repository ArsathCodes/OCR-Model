"""
ner_parser.py - spaCy NER based document field extractor
"""

import re
import spacy
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ocr_ner_model")
_nlp = None

def load_model():
    global _nlp
    if _nlp is None:
        if os.path.exists(MODEL_PATH):
            _nlp = spacy.load(MODEL_PATH)
        else:
            raise FileNotFoundError(
                f"NER model not found at {MODEL_PATH}\n"
                "Run: python api/ner_trainer.py"
            )
    return _nlp


def extract_with_ner(text: str, doc_type: str) -> dict:
    nlp = load_model()
    all_entities = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        doc = nlp(line)
        for ent in doc.ents:
            all_entities.append((ent.text, ent.label_))

    if doc_type == "invoice":
        return _map_invoice_fields(all_entities, text)
    elif doc_type == "purchase_order":
        return _map_po_fields(all_entities, text)
    elif doc_type == "resume":
        return _map_resume_fields(all_entities, text)
    elif doc_type == "id_card":
        return _map_id_fields(all_entities, text)
    else:
        return _map_general_fields(all_entities)


def _first(entities, label):
    for text, lbl in entities:
        if lbl == label:
            return text
    return None

def _all(entities, label):
    return [text for text, lbl in entities if lbl == label]

def _regex(text, pattern):
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _map_invoice_fields(entities, text):
    invoice_no  = _first(entities, "INVOICE_NO") or _regex(text, r"Invoice\s*(?:No|Number)[:\s#]*([A-Za-z0-9/\-]+)")
    date_val    = _first(entities, "DATE")        or _regex(text, r"(?:Invoice\s*)?Date[:\s]*(\d{1,2}[\s\-][A-Za-z]{3,}[\s\-]\d{4})")
    vendor      = _first(entities, "VENDOR")      or _regex(text, r"(?:Bill\s*To|Vendor)[:\s]*\n?([A-Za-z][\w\s\.,&]+(?:Ltd|Pvt|Inc|Co)\.?)")
    total       = _first(entities, "TOTAL_AMOUNT") or _regex(text, r"Grand\s*Total[:\s\n]*(?:Rs\.?|INR)?\s*([\d,]+\.?\d*)")
    gst         = _first(entities, "GST_AMOUNT")  or _regex(text, r"(?:IGST|CGST|GST)[^:\n]*[:\s]*(?:Rs\.?)?\s*([\d,]+\.?\d*)")
    return {
        "invoice_number": invoice_no,
        "date":           date_val,
        "vendor":         vendor,
        "total_amount":   total,
        "gst":            gst,
        "items":          [],
    }


def _map_po_fields(entities, text):
    po_num   = _first(entities, "PO_NUMBER")    or _regex(text, r"PO[-\s]*(?:Number|No)?[:\s]*\n?(PO[-\w]+)")
    date_val = _first(entities, "DATE")          or _regex(text, r"PO\s*Date[:\s]*\n?(\d{1,2}[\s\-][A-Za-z]{3,}[\s\-]\d{4})")
    delivery = _first(entities, "DELIVERY_DATE") or _regex(text, r"Delivery\s*Date[:\s]*\n?(\d{1,2}[\s\-][A-Za-z]{3,}[\s\-]\d{4})")
    payment  = _first(entities, "PAYMENT_TERMS") or _regex(text, r"Payment\s*Terms[:\s]*\n?([^\n]{3,30})")
    total    = _first(entities, "TOTAL_AMOUNT")  or _regex(text, r"Grand\s*Total[:\s\n]*(?:Rs\.?)[\s\n]*([\d,]+\.?\d*)")
    gst      = _first(entities, "GST_AMOUNT")    or _regex(text, r"GST[^:\n]*[:\s]*(?:Rs\.?)\s*([\d,]+\.?\d*)")

    # Vendor — skip label lines
    vendor = _first(entities, "VENDOR")
    if not vendor:
        SKIP = re.compile(r"^(po |invoice|date|delivery|payment|shipping|gstin|gst)", re.IGNORECASE)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines):
            if re.search(r"vendor\s*:", line, re.IGNORECASE):
                for nxt in lines[i+1:i+6]:
                    if SKIP.search(nxt) or nxt.endswith(":"):
                        continue
                    if re.search(r"[A-Za-z]{3,}", nxt) and len(nxt) > 4:
                        vendor = nxt
                        break
                break

    return {
        "po_number":      po_num,
        "date":           date_val,
        "delivery_date":  delivery,
        "vendor":         vendor,
        "payment_terms":  payment,
        "total_amount":   total,
        "gst":            gst,
        "items":          [],
    }


def _map_resume_fields(entities, text):
    name  = _first(entities, "PERSON")
    email = _first(entities, "EMAIL")   or _regex(text, r"[\w.\-]+@[\w.\-]+\.\w+")
    phone = _first(entities, "PHONE")   or _regex(text, r"(?:\+91[\s\-]?)?[6-9]\d{4}[\s\-]?\d{5}")
    score = _first(entities, "SCORE")   or _regex(text, r"CGPA[:\s]*([\d.]+/\d+)")

    # Name fallback — first line of resume
    if not name:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines and re.match(r"^[A-Z][a-z]+\s+[A-Z][a-z]+", lines[0]):
            name = lines[0]

    return {
        "name":          name,
        "email":         email,
        "phone":         phone,
        "job_title":     _first(entities, "JOB_TITLE"),
        "organizations": _all(entities, "ORGANIZATION"),
        "degrees":       _all(entities, "DEGREE"),
        "institutions":  _all(entities, "INSTITUTION"),
        "score":         score,
    }


def _map_id_fields(entities, text):
    def after_label(label):
        m = re.search(label + r"\s*:\s*\n([^\n]+)", text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    return {
        "name":           _first(entities, "PERSON")      or after_label(r"Employee\s*Name"),
        "employee_id":    _first(entities, "EMPLOYEE_ID") or after_label(r"Employee\s*ID"),
        "designation":    _first(entities, "DESIGNATION") or after_label(r"Designation"),
        "department":     _first(entities, "DEPARTMENT")  or after_label(r"Department"),
        "valid_until":    _first(entities, "VALIDITY")    or after_label(r"Valid\s*Until"),
        "blood_group":    _first(entities, "BLOOD_GROUP") or after_label(r"Blood\s*Group"),
    }


def _map_general_fields(entities):
    result = {}
    for text, label in entities:
        key = label.lower()
        if key not in result:
            result[key] = text
    return result