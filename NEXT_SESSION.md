# Next Session — What To Do

Last updated: 2026-05-20

## Status as of today

- FAISS index rebuilt — 75 real chunks indexed ✅
- Flask API working — tested with benchmark question Q001 ✅
- `.env` fixed — `OLLAMA_MODEL=qwen2.5:3b` ✅
- web/app.py fixed — sys.path added so it runs from any directory ✅

---

## Step 1: Chat UI (do this first)

Build a minimal web page so you can type questions and see answers without using curl.

**Files to create/edit:**
- `web/templates/chat.html` — new HTML page (plain HTML + JS fetch, no frameworks)
- `web/app.py` — add one route: `GET /chat` → serve the HTML page

**Features:**
- Text box for question
- Submit button
- Answer area
- Shows retrieved source chunks + similarity scores
- Loading spinner (Ollama takes ~20s per answer)

**How to use once built:**
```bash
cd ~/etf-rag-system
source venv/bin/activate
python web/app.py
# Then open http://localhost:8000/chat in your browser
```

---

## Step 2: Benchmark Runner (after chat UI)

Write `scripts/run_benchmark.py` to automatically score all 60 questions.

**What it does:**
- Loads `benchmarking/OAS_prec_23_benchmark.json`
- Calls the pipeline directly for each question (no server needed)
- Scores answers with ROUGE (fast, already implemented in `src/evaluation/__init__.py`)
- Saves per-question results + averages to `benchmarking/results_<timestamp>.json`

**How to run:**
```bash
python scripts/run_benchmark.py
# Takes ~20 min (60 questions × ~20s each on CPU)
```

**Classes to reuse (already written):**
- `ROUGEMetric` — `src/evaluation/__init__.py`
- `RAGPipeline` — `src/rag/__init__.py`
- Pipeline init pattern — copy from `web/app.py` → `get_pipeline()`

---

## Reminder: Starting Ollama

Ollama should already be running. If not:
```bash
ollama serve   # only if port 11434 is not already bound
ollama list    # should show qwen2.5:3b
```

Do NOT run `ollama serve` if it's already running — it will error.
