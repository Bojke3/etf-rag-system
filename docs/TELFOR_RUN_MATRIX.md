# Run matrix: embedding x chunking x generator

Prepared 18 September 2026. Supersedes nothing: the ten existing `c001`/`c002` runs stay as a
completed embedding comparison at the 8000-character budget. This matrix is collected fresh so
every arm shares one protocol.

## Settings held constant

| Setting | Value | Why |
|---|---|---|
| Questions | `benchmarking/finalna_pitanja.json`, 60 | Same set for every arm |
| `top_k` | 5 | Both strategies deliver their five best passages |
| Context budget | 22000 characters | Nothing is truncated for either strategy (see below) |
| `num_ctx` | 16384 tokens | 22000 characters is ~9016 tokens at the measured 2.44 chars/token; plus prompt and 2048 output tokens that is ~11164, leaving ~5200 tokens of headroom |
| Temperature / top_p | 0.7 / 0.9 | Unchanged from the existing protocol |
| Prompt | `zero_shot`, existing system prompt | Unchanged |
| Repetitions | 5 per configuration | Supervisor's requirement; mean and sample standard deviation |

**Why 22000 and not 20000.** Measured over all 60 questions, hierarchical at `top_k=5` produces a
median of 18056 characters and a maximum of 20908. A 20000-character budget still truncates 11 of
the 60 questions; 21000 truncates none. 22000 is that bound with margin. Flat at `top_k=5` never
exceeds 5128 characters, so it is never truncated at any of these budgets.

The two strategies therefore deliver very different amounts of text at the same `top_k`. That is a
property of the strategy, not a flaw in the setup, but it must be reported in the results table.
If hierarchical wins, add a flat control at a higher `top_k` to separate "better segmentation"
from "more text". If flat wins, no control is needed: it won while receiving roughly a third as
much context.

## The eight configurations

Index IDs (`c001`-`c004`) are defined in `models/registry.json`. Run configuration IDs use a
separate `c1xx` range so the two are never confused.

| Run config | Embedding | Chunking | Generator | Index |
|---|---|---|---|---|
| `c101` | all-MiniLM-L6-v2 | flat | mistral:latest | `c001` |
| `c102` | all-MiniLM-L6-v2 | flat | *second model* | `c001` |
| `c103` | all-MiniLM-L6-v2 | hierarchical | mistral:latest | `c003` |
| `c104` | all-MiniLM-L6-v2 | hierarchical | *second model* | `c003` |
| `c105` | BAAI/bge-m3 | flat | mistral:latest | `c002` |
| `c106` | BAAI/bge-m3 | flat | *second model* | `c002` |
| `c107` | BAAI/bge-m3 | hierarchical | mistral:latest | `c004` |
| `c108` | BAAI/bge-m3 | hierarchical | *second model* | `c004` |

8 configurations x 5 repetitions = **40 runs**, 2400 generation requests. At the measured 4-6
minutes per run that is roughly 3-4 hours of generation, excluding retries.

Run IDs follow the register's convention: `dev_combined_c101_r01` through `..._r05`.

## Before starting

1. **Name the second generator and check it is installed.** The register's shortlist is Qwen3.5,
   Mistral-small, Mistral-large and Qwen3.6; `.env` currently names `qwen3.5:9b`, and there is one
   failed historical `qwen35_9b_topk5` trial. The collector records the model digest, so the model
   must be present on the server before collection starts.
2. **Confirm the server accepts `num_ctx=16384`.** This doubles the KV cache against the previous
   runs. Check memory before launching 40 runs.
3. **Record the server.** `server_hardware` is null in every existing provenance record; nothing in
   the repository says what machine generates the answers. The paper needs it.
4. **Validate the judge.** Collection is not the bottleneck; scoring is. The judge profile is
   explicitly unvalidated, and 40 runs produce 2400 answers to grade.

## Commands

Every setting that selects a configuration is passed explicitly, so no `.env` edit can mislabel a
run. Environment variables override `.env` values.

PowerShell, on the machine with server access:

```powershell
$env:EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
$env:VECTOR_STORE_PATH = "./models/vectorstore_c001_c1024_o150"
$env:CHUNK_STRATEGY = "flat_baseline"

foreach ($repetition in 1..5) {
    $runId = "dev_combined_c101_r{0:D2}" -f $repetition
    & .\.venv\Scripts\python.exe scripts/collect_benchmark_answers.py `
        --execution ssh --model mistral:latest `
        --top-k 5 --context-max-chars 22000 --num-ctx 16384 `
        --run-id $runId --label c101
    if ($LASTEXITCODE -ne 0) { throw "$runId did not complete. Fix the error and rerun to resume." }
}
```

bash equivalent:

```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2 \
VECTOR_STORE_PATH=./models/vectorstore_c001_c1024_o150 \
CHUNK_STRATEGY=flat_baseline \
python scripts/collect_benchmark_answers.py \
    --execution ssh --model mistral:latest \
    --top-k 5 --context-max-chars 22000 --num-ctx 16384 \
    --run-id dev_combined_c101_r01 --label c101
```

Per-configuration values to substitute:

| Run config | `EMBEDDING_MODEL` | `VECTOR_STORE_PATH` | `CHUNK_STRATEGY` | `--model` |
|---|---|---|---|---|
| `c101` | `sentence-transformers/all-MiniLM-L6-v2` | `./models/vectorstore_c001_c1024_o150` | `flat_baseline` | `mistral:latest` |
| `c102` | `sentence-transformers/all-MiniLM-L6-v2` | `./models/vectorstore_c001_c1024_o150` | `flat_baseline` | *second model* |
| `c103` | `sentence-transformers/all-MiniLM-L6-v2` | `./models/vectorstore_c003_hier` | `hierarchical` | `mistral:latest` |
| `c104` | `sentence-transformers/all-MiniLM-L6-v2` | `./models/vectorstore_c003_hier` | `hierarchical` | *second model* |
| `c105` | `BAAI/bge-m3` | `./models/vectorstore_c002_c1024_o150` | `flat_baseline` | `mistral:latest` |
| `c106` | `BAAI/bge-m3` | `./models/vectorstore_c002_c1024_o150` | `flat_baseline` | *second model* |
| `c107` | `BAAI/bge-m3` | `./models/vectorstore_c004_hier_bge` | `hierarchical` | `mistral:latest` |
| `c108` | `BAAI/bge-m3` | `./models/vectorstore_c004_hier_bge` | `hierarchical` | *second model* |

A mismatched encoder and index is refused before any generation request:
`src/embedding/registry.py` checks the pairing, and a hierarchical strategy will not fall back to a
flat index. Reusing a run ID resumes it rather than duplicating answers; use a new ID for a new
repetition.

## Verification after collection

```bash
venv/bin/python -m src.embedding.registry                     # indexes match the registry
venv/bin/python scripts/benchmark_provenance.py --verify-run benchmarking/runs/dev_combined_c101_r01
```

Check per run: 60 successful answers, `context_truncated` false for every question, and the
recorded `effective_strategy` matching the intended arm.
