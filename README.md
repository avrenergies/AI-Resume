# Resume Parsing API — v7.0

Production-ready resume parsing API. Accepts every common resume format.

## Supported file formats

| Format | Extension | Method |
|--------|-----------|--------|
| PDF (text layer) | `.pdf` | pdfminer (fast) |
| PDF (scanned) | `.pdf` | EasyOCR fallback |
| Word 2007+ | `.docx` | python-docx + docx2txt |
| Word 97-2003 | `.doc` | antiword → LibreOffice → XML |
| WPS Office | `.wps` | Same as .doc |
| OpenDocument | `.odt` | XML extraction → LibreOffice |
| Rich Text | `.rtf` | striprtf |
| Plain Text | `.txt` | Direct read (UTF-8/UTF-16/Latin-1) |
| JPEG | `.jpg` `.jpeg` | EasyOCR |
| PNG | `.png` | EasyOCR |
| BMP | `.bmp` | PIL → EasyOCR |
| TIFF | `.tiff` `.tif` | PIL → EasyOCR |
| WebP | `.webp` | PIL → EasyOCR |
| GIF | `.gif` | PIL → EasyOCR |

## What's fixed vs v6

| # | Fix |
|---|-----|
| 1 | All resume formats accepted (was only PDF/DOCX/JPG/PNG) |
| 2 | `.doc` handled via antiword + LibreOffice fallback |
| 3 | `.odt` handled via XML + LibreOffice fallback |
| 4 | `.rtf` handled via striprtf |
| 5 | `.txt` handled with multi-encoding fallback |
| 6 | All images (BMP, TIFF, WEBP, GIF) normalised before OCR |
| 7 | `/health` endpoint now reports all supported formats |
| 8 | Better error message when unsupported format sent |

## All v6 fixes are included

- Word-boundary education regex (no more MBA false match)
- Phone deduplication to E164
- No trailing comma in currentWorkLocation  
- API key required from env (no hardcoded default)
- CORS restricted to explicit origins
- Rate limiting (slowapi + nginx)
- Lazy EasyOCR loading
- spaCy used for PERSON NER name fallback
- Expanded SKILL_DB (100+ skills)

## Quick start (local)

```bash
cp .env.example .env
# edit .env — set RESUME_API_KEY

python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# For .doc support on Mac:
brew install antiword libreoffice

# For .doc support on Ubuntu:
sudo apt install antiword libreoffice-writer

RESUME_API_KEY=dev-key uvicorn app.main:app --reload
```

## VPS deployment

```bash
sudo bash deploy.sh
# follow printed instructions to set env vars + get SSL cert
```

## Endpoints

| Method | Path | Auth | Rate | Description |
|--------|------|------|------|-------------|
| GET  | `/health` | None | — | Health + supported formats |
| POST | `/parse-resume` | x-api-key | 30/min | Parse from URL |
| POST | `/parse-resume-upload` | x-api-key | 30/min | Parse from file upload |
| POST | `/v2/parse-resume` | x-api-key | 20/min | URL + AI job match |
| POST | `/v2/parse-resume-upload` | x-api-key | 20/min | Upload + AI job match |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `RESUME_API_KEY` | Yes | API secret — app won't start without it |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS origins |
