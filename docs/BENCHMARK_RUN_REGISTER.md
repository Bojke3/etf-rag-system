# Benchmark run convention and register

Updated: 15 September 2026. Collection status below is a local-file audit on this date, not a live monitor.

## Current research direction

The priority is benchmarking RAG configurations for Serbian-language faculty documents, currently student regulations, to obtain TELFOR paper results. The web interface is an early testing aid and is outside the current priority.

Collect and preserve outputs for each parameter family, then validate and apply the same evaluation protocol to that whole family before selecting the next configurations. Metric implementation can follow collection; correct question/reference data and complete raw records should be checked before expensive batches. Preserve failures and negative results as well as improvements.

The supervisor requests **five complete repetitions per compared configuration**, reporting mean and sample standard deviation. This replaces the earlier three-repeat proposal. The earlier workload estimate is consequently out of date. Five judge samples of one answer do not constitute five generation repetitions.

## Run names

Use `<split>_<phase>_<config-id>_r<NN>`:

- Split: `dev`, `test`, or `diag`.
- Phase: `base`, `emb`, `chunk`, `depth`, `llm`, or `combined`; diagnostic phases may be `retrieved` and `curated`.
- Config ID: stable identifier, such as `c001`; each distinct effective configuration gets a new ID.
- Repetition: `r01` through `r05`.

Examples: `dev_base_c001_r02`, `dev_emb_c002_r01`, `dev_chunk_c003_r01`, `diag_curated_c001_r01`.

The name is a readable label. `run_config.json` and the configuration register define what actually ran. Never reuse a config ID after changing its effective settings. If the same configuration appears in two phases, record reuse explicitly rather than counting one output twice as independent repetition.

Existing directories retain their original names and internal provenance. A logical alias in this register supplies the new convention without breaking historical score/analysis references. An alias is not an additional run.

## Configuration c001: existing baseline candidate

Source: `benchmarking/runs/baseline_context8k/run_config.json`.

| Setting | Value |
|---|---|
| Dataset | `benchmarking/finalna_pitanja.json`, 60 development questions |
| Dataset SHA-256 | `a88e35cb6d7b1b883065dfaebd48cc5883f1caba703b068257de5cca8131e78d` |
| Embedding | `sentence-transformers/all-MiniLM-L6-v2`, CPU |
| Existing index directory | `models/vectorstore_c001_c1024_o150` (renamed 18 September 2026; the five c001 runs recorded it under its former path `models/vectorstore`, and those records were left unmodified) |
| Existing chunks | Flat, 1024 characters, overlap 150 |
| Retrieval | top-k 5, threshold 0.0 |
| Generator | `mistral:latest`, SSH |
| Generator digest | `6577803aa9a036369e481d648a2baebb381ebc6e897f2bb9a766a2aa7bfbc1cf` |
| Prompt | Existing system prompt and `zero_shot` |
| Prompt-file SHA-256 | `e54745269cf4e4a759a39c1f5d6dd554469fe8a18a4b1b79fd236f320f1048c0` |
| Temperature / top-p | 0.7 / 0.9 |
| Output limit / timeout | 2048 tokens / 900 seconds |
| Retrieved context / model window | 8000 characters / 8192 tokens |
| Thinking / seed | Neither explicitly set in the recorded generation options |

Do not change temperature to 0.0, increase context limits, switch embeddings, or rebuild with OCR cleanup while calling new outputs repetitions of c001. Such experiments remain useful but get a different configuration ID.

Before counting this historical run and new requests as one five-repeat series, check current installed generator digest and effective inputs/settings. Local index and metadata hashes match the preserved historical audit:

- Index: `b3e799a872701027e13a189297222a94500f15b02504d5dd41316d7890449708`.
- Metadata: `5e1c9dba1570a0d5d7e81cc174c5a45502837cca7a27f3baa0a2595fdbd97a65`.

These hashes were checked retrospectively; c001's original run config did not record them. `provenance.json` now records paths to the original questions, FAISS index and metadata, with hashes. Dataset and index versions are stored once at their own locations; new versions use new files/directories. No copies are created inside runs. All 60 saved contexts and system/user prompts were verified against current processing and source text. Original answers, timing, run configuration and prior analyses were left intact. The repetition command checks current retrieval for all questions and the installed generator digest before generation. Historical encoder revision/runtime and server hardware remain unknown. Disclose historical versus new execution dates when interpreting timings; the preflight warms the local encoder, so historical retrieval latency is not a strictly matched cold/warm comparison.

## Baseline repetition register

| Logical run | Physical directory | Collection | Evaluation / compatibility |
|---|---|---|---|
| `dev_base_c001_r01` | `baseline_context8k` | 60/60 returned successfully | Original input paths recorded; all 60 fresh retrieval results and saved prompts verified locally; server digest checked when repetitions start; final scoring pending |
| `dev_base_c001_r02` | Not created | Planned, 0/60 | Pending |
| `dev_base_c001_r03` | Not created | Planned, 0/60 | Pending |
| `dev_base_c001_r04` | Not created | Planned, 0/60 | Pending |
| `dev_base_c001_r05` | Not created | Planned, 0/60 | Pending |

If r01 is compatible, four additional full repetitions require 240 generation requests, excluding retries. A successful request means an answer was returned, not that it is correct or complete; c001's historical analysis flags REAL_002 as hitting the output limit.

The local verification passed on 15 September and is saved in `local_retrieval_verification.json`: 205 vectors, dimension 384, loaded encoder revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, native sequence limit 256. This revision was observed during the retrospective check; it is not falsely attributed to the original collection date. No generator requests were made by that check.

## Other existing runs

| Directory | Collected questions | Role / missing work |
|---|---:|---|
| `baselineNo1` | 60 successful | Historical 2000-character context; not a c001 repetition; no directly saved full diagnostics |
| `baseline_topk5` | 34 successful | Incomplete historical run; no directly saved full diagnostics |
| `2026-07-06_004328_baseline_topk3` | 0 | Empty historical collection |
| `qwen35_9b_topk5` | 1 error | Failed historical trial; not a completed model comparison |
| `diagnostic_pilot_retrieved` | 2 successful | Separate diagnostic pilot; existing ROUGE/judge scores need judge validation |
| `diagnostic_pilot_curated` | 2 successful | Separate curated-evidence pilot; existing ROUGE/judge scores need judge validation |

## Recommended experiment sequence

This sequence is a recommendation, not a claim that one factor matters most:

1. Complete the five matched baseline repetitions.
2. Compare embeddings on identical existing chunks, with separate indexes and fixed generator/prompt/settings. Current MiniLM is the reference; multilingual MiniLM is the simplest next candidate already supported by the generic wrapper. E5 requires its query/passage handling before testing. Preserve rankings as well as generated answers. Keep threshold fixed for a matched comparison and report filtering; a no-filter comparison is a separate protocol, not an unrecorded change to c001.
3. Evaluate the whole embedding family, retain promising candidates, and compare chunk sizes/boundaries/overlap using one frozen text snapshot. Keep OCR/preprocessing fixed. The local/SSH collector and snapshot chunker need strategy integration before hierarchical comparisons.
4. Cross promising embeddings with promising chunkers, then compare retrieval depth. A sequential winner need not remain the winner after another component changes.
5. Compare LLMs on the same saved contexts. General replay of retrieved-run contexts still needs implementation; curated pilot replay alone does not provide it.
6. Freeze finalists and evaluate on new held-out questions, separately from the development set used to select parameters.

When later chunking/depth configurations exceed c001's context limits, establish a new common-budget reference before comparing them. Do not silently truncate one strategy more than another. The initial reference series remains useful historical evidence.

## Raw records and status rules

The current direct local/SSH collector saves question IDs/text, expected and actual answers, reference criteria, sources, timings, status/errors, exact context and prompts, chunk inclusion diagnostics, and available generation token/count metadata. Configuration includes requested model names, generator digest, generation settings and dataset/prompt hashes. Scoring writes separate timestamped files.

New collections record the original benchmark, FAISS index, metadata and optional indexing manifest paths and hashes, without copying their contents. Paths inside the repository are relative to the project root; external files use absolute paths. `provenance.json` also records client package/runtime versions, git revision and hashes of source/script files (including uncommitted changes). The loaded encoder revision is recorded when exposed by the library; unknown values remain null. Index dimension/count/type and encoder sequence limit are recorded. The legacy index has no original extraction/encoder build manifest, so these historical facts cannot be recovered by relabeling current settings. Server hardware/runtime still needs separate recording. Old API collections have less detail than current direct collections.

Scoring fills missing historical reference criteria from the referenced benchmark using an exact ID/question/reference-text match and verifies its hash. It does not rewrite original answers. Scoring output records `reference_benchmark_sha256`. Rescore compared runs together under this same input protocol; retain earlier score files.

## Running the remaining baseline repetitions

From the repository root in PowerShell:

```powershell
foreach ($repetition in 2..5) {
    $runId = "dev_base_c001_r{0:D2}" -f $repetition
    & .\.venv\Scripts\python.exe scripts/collect_benchmark_answers.py --repeat-from benchmarking/runs/baseline_context8k --run-id $runId --label $runId
    if ($LASTEXITCODE -ne 0) {
        throw "Run $runId did not complete successfully. Resolve the error and rerun this block to resume."
    }
}
```

`--repeat-from` uses the original dataset/index paths recorded by the reference run and restores its encoder, retrieval, model, prompt, temperature, output/context limits and timeout. These replace current parameter defaults/CLI overrides; SSH connection settings still come from `.env`. It verifies generator digest and identical retrieved passages/prompts for all 60 questions before making the first generation request. Each run records input paths and hashes only. The block runs sequentially and stops on failure; repeating it resumes completed/partial runs instead of generating duplicate successful answers. No generation was launched when preparing this command.

Optional local-only verification, with cached weights and no downloads or LLM requests:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_provenance.py --verify-run benchmarking/runs/baseline_context8k
```

Embedding similarity scoring can be added later using saved reference/candidate text and a fixed evaluation encoder. The evaluation encoder need not be the retrieval encoder; embedding every answer now is unnecessary.

Track collection and evaluation separately:

- Collection: `planned`, `running`, `partial`, `collected`, `failed`.
- Evaluation: `pending`, `provisional`, `validated`.
- Record expected/collected/success/error counts, artifact path, changed factor, parent/reference config ID, metric version and any limitation.

One run ID supports resumption, not another independent repetition. Keep appended attempts; summaries use the latest attempt per question. Inspect failed/truncated outputs rather than counting missing values as correct answers or silently excluding them.

For each configuration, calculate a dataset metric separately in each of five repetitions, then report its mean and sample standard deviation (denominator n-1). The 60 questions repeated five times remain 60 unique questions. Repeated deterministic retrieval over identical inputs may have zero quality variance; time repeated retrieval separately where latency is of interest. Keep warm and model-load timings distinct where available.

## Paper and meeting notes

Working scope: optimization of RAG for Serbian-language faculty documentation, evaluated on student regulations. The final title and selected comparisons should follow the supported findings; retain every collected configuration, including negative results.

Supervisor guidance: IEEE conference A4 template in LaTeX/Overleaf, approximately 3.5-4 pages total; abstract and keywords; introduction covering problem, motivation and key contributions with references; related work with most literature citations (maximum 1.5 pages); methodology; results and discussion; limitations; conclusion; references. Bold the best values in result tables. The two students precede professor Misic in the author list; their internal order remains unspecified. Write the final abstract after measured results are available.

The four files in `AI/sessions/` are historical context/handoff and decision records, not the current complete experimental protocol. Their stale configuration names and execution instructions should not override inspected code or the present study decisions.
