# Three-stage document pipeline

The pipeline separates extraction/OCR, chunking and vectorization. The extraction and text-cleaning algorithms are unchanged. Existing chunks, indexes and benchmark runs are not migrated automatically.

## 1. Extract text once

Run from the repository root in the project Python environment:

```powershell
python scripts/extract_documents.py --input DataAkti --output data/extracted_v1 --ocr-languages rs_cyrillic,en
```

For each document this saves:

- `raw/<document>.txt`: the complete text returned by the existing loader.
- `cleaned/<document>.txt`: the existing preprocessing result, saved before chunking.
- `manifest.json`: source hashes, text hashes, extraction options, implementation hashes and source metadata, including `ocr_used` for PDFs.

The existing PDF loader first tries native text extraction. OCR is a fallback only when the entire PDF has no extracted text, not a per-page fallback. This behavior is deliberately unchanged for comparison with the historical corpus. The snapshot does not add page-level coordinates that the current loader does not preserve. OCR failures on individual pages may still leave partial text; inspect the logs and compare coverage before freezing a snapshot.

Use `--no-ocr` to disable fallback. `--ocr-max-pages N` intentionally limits the OCR pass and should be omitted for the full-corpus baseline. The default OCR languages remain `rs_cyrillic,en`.

Extraction stops on a document-level error or empty result and returns a nonzero exit code. It publishes the manifest only after all documents succeed. A failed partial snapshot cannot be used for chunking; rerun into a fresh directory after resolving the failure.

## 2. Chunk the saved text

```powershell
python scripts/chunk_documents.py --input data/extracted_v1 --output data/chunks_v1_c1024_o150 --chunk-size 1024 --overlap 150
```

This reads only the frozen `cleaned` files named in the extraction manifest, verifies their hashes and applies the existing fixed-character chunker. It does not load PDFs, run OCR or clean the text again. Filenames remain `<document>_chunk0000.txt`, preserving compatibility with retrieval metadata and historical chunk comparisons.

To test another size, reuse the same snapshot:

```powershell
python scripts/chunk_documents.py --input data/extracted_v1 --output data/chunks_v1_c512_o150 --chunk-size 512 --overlap 150
```

Each output includes a chunk manifest with the source snapshot hash, chunking settings and individual chunk hashes. Modified snapshot text is rejected; intentional text changes require a new extraction snapshot instead of silently editing a frozen input.

`scripts/process_documents.py` detects its input. Given an extraction snapshot (a directory with `manifest.json` and `cleaned/`) it acts as this second stage and delegates to `chunk_documents.py`, without re-running OCR; OCR flags belong to `extract_documents.py` in that flow. Given a directory of documents it runs the older combined path — extraction, OCR and strategy-aware chunking in one pass — writing `chunks.jsonl` into a per-strategy subdirectory. Prefer stages 1 and 2 for the reproducible baseline; use the combined path for chunking-strategy experiments.

## 3. Vectorize and index

For a comparison with the historical all-MiniLM-L6-v2 embedding reference:

```powershell
python scripts/index_documents.py --input data/chunks_v1_c1024_o150 --output models/vectorstore_v1_c1024_o150 --model sentence-transformers/all-MiniLM-L6-v2 --device cpu
```

Indexing validates the chunk manifest and rejects extra, missing or modified chunks. It saves the existing FAISS index and metadata format, plus a manifest recording the requested embedding model, device, batch size and input hashes. This is basic provenance, not a complete resolved model-revision manifest. Historical directories without a manifest remain accepted if every text filename follows the chunk naming convention.

To compare another embedding model, reuse the same chunk directory and select a different model and output directory. OCR and chunking do not run during indexing. Embedding model initialization may download weights if they are not cached.

## Chunking strategies alongside the staged pipeline

`scripts/index_documents.py` supports two chunk layouts and auto-detects which one it was given (`--mode auto`, the default):

- **staged** — a `chunk_documents.py` output, recognised by its chunking manifest. This is the verified stage 3 described above: hashes are checked and an indexing manifest is written, producing `index.faiss` / `metadatas.json`.
- **strategy** — a `chunks.jsonl` under a per-strategy subdirectory, or a legacy flat directory of `<stem>_chunk<NNNN>.txt`. Each strategy gets its own artifacts so they never mix:

```powershell
python scripts/index_documents.py --strategy hierarchical
```

```
models/vectorstore/index_<strategy>.faiss
models/vectorstore/metadatas_<strategy>.json
models/vectorstore/parents_<strategy>.json   (hierarchical only, not embedded)
```

For hierarchical chunking only child chunks are embedded; parents go to the sidecar and are looked up by id at retrieval time. Pass `--mode staged` or `--mode strategy` to override detection. A directory of raw or cleaned document text is rejected either way.

Note that `implementation_sha256` for the chunking stage now hashes the whole `src/data/chunking` package rather than a single module, so chunk manifests written before the strategy refactor carry a value that cannot be compared against new ones.

## Output locations and migration

All three stages require a new or empty output directory and reject nested input/output locations. This prevents stale chunks from surviving a change in chunk size and protects previous indexes. There is no implicit overwrite or automatic deletion.

Defaults are `data/extracted` for extraction, `data/chunks` for chunk output and `models/vectorstore_new` for index output. Use explicit versioned paths as above for experiments. The application continues using its configured index; creating a new index does not switch the application or change `.env`.

After the first extraction, compare the new 1024/150 chunk set with `data/processed` or its backup before choosing the new study reference. Compare decoded text, filenames and counts: historical Windows files may use CRLF while newly saved files use LF, which can change byte hashes without changing text read by indexing. Differences in content should be reviewed per document. Preserve the two historical runs even if a new controlled baseline is needed.

| Change | Stages to repeat |
|---|---|
| Documents, extraction/OCR options or text preprocessing | 1, 2 and 3, in new output directories |
| Chunk size or overlap | 2 and 3 |
| Embedding model | 3 |
| Retrieval `top_k` | Retrieval and answer collection only |
| LLM | Generation from saved contexts |

The implementation can be checked without OCR, model downloads or server access:

```powershell
python -m unittest discover -s tests -p test_data_stages.py -v
```
