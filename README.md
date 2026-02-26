# OCR Extraction API

Production-ready OCR service using **PaddleOCR + PyMuPDF**.

## Models Used

| Model | Purpose |
|-------|---------|
| **PaddleOCR** (PP-OCRv3) | Text detection & recognition for scanned PDFs/images |
| **PyMuPDF** (fitz) | Native text & table extraction for digital PDFs |

> Digital PDFs → PyMuPDF native extraction (fast, 100% accuracy)  
> Scanned PDFs → PaddleOCR (PP-OCRv3 det/rec models)

## Project Structure

```
ocr-project/
├── api/
│   ├── api.py          # FastAPI endpoints
│   ├── ocr_engine.py   # PaddleOCR wrapper (scanned docs)
│   ├── pdf_ex.py       # PyMuPDF extractor
│   └── parsers.py      # Field extraction parser + doc type detection
├── docker/
│   └── Dockerfile
├── tests/
│   └── test_api.py
├── Jenkinsfile
└── README.md
```

## Supported Document Types

| Type | Fields Extracted |
|------|-----------------|
| **Invoice** | invoice_number, date, vendor, total_amount, gst, items |
| **Purchase Order** | po_number, date, delivery_date, vendor, payment_terms, gst, items |
| **Resume** | name, email, phone, skills, experience, education, certifications |
| **ID Card** | name, employee_id, designation, department, valid_until, blood_group |
| **General** | key fields auto-detected |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/extract/pdf` | Extract from PDF (digital + scanned) |
| POST | `/extract/image` | Extract from image (JPG/PNG) |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

## Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start API
uvicorn api.api:app --reload

# 3. Open Swagger UI
# http://127.0.0.1:8000/docs
```

## Docker Setup

```bash
# Build image
docker build -f docker/Dockerfile -t ocr-api .

# Run container
docker run -d \
  --name ocr-api \
  -p 8000:8000 \
  ocr-api

# Check health
curl http://localhost:8000/health
```

## Jenkins Setup

```
1. Install Jenkins (https://www.jenkins.io)
2. Install plugins: Git, Docker, Pipeline
3. New Item → Pipeline
4. Pipeline script from SCM → Git → your repo URL
5. Build Now
```

## Sample Response

```json
{
  "status": "success",
  "total_pages": 1,
  "confidence": 1.0,
  "pages": [{
    "page": 1,
    "doc_type": "invoice",
    "fields": {
      "invoice_number": "INV/2025/0118",
      "date": "05 Feb 2025",
      "vendor": "Priya Textiles Ltd.",
      "total_amount": "88,983.50",
      "gst": "9,534.00",
      "items": [
        {
          "S.No": "1",
          "Item Description": "Cotton Fabric - White (50m Roll)",
          "HSN": "520811",
          "Qty": "10",
          "Unit": "Roll",
          "Rate (Rs.)": "3,500.00",
          "Amount (Rs.)": "35,000.00"
        }
      ]
    }
  }]
}
```