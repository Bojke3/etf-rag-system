# ETF RAG System — Technical Decisions

This document records every significant technical decision made during development,
with the reasoning behind each choice. Read this before proposing changes to core components.

---

## D1: Embedding Model — `paraphrase-multilingual-MiniLM-L12-v2`

**Decision**: Use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` instead of the default `all-MiniLM-L6-v2`.

**Why**: `all-MiniLM-L6-v2` is trained on English data only. Serbian (Cyrillic) text produces near-random embeddings with it, making cosine similarity meaningless. The multilingual model was trained on 50+ languages including Serbian/South Slavic.

**Trade-off**: Multilingual model is ~470MB vs ~90MB for English-only. Slightly slower on CPU (~90ms vs ~40ms per query). Acceptable for this use case.

**Alternatives considered**:
- `multilingual-e5-base` (intfloat) — higher quality but 1.1GB and requires query prefix formatting (`query:` / `passage:`)
- `paraphrase-multilingual-mpnet-base-v2` — better quality than MiniLM but ~3x slower

**Config**: `EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` in `.env`

---

## D2: LLM — `qwen2.5:3b` (primary), `mistral` (planned comparison)

**Decision**: Use `qwen2.5:3b` as the primary LLM for initial testing.

**Why**: `qwen2.5:3b` is 1.9GB — fast to download and run on CPU. `mistral` (4.4GB) has better multilingual support but the download was interrupted. For initial end-to-end testing, `qwen2.5:3b` is sufficient. Both will be compared in benchmarking.

**Trade-off**: `qwen2.5:3b` may produce lower-quality Serbian answers than `mistral`. This is acceptable for the first working pipeline — quality optimization comes after correctness.

**Config**: `OLLAMA_MODEL=qwen2.5:3b` in `.env`

---

## D3: Vector Store — FAISS (local, `IndexFlatIP` with L2 normalization)

**Decision**: Use FAISS `IndexFlatIP` with L2-normalized vectors (= cosine similarity).

**Why**:
1. FAISS runs locally — no cloud dependency, no API keys, no latency
2. Cosine similarity is the correct metric for sentence embeddings (measures angle, not magnitude)
3. `IndexFlatIP` is exact search (no approximation), which is fine for our scale (~100–500 chunks)

**Implementation**: In `src/embedding/__init__.py`, vectors are L2-normalized before `add()` and `search()`, so inner product equals cosine similarity.

**Alternatives considered**:
- Pinecone — cloud, requires API key, overkill for a research prototype
- ChromaDB — simpler API but adds another dependency with its own persistence format
- `IndexFlatL2` — wrong metric for embeddings (L2 distance penalizes magnitude, not angle)

**Config**: `VECTOR_STORE_TYPE=faiss`, `VECTOR_STORE_PATH=./models/vectorstore`

---

## D4: Chunk Size — 1024 characters, 150 overlap

**Decision**: Use 1024-character chunks with 150-character overlap instead of the original 512/100 defaults.

**Why**: Serbian administrative/legal text has very long compound sentences and subordinate clauses. At 512 characters, chunks frequently end mid-sentence, cutting off the predicate or the relevant clause. 1024 characters reliably captures complete thoughts from the pravilnik documents.

**Overlap rationale**: 150 characters (~2 short sentences) ensures that a concept split at a boundary is still retrievable from either adjacent chunk.

**Config**: `CHUNK_SIZE=1024`, `CHUNK_OVERLAP=150` in `.env`

**Note**: `src/data/chunking.py` defaults are `chunk_size=1000, overlap=200`. The `.env` values override these via `config.py` which is passed to `process_documents.py` argparse defaults.

---

## D5: Document Processing — Character-based chunking, not sentence/paragraph splitting

**Decision**: Use simple character-based sliding window chunking (`SimpleChunker`) rather than sentence or paragraph splitting.

**Why**: Serbian PDF text extracted by pypdf/easyocr does not reliably preserve paragraph boundaries. Sentence splitting (via nltk or spacy) requires a Serbian language model and is an extra dependency. Character-based chunking is deterministic and works regardless of text quality. Given the overlap, retrieval quality is acceptable.

**Future improvement**: Semantic chunking (split on paragraph/section boundaries) would improve retrieval quality, especially for articles (Члан X) in the pravilnik.

---

## D6: OCR — easyocr + PyMuPDF (Andrija's addition)

**Decision**: Use `easyocr` with `rs_cyrillic` language model for scanned PDFs, with PyMuPDF for page-to-image rendering.

**Why**: 6 of 7 PDFs in `DataAkti/` are scanned images — pypdf extracts 0 bytes from them. Without OCR, only 1 document is searchable. EasyOCR was chosen because it supports Serbian Cyrillic out of the box (`rs_cyrillic` language pack) and installs cleanly via pip.

**Flow**: `PDFLoader` tries pypdf first → if no text extracted AND `ETF_RAG_ENABLE_OCR != "0"` → `OCRHandler` renders pages via PyMuPDF at 2x zoom → easyocr reads rendered image.

**Trade-off**: EasyOCR is slow on CPU (~1-2 min/page). OCR quality for Cyrillic is decent but not perfect — expect occasional misreads on degraded scans. For production, Tesseract with Serbian language data would be higher quality.

**Control env vars**:
- `ETF_RAG_ENABLE_OCR=1` — enable/disable (default enabled)
- `ETF_RAG_OCR_LANGUAGES=rs_cyrillic,en` — language list
- `ETF_RAG_OCR_MAX_PAGES=10` — limit pages per document

---

## D7: `src/data/` Module Structure — Refactored into submodules

**Decision**: Split the original monolithic `src/data/__init__.py` into `document.py`, `loaders.py`, `chunking.py`, `preprocessing.py`, `ocr.py`.

**Why** (Andrija's refactor): The original single-file approach mixed unrelated concerns. The new structure follows single-responsibility: each file has one class family. This makes testing and future extension (e.g. new loaders) straightforward.

**Compatibility**: `web/app.py` and `src/rag/` do not import from `src/data/` directly — they use the embedding + retrieval layers which work with plain text strings. The refactor had zero downstream impact on the pipeline.

---

## D8: Config System — Pydantic BaseSettings reading from `.env`

**Decision**: Use `pydantic-settings` `BaseSettings` to load all configuration from `.env`.

**Why**: Single source of truth. All components read from `config` object — no scattered `os.getenv()` calls. Type validation is automatic. Easy to override in tests by creating a new `Config(...)` instance.

**Important**: `.env` is gitignored. `.env.example` is the template committed to the repo. Any new config field added to `Config` in `src/config.py` must also be documented in `.env.example`.

**Current `.env` values** (differs from `.env.example` defaults):
```
OLLAMA_MODEL=mistral              ← must change to qwen2.5:3b (mistral not installed)
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
DATA_DIR=./DataAkti               ← overrides default ./data/documents
CHUNK_SIZE=1024
CHUNK_OVERLAP=150
RETRIEVAL_THRESHOLD=0.5           ← lower than default 0.7 (more permissive)
```

---

## D9: Retrieval Threshold — 0.5 (cosine similarity)

**Decision**: Set `RETRIEVAL_THRESHOLD=0.5` instead of the default `0.7`.

**Why**: With multilingual embeddings on short queries in Serbian, cosine similarity scores tend to be lower than with English sentence-transformers. A threshold of 0.7 filtered out many genuinely relevant chunks in early testing. 0.5 is more permissive while still filtering noise.

**Risk**: At 0.5, marginally relevant chunks may be included in context. Monitor whether answers include hallucinated details from weak-match chunks.

---

## D10: Prompt Strategies — Zero-shot, Few-shot, Chain-of-Thought

**Decision**: Implement three prompt strategies in `src/llm/__init__.py`, selectable per-request via `prompt_strategy` field.

**Why**: Different question types benefit from different approaches:
- `zero_shot` — fast, good for factual lookups ("Kada počinje školska godina?")
- `few_shot` — better for format-sensitive answers (lists, dates)
- `chain_of_thought` — better for reasoning across multiple clauses

**Current state**: All three are implemented. Benchmark will determine which works best for Serbian legal/administrative text.

---

## D11: Flask over FastAPI

**Decision**: Use Flask for the web API (`web/app.py`).

**Why**: The team is more familiar with Flask. The API has only 2 endpoints (`GET /`, `POST /query`) — Flask is sufficient. FastAPI is in `requirements.txt` for future async support if needed.

**Note**: The API in `web/app.py` does NOT match the `docs/API_DOCS.md` spec exactly (no `/api/v1` prefix, no `/search`, `/documents`, `/models` endpoints). The docs describe the planned API, not the current implementation.

---

## D12: Chunking — Pluggable strategies behind a config flag

**Decision**: Chunking is a strategy interface (`src/data/chunking/`), selected end-to-end by
`CHUNK_STRATEGY`. Two implementations ship: `flat_baseline` (the original sliding window) and
`hierarchical` (parent–child). Each strategy gets its own FAISS index.

**Why**: We want to A/B the current flat chunking against hierarchical chunking for the TELFOR
paper, and add a graph-based strategy later. Previously `SimpleChunker` was hardcoded at the one
call site in `process_documents.py` and there was a single index, so trying a second approach
meant editing code and destroying the existing index.

**Naming**: The strategy is `flat_baseline`, not `flat_512` — the baseline is 1024 *characters*
(D4), and measuring `data/processed/` confirms it (`min=76 max=1024 mean=1000.8 median=1024.0`).
`flat_512` is accepted as an alias in `registry.py` so the name from the original task brief
still resolves.

**Units**: Hierarchical sizes are characters, not tokens — nothing in this project is
token-aware. Converted at ~3.5 chars/token for Serbian: parents 3600–5400 (~1024–1536 tokens),
children 900–1350 (~256–384 tokens), 12% child overlap.

**Artifacts** (one set per strategy, never mixed):
```
data/processed/<strategy>/chunks.jsonl          canonical, full metadata
models/vectorstore/index_<strategy>.faiss
models/vectorstore/metadatas_<strategy>.json
models/vectorstore/parents_<strategy>.json      hierarchical only, NOT embedded
```
`chunks.jsonl` exists because the old pipeline computed chunk metadata and then threw it away —
only the text reached disk, and `index_documents.py` re-derived `document`/`chunk_id` from the
file name. Parent chunks are held out of the index deliberately: only children are embedded,
and parents are looked up by id at retrieval time by `ParentAwareRetriever`.

**Adding a third strategy**: one entry in `STRATEGIES` in `src/data/chunking/registry.py`.
Nothing else changes — the scripts, the config flag and the index naming all read through it.

---

## D13: OCR text repair as shared preprocessing, gated by `OCR_CLEANUP`

**Decision**: `TextPreprocessor` gained four OCR-repair passes — hyphenation rejoin, wrapped-line
rejoin, page-artifact removal, repeated header/footer removal — run once per document upstream of
any chunker, controlled by `OCR_CLEANUP` (default `true`).

**Why gated**: Cleanup changes flat output too, which would break the guarantee that the baseline
is reproducible. With `OCR_CLEANUP=0` the flat strategy produces byte-identical output to the
pre-refactor `SimpleChunker`; with it on, both strategies get cleaned text, which is what a fair
A/B requires. Turning it on means the baseline index must be rebuilt — the existing
`benchmarking/runs/baseline_topk5` answers were collected against the uncleaned index.

**Queries are not cleaned**: `RAGPipeline` constructs `TextPreprocessor(ocr_cleanup=False)`. The
repair passes fix scanned documents; stripping "page numbers" out of a user's question would be
wrong.

**Page numbers**: `PDFLoader` and `OCRHandler` now join pages with `\f` instead of `\n`, so page
boundaries survive to chunking and the `page` metadata field is real. Chunkers convert `\f` back
to `\n` in the emitted chunk text.

---

## D14: Context budget is configurable and must be held fixed when comparing strategies

**Decision**: `ContextBuilder.build_context` takes its character budget from
`CONTEXT_MAX_LENGTH` (default 6000) instead of a hardcoded 2000.

**Why**: The hardcoded 2000 was silently capping retrieval. With 1024-character chunks and
`top_k=5`, `build_context` appended chunk 1 (1024), truncated chunk 2 to 976, then broke — **only
2 of 5 retrieved chunks ever reached the LLM**, and 2000/5 = 400 explains why chunks appeared to
be ~400 characters. `top_k` above ~2 bought nothing but retrieval latency, and the existing
`baseline_topk5` run was effectively top-k≈2.

**Constraint**: When A/B testing chunking strategies this value must be identical across runs.
A 4500-character hierarchical parent alone exceeds the old cap, so leaving it at 2000 would have
measured context budget rather than chunking.
