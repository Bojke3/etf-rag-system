# ETF RAG System — Progress

Last updated: 2026-05-18

---

## Project Structure

```
etf-rag-system/
├── DataAkti/                          # 7 source PDFs (Serbian ETF rulebooks)
├── benchmarking/
│   └── OAS_prec_23_benchmark.json     # 60 Q&A pairs for evaluation
├── data/
│   └── processed/                     # .txt chunk files (gitignored, 75 files)
├── models/
│   └── vectorstore/                   # FAISS index + metadatas.json (gitignored)
├── scripts/
│   ├── process_documents.py           # PDF → .txt chunks (with OCR fallback)
│   ├── index_documents.py             # .txt chunks → FAISS vector index
│   └── setup_ollama_models.sh         # Pulls mistral, llama2, neural-chat
├── src/
│   ├── config.py                      # Pydantic BaseSettings, reads .env
│   ├── constants.py                   # Model lists, supported formats, metrics
│   ├── data/
│   │   ├── document.py                # Document dataclass: text + metadata dict
│   │   ├── loaders.py                 # PDFLoader, WordLoader, TextLoader, Factory
│   │   ├── chunking.py                # SimpleChunker — overlapping character chunks
│   │   ├── preprocessing.py           # TextPreprocessor — whitespace/newline cleanup
│   │   └── ocr.py                     # OCRHandler — easyocr + PyMuPDF for scanned PDFs
│   ├── embedding/
│   │   └── __init__.py                # SentenceTransformerEmbedding + FAISSVectorStore
│   ├── retrieval/
│   │   └── __init__.py                # SimpleRetriever (threshold filter) + ContextBuilder
│   ├── llm/
│   │   └── __init__.py                # OllamaClient + PromptTemplate (zero/few/CoT)
│   ├── rag/
│   │   └── __init__.py                # RAGPipeline: retrieve → prompt → generate
│   ├── evaluation/
│   │   └── __init__.py                # BLEUMetric, ROUGEMetric, BERTScoreMetric, Evaluator
│   ├── chatbot/
│   │   └── __init__.py                # RAGAgent with conversation history (stub)
│   └── utils/
│       └── __init__.py                # setup_logging, ensure_directories, get_file_paths
├── web/
│   └── app.py                         # Flask REST API: GET /, POST /query
├── tests/
│   ├── conftest.py
│   ├── test_document_loader.py
│   └── test_embedding.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── OCR.md
│   ├── SETUP.md
│   ├── RESEARCH.md
│   ├── BENCHMARKING.md
│   └── API_DOCS.md
├── main.py                            # Demo: loads all PDFs, prints first 3 chunks
├── test_structure.py                  # Smoke test for imports
├── .env                               # Local config (gitignored)
└── .env.example                       # Config template
```

---

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| Python venv | ✅ | `venv/` exists, dependencies installed |
| `.env` config | ✅ | Configured, Pydantic reads all values |
| Embedding model | ✅ | `paraphrase-multilingual-MiniLM-L12-v2` cached at `~/.cache/huggingface/hub/` |
| Document loading | ✅ | PDFLoader, WordLoader, TextLoader all working |
| Text preprocessing | ✅ | TextPreprocessor cleans whitespace/newlines |
| Chunking | ✅ | SimpleChunker: 1024 chars, 150 overlap |
| OCR handler | ✅ | Code complete in `src/data/ocr.py`, uses easyocr + PyMuPDF |
| 75 real chunks | ✅ | In `data/processed/` from `Pravilnik_o_OAS_preciscen_jun_2023.pdf` |
| qwen2.5:3b | ✅ | Installed via Ollama (1.9 GB) |
| Flask API code | ✅ | `web/app.py` complete, lazy pipeline init |
| Evaluation metrics | ✅ | BLEU, ROUGE, BERTScore code exists in `src/evaluation/` |
| Benchmark dataset | ✅ | 60 Q&A pairs in `benchmarking/OAS_prec_23_benchmark.json` |

## What Does NOT Work Yet

| Component | Status | Blocker |
|-----------|--------|---------|
| FAISS index | ❌ | Contains 2 old dummy test chunks (May 12). Must rebuild |
| 6 scanned PDFs | ❌ | OCR has not been run yet — 0 chunks from these |
| Web server | ❌ | Never started with real data; would return answers from 2 test chunks |
| Benchmark runner | ❌ | Script doesn't exist — needs to be written |
| mistral model | ❌ | 4.4 GB download was interrupted; not installed |

---

## How to Run

```bash
# Activate environment
source venv/bin/activate

# Step 1: Fix .env — change model to what's actually installed
# Edit .env: OLLAMA_MODEL=qwen2.5:3b

# Step 2: Install latest deps (Andrija added easyocr, PyMuPDF)
pip install -r requirements.txt

# Step 3: Process all documents with OCR for scanned PDFs
# (~10-30 min on CPU; easyocr downloads ~500MB models on first run)
python scripts/process_documents.py \
  --input DataAkti \
  --output data/processed \
  --chunk-size 1024 \
  --overlap 150 \
  --ocr-languages rs_cyrillic,en

# Step 4: Rebuild FAISS index
python scripts/index_documents.py

# Step 5: Start web server
python web/app.py

# Step 6: Test with a benchmark question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Када по правилу почиње школска година на Факултету?", "top_k": 5}'

# Expected: answer matches "Школска година по правилу почиње 1. октобра..."
```

---

## Next Steps (Priority Order)

1. **Fix `.env`** — `OLLAMA_MODEL=qwen2.5:3b`
2. **`pip install -r requirements.txt`** — get easyocr and PyMuPDF
3. **Run OCR processing** — extracts text from 6 scanned PDFs
4. **Rebuild FAISS index** — index all real chunks
5. **Test web server end-to-end** — verify real Q&A works
6. **Write benchmark runner script** — iterate over `OAS_prec_23_benchmark.json`, call `/query`, score with ROUGE
7. **Pull mistral** (`ollama pull mistral`) for comparison experiments
8. **Evaluate OCR quality** — manually check a few chunks from scanned PDFs for Cyrillic accuracy

---

## Known Issues and Bugs

| Issue | File | Details |
|-------|------|---------|
| `.env` has wrong model | `.env` L3 | `OLLAMA_MODEL=mistral` but mistral not installed |
| FAISS index is stale | `models/vectorstore/` | May 12 timestamp, 2 dummy chunks |
| easyocr not yet run | — | OCR models (~500MB) will download on first `process_documents.py` run |
| Benchmark runner missing | — | `src/evaluation/` has metric classes but no script to run against JSON dataset |

---

## Model Status

| Model | Type | Size | Status |
|-------|------|------|--------|
| `qwen2.5:3b` | Ollama LLM | 1.9 GB | ✅ Installed |
| `mistral` | Ollama LLM | 4.4 GB | ❌ Not installed (download interrupted) |
| `paraphrase-multilingual-MiniLM-L12-v2` | Embedding | ~470 MB | ✅ Cached at `~/.cache/huggingface/hub/` |
| `all-MiniLM-L6-v2` | Embedding | ~90 MB | ✅ Cached (not used — English only) |

---

## Benchmark Dataset

**File**: `benchmarking/OAS_prec_23_benchmark.json`

- 60 question/answer pairs from `Pravilnik_o_OAS_preciscen_jun_2023.pdf`
- Schema: `id`, `type` (`single_chunk`), `difficulty` (`easy`/`medium`/`hard`), `question`, `expected_answer`, `source_document`, `source_section`
- All questions are in Serbian Cyrillic
- **No evaluation script yet** — needs to be written

---

## Team

- **Vuk Bojovic** — environment setup, pipeline config, retrieval, bugfixes
- **Andrija Trnavcevic** — `src/data/` refactor into modules, OCR integration (easyocr + PyMuPDF)

**Deadline**: TELFOR 2026 — September 4, 2026
