# ETF RAG System — Full Context

This file is written for a new Claude session starting without any prior conversation history.
Read this file and PROGRESS.md before doing anything else in this project.

---

## What This Project Is

A RAG (Retrieval-Augmented Generation) system for answering student questions about
ETF (Elektrotehički fakultet, Belgrade) faculty regulations. Students ask questions
like "When does the school year start?" or "How many ECTS credits is the full load per year?"
and the system answers using the actual text of the official rulebooks.

**Goal**: Submit a conference paper to TELFOR 2026 (deadline: September 4, 2026).

**Language**: Everything is in Serbian. Documents use both Cyrillic and Latin script.
The main corpus is in Cyrillic (ћирилица). LLM answers should be in Serbian.

---

## The Pipeline (How It Works)

```
PDF files in DataAkti/
        ↓
PDFLoader (pypdf first, easyocr fallback for scanned pages)
        ↓
TextPreprocessor (cleanup whitespace/newlines)
        ↓
SimpleChunker (1024 chars, 150 overlap → .txt files in data/processed/)
        ↓
SentenceTransformerEmbedding (paraphrase-multilingual-MiniLM-L12-v2)
        ↓
FAISSVectorStore (IndexFlatIP + L2 norm = cosine similarity)
        ↓
[saved to models/vectorstore/]

User query (POST /query)
        ↓
embed query with same model
        ↓
FAISS search → top-k chunks with score >= threshold (0.5)
        ↓
ContextBuilder (concatenate up to 2000 chars)
        ↓
PromptTemplate (zero_shot / few_shot / chain_of_thought)
        ↓
OllamaClient → http://localhost:11434/api/generate
        ↓
JSON response: {answer, sources, retrieved_chunks, timing}
```

---

## Repository Layout (What Each File Does)

### Source Library (`src/`)

**`src/config.py`**
Pydantic `BaseSettings` class. Reads ALL config from `.env`. Import `from src.config import config` to get the singleton. Fields include: `embedding_model`, `ollama_model`, `ollama_base_url`, `chunk_size`, `chunk_overlap`, `retrieval_threshold`, `vector_store_path`, `processed_data_dir`, `data_dir`.

**`src/data/document.py`**
`@dataclass Document(text: str, metadata: Dict[str, Any])`. Base unit returned by loaders. `metadata` always has `source`, `file_name`, `file_type`; PDFs add `ocr_used: bool`.

**`src/data/loaders.py`**
`PDFLoader` — tries pypdf, falls back to `OCRHandler` if text is empty and `ETF_RAG_ENABLE_OCR != "0"`.
`WordLoader` — python-docx.
`TextLoader` — plain utf-8 read.
`DocumentLoaderFactory.load_document(path)` — dispatches by file extension.

**`src/data/preprocessing.py`**
`TextPreprocessor.clean(text)` — removes multiple spaces/tabs, collapses 3+ newlines to 2. Applied to `document.text` before chunking.

**`src/data/chunking.py`**
`SimpleChunker(chunk_size, overlap).split(document) → List[Chunk]`. Character-based sliding window. Each `Chunk` inherits the document's metadata plus `chunk_index`.

**`src/data/ocr.py`**
`OCRHandler` — lazy-loads `easyocr.Reader` (singleton, expensive). Renders PDF pages via `fitz` (PyMuPDF) at 2x zoom, passes numpy image to easyocr, joins text. Configured via env vars `ETF_RAG_OCR_LANGUAGES`, `ETF_RAG_OCR_MAX_PAGES`.

**`src/embedding/__init__.py`**
`SentenceTransformerEmbedding` wraps sentence-transformers. Properties: `embed_text(str) → np.ndarray`, `embed_texts(List[str]) → np.ndarray`, `embedding_dim → int` (384 for MiniLM-L12-v2).
`FAISSVectorStore` — `IndexFlatIP`, L2-normalizes before add/search (= cosine similarity). `save(path)` writes `index.faiss` + `metadatas.json`. `load(path)` restores both.

**`src/retrieval/__init__.py`**
`SimpleRetriever(embedding_model, vector_store, threshold).retrieve(query, top_k) → List[Dict]`. Embeds query, searches FAISS, filters by score >= threshold.
`ContextBuilder.build_context(docs, max_length=2000)` — concatenates `doc['text']` values, truncates to fit.

**`src/llm/__init__.py`**
`OllamaClient(base_url, model).generate(prompt) → str`. POSTs to `/api/generate` with `stream=False`. Timeout 120s.
`PromptTemplate` — static methods `format_zero_shot`, `format_few_shot`, `format_chain_of_thought`.

**`src/rag/__init__.py`**
`RAGPipeline(retriever, llm_client, embedding_model).process_query(question, top_k, prompt_strategy, include_sources, examples) → Dict`.
Returns: `{status, question, answer, retrieved_chunks, processing_time_ms, retrieval_time_ms, generation_time_ms, sources}`.
Returns `{"status": "error", "error": "No relevant documents found"}` if retrieval returns empty list.

**`src/evaluation/__init__.py`**
`BLEUMetric`, `ROUGEMetric` (rouge1/2/L), `BERTScoreMetric`, `Evaluator`. All implemented but NOT yet wired to any benchmark runner script.

**`src/chatbot/__init__.py`**
`RAGAgent` with conversation history per `user_id`. Not connected to any live chat platform yet.

### Scripts

**`scripts/process_documents.py`**
CLI entry point for document processing. Args: `--input`, `--output`, `--chunk-size`, `--overlap`, `--no-ocr`, `--ocr-max-pages`, `--ocr-languages`. Defaults read from `config` (which reads `.env`). Writes `{stem}_chunk{NNNN}.txt` files.

**`scripts/index_documents.py`**
CLI entry point for building FAISS index. Reads `.txt` files from `data/processed/`, embeds in batches of 32, saves to `models/vectorstore/`. Parses chunk filename to extract `document` name and `chunk_id` for metadata.

### Web API

**`web/app.py`**
Flask app. Two endpoints:
- `GET /` — health check, returns model config
- `POST /query` — body: `{question, top_k?, prompt_strategy?, examples?}` — runs full RAG pipeline

Pipeline is lazy-initialized on first request. Loads FAISS index from `config.vector_store_path` if it exists.

---

## Data Directory (`DataAkti/`)

7 PDF files, all Serbian legal/academic documents:

| File | Size | Readable | Chunks |
|------|------|----------|--------|
| `Pravilnik_o_OAS_preciscen_jun_2023.pdf` | 331 KB | ✅ (digital text) | 75 |
| `Pravilnik o osnovnim akademskim studijama.pdf` | 3.3 MB | ❌ (scanned image) | 0 |
| `Pravilnik o upisu studenata.pdf` | ~1 MB | ❌ (scanned) | 0 |
| `Izmena Pravilnika o osnovnim akademskim studijama.pdf` | small | ❌ (scanned) | 0 |
| `Odluka o izmenama i dopunama Pravilnika o OAS.pdf` | small | ❌ (scanned) | 0 |
| `Odluka o izmeni Pravilnika o osnovnim akademskim studijama.pdf` | small | ❌ (scanned) | 0 |
| `Odluka_OAS_jun_23.pdf` | small | ❌ (scanned) | 0 |

The "prečišćen" (consolidated) version is the most important document — it includes all amendments merged in.

---

## Current State of Generated Artifacts

**`data/processed/`** (gitignored)
- 75 `.txt` files: `Pravilnik_o_OAS_preciscen_jun_2023_chunk0000.txt` through `_chunk0074.txt`
- Created with new `TextPreprocessor` (whitespace cleaned)
- Created with chunk_size=1024, overlap=150
- 0 chunks from the 6 scanned PDFs (OCR not yet run)

**`models/vectorstore/`** (gitignored)
- `index.faiss` + `metadatas.json` — **STALE**, timestamp May 12
- Contains only 2 dummy test chunks: `{"document":"test","chunk_id":0,"text":"Elektrotehnicke studije traju cetiri godine."}` and similar
- **Must be rebuilt** before the web server can answer real questions

---

## Environment Configuration (`.env`)

```env
LLM_TYPE=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral          ← BUG: must change to qwen2.5:3b (mistral not installed)
OLLAMA_TEMPERATURE=0.7
OLLAMA_TOP_P=0.9
OLLAMA_MAX_TOKENS=2048

EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DEVICE=cpu

VECTOR_STORE_TYPE=faiss
VECTOR_STORE_PATH=./models/vectorstore

DATA_DIR=./DataAkti
PROCESSED_DATA_DIR=./data/processed
EMBEDDING_DIR=./data/embeddings

CHUNK_SIZE=1024
CHUNK_OVERLAP=150

RETRIEVAL_TOP_K=5
RETRIEVAL_THRESHOLD=0.5

LOG_LEVEL=INFO
LOG_DIR=./logs

WEB_HOST=0.0.0.0
WEB_PORT=8000
WEB_DEBUG=false
```

---

## Installed Models

**Ollama** (`ollama list`):
- `qwen2.5:3b` — 1.9 GB — INSTALLED ✅
- `mistral` — 4.4 GB — NOT INSTALLED ❌ (download was interrupted mid-session)

**HuggingFace** (cached at `~/.cache/huggingface/hub/`):
- `paraphrase-multilingual-MiniLM-L12-v2` — ✅ (used for embeddings)
- `all-MiniLM-L6-v2` — ✅ (not used — English only)

---

## Benchmark Dataset

**File**: `benchmarking/OAS_prec_23_benchmark.json`

60 question/answer pairs in Serbian Cyrillic. All sourced from `Pravilnik_o_OAS_preciscen_jun_2023.pdf`.

Schema:
```json
{
  "id": "Q001",
  "type": "single_chunk",
  "difficulty": "easy",
  "question": "Када по правилу почиње школска година на Факултету?",
  "expected_answer": "Школска година по правилу почиње 1. октобра и траје 12 календарских месеци.",
  "source_document": "Pravilnik_o_OAS_preciscen_jun_2023.pdf",
  "source_section": "Члан 9"
}
```

**No benchmark runner script exists yet.** It needs to be written to: load the JSON, call `POST /query` for each question, compare answer to `expected_answer` using ROUGE or semantic similarity, produce a summary score.

---

## What the Prompts Look Like

**Zero-shot** (default):
```
Question: {question}
Context: {context}
Answer:
```

**Few-shot**:
```
Examples:
{examples}

Now answer this question based on the context:
Question: {question}
Context: {context}
Answer:
```

**Chain-of-thought**:
```
Let's think through this step by step.
Question: {question}
Context: {context}
Step 1: Identify key information in the context
Step 2: Reason through the problem
Final Answer:
```

The prompts are in English, which means the LLM is instructed in English but the context is in Serbian. This may cause the LLM to respond in English sometimes. A future improvement is to write prompts in Serbian.

---

## Important Gotchas

1. **Ollama must be running** before starting the web server. It's already running (port 11434 is bound). Do not run `ollama serve` — it will fail because the port is already in use.

2. **FAISS index must be rebuilt** before the web server returns real answers. The current index on disk has 2 dummy test chunks from May 12, not the real 75 chunks from `data/processed/`.

3. **easyocr downloads language models** (~500MB for `rs_cyrillic`) on first run of `process_documents.py` with OCR enabled. This is slow and expected — it only happens once.

4. **Chunk files are gitignored** (`data/processed/`). If you clone fresh, you must run `process_documents.py` before `index_documents.py`.

5. **The FAISS index is gitignored** (`models/vectorstore/`). Always run `index_documents.py` after a fresh clone.

6. **`config.py` has different defaults than `.env`** — `config.py` says `chunk_size=1000`, but `.env` overrides to `1024`. The `.env` value wins.

7. **`web/app.py` does not match `docs/API_DOCS.md`** — the docs describe a planned v2 API. The real API has only `GET /` and `POST /query`.

---

## Git Log (recent)

```
f5f6ca3  Update PROGRESS.md with detailed project status and next steps
a5cd7b8  Add PROGRESS.md with current status and next steps
73c7c3d  Add benchmarking folder with OAS benchmark dataset
3583fd2  (Andrija) some commit
53f0c11  (Andrija) konflijt u scripts — merge OCR branch into main
3e22481  Fix chunk size and overlap not being read from config/.env
55434a9  (previous) Add benchmarking folder
3b5ac5f  (Andrija) data izmene — refactor src/data/ into modules + add OCR
```

---

## Team

- **Vuk Bojovic** (vuki253@gmail.com) — primary author of this session's work
- **Andrija Trnavcevic** — collaborator, added `src/data/` module refactor and OCR support
- Both are researchers targeting TELFOR 2026
