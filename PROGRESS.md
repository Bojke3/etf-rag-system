# ETF RAG System — Progress

## Urađeno

- Python `venv` kreiran, `requirements.txt` instaliran
- `.env` konfigurisan (multilingual embedding model, chunk 1024/150, FAISS vector store)
- Ollama instaliran, `qwen2.5:3b` model preuzet
- Embedding modeli keširani lokalno (`paraphrase-multilingual-MiniLM-L12-v2`)
- `DataAkti/` — 7 PDF dokumenata (pravilnici ETF-a)
- 75 chunkova iz `Pravilnik_o_OAS_preciscen_jun_2023.pdf` u `data/processed/`
- `src/data/` refaktorisan u module: `document.py`, `loaders.py`, `chunking.py`, `preprocessing.py`
- OCR podrška dodata (`easyocr`) za skenirana PDF-ova — Andrija
- Benchmark dataset kreiran: `benchmarking/OAS_prec_23_benchmark.json` (60 pitanja/odgovora)
- Bugfix: `chunk_size` i `chunk_overlap` sada se čitaju iz `.env` u `process_documents.py`

## Sledeći Koraci

1. **Update `.env`** — promeniti `OLLAMA_MODEL=mistral` → `OLLAMA_MODEL=qwen2.5:3b`
2. **Instalirati nove deps** — `pip install -r requirements.txt` (easyocr, PyMuPDF)
3. **OCR procesiranje** — pokrenuti `process_documents.py` sa `--ocr-languages rs_cyrillic,en` za 6 skeniranih PDF-ova (~10-30 min)
4. **Rebuild FAISS index** — pokrenuti `index_documents.py` (trenutni index ima samo 2 test chunka)
5. **Pokrenuti web server** — `python web/app.py`, testirati upit iz benchmark dataseta
6. **Evaluacija** — pokrenuti benchmark skriptu nad `OAS_prec_23_benchmark.json`
