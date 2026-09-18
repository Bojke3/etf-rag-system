# Vector indexes

One directory per benchmark configuration, named `vectorstore_<config-id>_c<chunk-size>_o<overlap>`.
`registry.json` is the authoritative binding of config ID to embedding model; this file is its
readable form.

| Config | Directory | Embedding model | Dim | Chunks | Provenance |
|---|---|---|---|---|---|
| `c001` | `vectorstore_c001_c1024_o150` | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 205, from `data/chunks_v1_c1024_o150` | retrospective audit |
| `c002` | `vectorstore_c002_c1024_o150` | `BAAI/bge-m3` | 1024 | 205, same chunk snapshot | build manifest |
| `c003` | `vectorstore_c003_hier` | `sentence-transformers/all-MiniLM-L6-v2` | 384 | 176 children embedded, 51 parents held out | build manifest |
| `c004` | `vectorstore_c004_hier_bge` | `BAAI/bge-m3` | 1024 | same 176 children, 51 parents | build manifest |

All indexes are `IndexFlatIP` over L2-normalised vectors. `c001` and `c002` are built from the
**same** 205 chunks — their `metadatas.json` hashes are identical — so only the encoder differs,
which is what makes `c001` vs `c002` a controlled embedding comparison. `c003` shares `c001`'s
encoder and is chunked from the same frozen extraction snapshot (`data/extracted_v1`), so
`c001` vs `c003` isolates chunking. `c004` completes the 2x2 — its `metadatas_hierarchical.json` and
`parents_hierarchical.json` are byte-identical to `c003`'s, so only the vectors differ. A strategy build names its files `index_<strategy>.faiss`;
the registry entry's `index_file` records which.

## Context budget is not comparable at equal top_k

Measured over the first 20 benchmark questions at an 8000-character context budget:

| Strategy | top_k | Retrieved | Reached the LLM | Passages delivered |
|---|---|---|---|---|
| `c001` flat | 5 | 5074 | 5074 (100%) | 5.0 |
| `c003` hierarchical | 5 | 18221 | 7992 (44%) | 2.7 |

Hierarchical parents average ~3400 characters, so five of them overflow the budget and the
context builder drops 2.1 of the 5 retrieved passages. Comparing the two at `top_k=5` therefore
measures truncation as much as chunking. Holding the **character budget** equal is what makes the
comparison fair — at 8000 characters that is roughly `top_k=8` for flat and `top_k=2` for
hierarchical. Record the delivered passage count either way; the collector saves it per question
in `diagnostics`.

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

## Historical run records point at the old path (handled)

The five `c001` runs recorded their index as `models/vectorstore`, the legacy default on the
machine that produced them. That directory is now `vectorstore_c001_c1024_o150`.
`benchmark_provenance.validate_inputs` resolves the move by searching the registry for a file
whose **hash equals what the run recorded** — so it identifies the same artifact rather than
guessing a substitute — and reports it under `input_match_exceptions` as `relocated`. Raw run
records are never rewritten. A file whose bytes differ still fails, as it should.

## Line endings in recorded hashes (handled)

Provenance hashes raw bytes. Some hashes were recorded on Windows from CRLF working copies while
the committed blobs are LF, so they could never match on a Linux/macOS checkout — which had
silently broken `--repeat-from` and `--verify-run` for **every** existing run on a Mac. Two
changes fix it:

- `.gitattributes` normalises text to LF everywhere, so new records cannot drift the same way.
- Verification accepts a match found only after line-ending repair and names those files in
  `input_match_exceptions` as `line_endings`, instead of either failing or hiding the difference.

Affected today: `benchmarking/finalna_pitanja.json` and
`models/vectorstore_c002_c1024_o150/manifest.json`. `index.faiss` and `metadatas.json` match
exactly and are unaffected.
