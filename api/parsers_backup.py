import re


def find_field_bbox(value, line_items):
    if not value or not line_items:
        return None
    v = str(value).lower()
    for item in line_items:
        if v in item["text"].lower():
            return item.get("bbox")
    return None


# ── Helpers ───────────────────────────────────────────────────────────────────

UNIT_WORDS = {"roll","spool","litre","liter","box","kg","piece","pack",
              "nos","set","mtr","pcs","unit","bag","bottle","sheet","pair"}

def _is_hsn(t):    return bool(re.fullmatch(r"\d{6,8}", t.strip()))
def _is_amount(t): return ("," in t or ("." in t and len(t) > 4)) and bool(re.search(r"\d{3,}", t))
def _is_pct(t):    return bool(re.fullmatch(r"\d{1,2}%", t.strip()))
def _is_unit(t):   return t.strip().lower() in UNIT_WORDS
def _is_qty(t):    return bool(re.fullmatch(r"\d{1,3}", t.strip())) and not _is_hsn(t) and not _is_amount(t)
def _is_name(t):   return bool(re.search(r"[A-Za-z]{3,}", t)) and not _is_unit(t) and not _is_pct(t)
def _is_stop(t):   return any(s in t.lower() for s in {
    "subtotal","sub total","cgst","sgst","igst","total gst",
    "grand total","payment","bank","thank","round off"})

HEADER_WORDS = {"description","particulars","hsn","hsn code","qty","quantity",
                "unit price","amount","rate","item","s.no","sno","unit"}

def _is_header(t): return t.lower().strip("(). ") in HEADER_WORDS or \
                          any(h in t.lower() for h in HEADER_WORDS)

def _clean(t):
    t = re.sub(r"[₹$\s]", "", t)
    t = re.sub(r"Rs\.?", "", t)
    return t.replace(",", "").strip()


# ── Invoice table parser ──────────────────────────────────────────────────────

def parse_invoice_table_text(text: str) -> list:
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Find table start — use LAST header line index
    # (avoids break on non-header words like "IGST %")
    last_header_idx = -1
    for i, line in enumerate(lines):
        if _is_header(line):
            last_header_idx = i

    if last_header_idx != -1:
        start_idx = last_header_idx + 1
    else:
        start_idx = -1
        for idx, line in enumerate(lines):
            if "description" in line.lower() or "amount (rs" in line.lower():
                start_idx = idx + 1
                break

    if start_idx == -1:
        return []

    table_lines = []
    for line in lines[start_idx:]:
        if _is_stop(line):
            break
        table_lines.append(line)

    items = []
    i = 0

    while i < len(table_lines):
        line = table_lines[i]

        if _is_stop(line): break
        # Skip stray row numbers
        if re.fullmatch(r"\d{1,2}", line) and not _is_amount(line):
            i += 1; continue
        if not _is_name(line):
            i += 1; continue

        name = line
        hsn = qty = unit = unit_price = total = None
        j = i + 1

        while j < len(table_lines) and (j - i) <= 10:
            nxt = table_lines[j]
            if _is_stop(nxt): break
            if _is_name(nxt) and not _is_hsn(nxt) and not _is_amount(nxt): break

            if _is_hsn(nxt) and hsn is None:
                hsn = nxt
            elif _is_qty(nxt) and qty is None and hsn is not None:
                qty = nxt
            elif _is_unit(nxt) and unit is None:
                unit = nxt
            elif _is_pct(nxt):
                pass  # skip GST %
            elif _is_amount(nxt) and unit_price is None:
                unit_price = _clean(nxt)
            elif _is_amount(nxt) and total is None:
                total = _clean(nxt)
            elif re.fullmatch(r"\d{1,2}", nxt) and qty is not None and not _is_amount(nxt):
                pass  # skip stray row numbers

            j += 1

        if unit_price:
            item = {"name": name, "hsn": hsn or "", "quantity": qty or "1",
                    "unit_price": unit_price, "total": total or unit_price}
            if unit:
                item["unit"] = unit
            items.append(item)
            i = j
        else:
            i += 1

    return items


# ── Invoice parser ────────────────────────────────────────────────────────────

def parse_invoice(text: str, line_items=None):

    def find(p):
        m = re.search(p, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    invoice_number = find(
        r"Invoice\s*(?:Number|No|#|Num|No\.)[:\s/]*([A-Za-z0-9\-/]+)"
    )

    date_match = re.search(
        r"\b(?:Invoice\s*Date|Date)\b[\s:\n]*"
        r"(\d{1,2}[\s\-/][A-Za-z]{3,9}[\s\-/]\d{2,4}"
        r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        text, re.IGNORECASE
    )
    date_val = date_match.group(1).strip() if date_match else None

    amt_pat = r"(?:Rs\.?|₹|\$)\s*([\d,]+(?:\.\d+)?)"

    grand = re.search(r"Grand\s*Total[:\s\n]*" + amt_pat, text, re.IGNORECASE)
    total_amount = grand.group(1) if grand else None
    if not total_amount:
        totals = re.findall(r"\bTotal\b[\s:\n]*" + amt_pat, text, re.IGNORECASE)
        total_amount = totals[-1] if totals else None

    # GST — IGST / CGST+SGST / Total GST
    total_gst = re.search(r"Total\s*GST[:\s\n]*" + amt_pat, text, re.IGNORECASE)
    if total_gst:
        gst_val = total_gst.group(1)
    else:
        igst = re.search(r"IGST[^:\n]*[:\s\n]*" + amt_pat, text, re.IGNORECASE)
        cgst = re.search(r"CGST[^:\n]*[:\s\n]*" + amt_pat, text, re.IGNORECASE)
        sgst = re.search(r"SGST[^:\n]*[:\s\n]*" + amt_pat, text, re.IGNORECASE)
        if igst:
            gst_val = igst.group(1)
        elif cgst and sgst:
            try:
                gst_val = str(round(
                    float(cgst.group(1).replace(",","")) +
                    float(sgst.group(1).replace(",","")), 2))
            except Exception:
                gst_val = cgst.group(1)
        else:
            gst_val = None

    # Vendor — skip label/invoice-number lines after "Bill To:"
    LABEL_PAT = re.compile(
        r"^(invoice|due|gstin|gst|po |phone|email|date|payment|bill|no\.|number|#|inv[/\-])",
        re.IGNORECASE
    )
    vendor = None
    lines_v = [l.strip() for l in text.split("\n") if l.strip()]
    for vi, vline in enumerate(lines_v):
        if re.search(r"bill\s*to", vline, re.IGNORECASE):
            for nxt in lines_v[vi+1:vi+8]:
                if LABEL_PAT.search(nxt):
                    continue
                if re.fullmatch(r"[A-Za-z0-9/\-]+", nxt) and "/" in nxt:
                    continue  # skip INV/2025/0118 style numbers
                if re.search(r"[A-Za-z]{3,}", nxt) and len(nxt) > 4:
                    vendor = nxt
                    break
            break

    items = parse_invoice_table_text(text)

    return {
        "invoice_number": invoice_number,
        "date":           date_val,
        "vendor":         vendor,
        "total_amount":   total_amount,
        "gst":            gst_val,
        "items":          items,
    }


# ── Resume / ID / Generic ─────────────────────────────────────────────────────

def parse_resume(text: str, line_items=None):
    email = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.findall(r"\+?\d[\d\s\-]{8,}\d", text)
    return {
        "name":  text.split("\n")[0].strip() if text else None,
        "email": email[0] if email else None,
        "phone": phone[0].strip() if phone else None,
    }

def parse_id(text: str, line_items=None):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    name = next((l for l in lines[:5]
                 if re.fullmatch(r"[A-Z ]{5,}", l) and len(l.split()) >= 2), None)
    validity = re.search(r"(20\d{2}\s*[-–]\s*20\d{2})", text)
    id_num   = re.search(r"\b[A-Z0-9]{6,}\b", text)
    return {
        "name":      name,
        "id_number": id_num.group(0) if id_num else None,
        "validity":  validity.group(1) if validity else None,
    }

def parse_generic(text: str, line_items=None):
    return {
        "possible_name": text.split("\n")[0].strip() if text else None,
        "emails":  list(set(re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))),
        "phones":  list(set(re.findall(r"\+?\d[\d\s\-]{8,}\d", text))),
        "amounts": list(set(re.findall(r"(?:Rs\.?|₹|\$)\s?\d[\d,]+(?:\.\d+)?", text))),
    }

def parse_by_type(doc_type: str, text: str, line_items=None):
    return {"invoice": parse_invoice, "resume": parse_resume,
            "id": parse_id}.get(doc_type, parse_generic)(text, line_items)