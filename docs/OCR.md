# OCR Test Fallback

This project currently has a minimal OCR fallback in `src/data/ocr.py`.

The flow is:

1. `PDFLoader` first tries normal PDF text extraction with `pypdf`.
2. If no text is found, it calls `OCRHandler`.
3. `OCRHandler` renders scanned PDF pages with PyMuPDF and reads them with EasyOCR.

This is intentionally simple, only for testing the rest of the RAG pipeline.

Requirements:

- Python package: `easyocr`
- Python package: `PyMuPDF`

Limitations:

- It uses EasyOCR with English by default.
- It renders full PDF pages, which can be slow on larger documents.
- For production OCR, use a stronger implementation with page rendering, language settings, and better error reporting.
