# Vector indexes

One directory per benchmark configuration, named `vectorstore_<config-id>_c<chunk-size>_o<overlap>`.
`registry.json` is the authoritative binding of config ID to embedding model; this file is its
readable form.

| Config | Directory | Embedding model | Dim | Chunks | Provenance |
|---|---|---|---|---|---|
| `c001` | `vectorstore_c001_c1024_o150` | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 205, from `data/chunks_v1_c1024_o150` | retrospective audit |
| `c002` | `vectorstore_c002_c1024_o150` | `BAAI/bge-m3` | 1024 | 205, same chunk snapshot | build manifest |

Both indexes are `IndexFlatIP` over L2-normalised vectors, built from the **same** 205 chunks —
their `metadatas.json` hashes are identical. Only the encoder differs, which is what makes
`c001` vs `c002` a controlled embedding comparison.

## Why the pairing is checked in code

An index is only meaningful to the encoder that built it. A dimension mismatch raises, but two
different 384-dimensional encoders load each other's index **without any error** and return
quietly wrong neighbours. `sentence-transformers/all-MiniLM-L6-v2` (c001) and
`paraphrase-multilingual-MiniLM-L12-v2` (the old `.env` default) are exactly such a pair.

`src/embedding/registry.py` therefore checks the requested encoder against the registry entry for
the index directory being loaded, and refuses a mismatch. `scripts/benchmark_execution.py` and
`web/app.py` call it before retrieval. An index directory that is not in the registry is allowed
through unchecked, so ad-hoc indexes still work.

## Checking the registry against disk

```bash
venv/bin/python -m src.embedding.registry
```

Verifies every registered index's files, hashes, dimension and vector count. Loads no encoder and
downloads nothing; exits non-zero on any mismatch.

## Adding a configuration

1. Build it into a new directory: `python scripts/index_documents.py --input data/chunks_v1_c1024_o150 --output models/vectorstore_c003_...`
   (the script writes its own `manifest.json`).
2. Add an entry to `registry.json` with the encoder, dimension, chunk source and file hashes.
3. Never reuse a config ID after changing its effective settings — see `docs/BENCHMARK_RUN_REGISTER.md`.

## Known issue: `models/vectorstore` in historical run records

The five `c001` runs recorded their index path as `models/vectorstore`, the legacy default, because
that is where the index lived on the machine that ran them. That path no longer exists here; the
same bytes are now in `vectorstore_c001_c1024_o150`. `--repeat-from` on those runs will look for
the old path, so either point `VECTOR_STORE_PATH` at the c001 directory, or recreate
`models/vectorstore` as a link to it on the machine doing the repetition. The raw run records were
deliberately left unmodified.

## Known issue: line endings break recorded text-file hashes

Provenance records sha256 over raw file bytes. Some hashes were recorded on Windows with CRLF and
the committed blobs are LF, so they cannot match on a Linux/macOS checkout:

| Recorded hash of | Matches |
|---|---|
| `models/vectorstore_c002_c1024_o150/manifest.json` | CRLF only |
| `benchmarking/finalna_pitanja.json` | CRLF only |
| `src/retrieval/context.py` | CRLF only |
| `src/llm/prompts.py` | LF |

`index.faiss` and `metadatas.json` are unaffected and verify correctly everywhere. This is a
cross-machine verification problem, not a data problem, but `benchmark_provenance.py --verify-run`
will report failures for the CRLF-recorded files. Fixing it means agreeing on one canonical line
ending (a `.gitattributes` rule) and re-recording the affected hashes for all compared runs — do it
once, deliberately, before the paper's results are frozen.
