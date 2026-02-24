"""
llm_parser.py
-------------
Groq LLM based invoice extraction.
Any invoice format → perfect structured JSON.
No rules. No fine-tuning. Just works.
"""

import os
import re
import json
from groq import Groq

# ── Setup ─────────────────────────────────────────────────────────────────────
# Get free API key from: https://console.groq.com
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "your-groq-api-key-here")

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are an invoice data extraction AI.
Extract structured data from invoice OCR text and return ONLY valid JSON.
No explanation. No markdown. No extra text. Just JSON.

Output format:
{
  "invoice_number": "string or null",
  "date": "string or null",
  "vendor": "string or null",
  "total_amount": "string or null",
  "gst": "string or null",
  "items": [
    {
      "name": "string",
      "hsn": "string or null",
      "quantity": "string",
      "unit": "string or null",
      "unit_price": "string",
      "total": "string"
    }
  ]
}

Rules:
- Extract ALL line items from the invoice table
- unit_price and total should be plain numbers without currency symbols (e.g. "3500.00")
- quantity should be plain number (e.g. "10")
- If a field is not found, use null
- Do not include subtotal/tax rows in items array"""


def extract_with_llm(ocr_text: str) -> dict:
    """
    Send OCR text to Groq LLM → get structured invoice JSON back.
    Works for ANY invoice format automatically.
    """
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Extract invoice data from this text:\n\n{ocr_text}"}
            ],
            temperature=0,        # deterministic output
            max_tokens=2048,
        )

        raw = response.choices[0].message.content.strip()

        # Clean markdown if LLM adds it
        raw = re.sub(r"```json|```", "", raw).strip()

        result = json.loads(raw)
        return {"status": "success", "fields": result}

    except json.JSONDecodeError as e:
        return {"status": "error", "error": f"JSON parse failed: {e}", "raw": raw}
    except Exception as e:
        return {"status": "error", "error": str(e)}