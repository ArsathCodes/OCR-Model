# OCR Extraction API

Production-ready OCR service using PaddleOCR + PyMuPDF + Groq LLM.

## Project Structure

```
ocr-project/
├── api/
│   ├── api.py          # FastAPI endpoints
│   ├── ocr_engine.py   # PaddleOCR wrapper
│   ├── pdf_ex.py       # PyMuPDF extractor
│   ├── llm_parser.py   # Groq LLM invoice parser
│   └── parsers.py      # Rule-based fallback parser
├── docker/
│   └── Dockerfile
├── tests/
│   └── test_api.py
├── app.py              # Hugging Face Space
├── Jenkinsfile         # Jenkins CI/CD
├── .gitlab-ci.yml      # GitLab CI/CD
├── requirements.txt
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/extract/pdf` | Extract from PDF |
| POST | `/extract/image` | Extract from image |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

## Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set Groq API key
export GROQ_API_KEY="your-key-here"   # Linux/Mac
$env:GROQ_API_KEY = "your-key-here"   # Windows PowerShell

# 3. Start API
uvicorn api.api:app --reload

# 4. Open Swagger UI
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
  -e GROQ_API_KEY=your-key-here \
  ocr-api

# Check health
curl http://localhost:8000/health
```

## GitLab Setup

```bash
# 1. Initialize git
git init
git remote add origin https://gitlab.com/YOUR_USERNAME/ocr-project.git

# 2. Copy .gitlab-ci.yml to root
cp .gitlab/.gitlab-ci.yml .gitlab-ci.yml

# 3. Add GROQ_API_KEY in GitLab:
#    Settings → CI/CD → Variables → Add GROQ_API_KEY

# 4. Push
git add .
git commit -m "Initial commit"
git push -u origin main
```

## Jenkins Setup

```
1. Install Jenkins (https://www.jenkins.io)
2. Install plugins: Git, Docker, Pipeline
3. New Item → Pipeline
4. Pipeline script from SCM → Git → your GitLab URL
5. Add GROQ_API_KEY in Jenkins Credentials
6. Build Now
```

## Hugging Face Deployment

```bash
# 1. Install HF CLI
pip install huggingface_hub

# 2. Login
huggingface-cli login

# 3. Create Space at https://huggingface.co/new-space
#    - SDK: Gradio
#    - Name: ocr-extraction-api

# 4. Push
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/ocr-extraction-api
git push hf main
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key (free at console.groq.com) |

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
          "name": "Cotton Fabric - White (50m Roll)",
          "hsn": "520811",
          "quantity": "10",
          "unit": "Roll",
          "unit_price": "3500.00",
          "total": "35000.00"
        }
      ]
    }
  }]
}
```