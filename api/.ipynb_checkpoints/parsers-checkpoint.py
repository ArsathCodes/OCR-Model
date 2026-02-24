import re
def find_field_bbox(value, line_items):
    if not value:
        return None

    v = str(value).lower()

    for item in line_items:
        if v in item["text"].lower():
            return item.get("bbox")

    return None
# =============================
# INVOICE TABLE PARSER
# =============================
def parse_invoice_table(text: str):

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    items = []
    i = 0

    while i < len(lines) - 4:

        # detect index row (01, 02 etc)
        if re.fullmatch(r"\d{1,3}", lines[i]):

            name = lines[i+1]
            price = lines[i+2]
            qty = lines[i+3]
            total = lines[i+4]

            if (
                re.search(r"\$?\d", price)
                and re.fullmatch(r"\d+", qty)
                and re.search(r"\$?\d", total)
            ):
                items.append({
                    "name": name,
                    "price": price,
                    "quantity": qty,
                    "total": total
                })

                i += 5
                continue

        i += 1

    return items


# =============================
# INVOICE PARSER
# =============================
def parse_invoice(text: str, line_items=None):

    def find(p):
        m = re.search(p, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    items = parse_invoice_table(text)

    totals = re.findall(r"Total[:\s\n]*\$?([0-9,.]+)", text, re.IGNORECASE)

    return {
        "invoice_number": find(r"Invoice Number[:\s\n]*#?([A-Za-z0-9\-]+)"),
        "date": find(r"Date[:\s]*([A-Za-z0-9 ,\-]+)"),
        "total_amount": totals[-1] if totals else None,
        "gst": find(r"GST.*?([0-9,.]+)"),
        "items": items
    }


# =============================
# RESUME PARSER
# =============================
def parse_resume(text: str):

    email = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phone = re.findall(r"\+?\d[\d\s\-]{8,}\d", text)

    first_line = text.split("\n")[0] if text else None

    return {
        "name": first_line,
        "email": email[0] if email else None,
        "phone": phone[0] if phone else None
    }
# =============================
# ID PARSER (FIXED)
# =============================
def parse_id(text: str):
    import re

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # name → first line with 2+ words uppercase (typical ID name)
    name = None
    for l in lines[:5]:
        if re.fullmatch(r"[A-Z ]{5,}", l) and len(l.split()) >= 2:
            name = l
            break

    # year range → validity
    validity_match = re.search(r"(20\d{2}\s*[-–]\s*20\d{2})", text)
    validity = validity_match.group(1) if validity_match else None

    # id number → long alphanumeric
    id_match = re.search(r"\b[A-Z0-9]{6,}\b", text)
    id_number = id_match.group(0) if id_match else None

    return {
        "name": name,
        "id_number": id_number,
        "validity": validity
    }
# =============================
# GENERIC PARSER
# =============================
def parse_generic(text: str):

    emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    phones = re.findall(r"\+?\d[\d\s\-]{8,}\d", text)
    amounts = re.findall(r"(?:₹|\$)?\s?\d[\d,]+(?:\.\d+)?", text)
    dates = re.findall(
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{1,2}\s[A-Za-z]+\s\d{4}\b",
        text
    )

    first_line = text.split("\n")[0] if text else None

    return {
        "possible_name": first_line,
        "emails": list(set(emails)),
        "phones": list(set(phones)),
        "amounts": list(set(amounts)),
        "dates": list(set(dates))
    }

# =============================
# ROUTER
# =============================
def parse_by_type(doc_type: str, text: str, line_items=None):

    if doc_type == "invoice":
        return parse_invoice(text, line_items)

    if doc_type == "resume":
        return parse_resume(text)

    if doc_type == "id":
        return parse_id(text)

    return parse_generic(text))