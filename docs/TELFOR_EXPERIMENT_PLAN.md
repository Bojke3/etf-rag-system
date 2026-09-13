# TELFOR Experiment Plan

**Version:** proposed protocol, 13 September 2026.  
**Language:** paper and research documentation in English; corpus, questions and answers in Serbian.  
**Status:** planning only. This document does not launch experiments or change `.env`.

## 1. Scope and decision sequence

Study four main factors: embedding model, chunking, retrieval depth, and generation model. Keep OCR output and preprocessing fixed. Additional document/version information in the LLM context is an optional final experiment, after the main study.

Run inexpensive retrieval experiments first. Select provisional candidates at checkpoints, then evaluate their downstream answers. Preserve an accuracy candidate and an efficiency candidate; add a balanced candidate only if it offers a distinct, useful trade-off.

Do not permanently lock the first winning parameter. Explicitly cross the shortlisted embedding models with shortlisted chunking configurations before finalizing retrieval. A sequential search identifies good configurations within the tested space, not a global optimum.

## 2. Preparation: data and an evaluation minimum

### Datasets

| Set | Proposed size | Purpose |
|---|---:|---|
| Development | Existing 60 questions | Screening, error analysis and configuration selection |
| Diagnostic subset | 20 questions selected from development | Paired normal-context and curated-evidence probes |
| Held-out test | Target 50 new questions | Final comparison after configurations and selection rules are frozen |

Existing questions are development data because their answers have already influenced decisions. Do not re-label a subset of these inspected questions as an untouched test set. Keep close paraphrases and the same underlying scenarios together rather than splitting them between development and test.

For the 50 new questions, aim for coverage of direct rules, conditions/exceptions, calculations, multiple passages/amendments, and insufficient-information cases. Define one primary stratum per question and allow additional tags. Check references against the PDFs and disclose synthetic versus observed-user origins. Prefer a second reviewer for reference validation and a subset of answer labels.

### Freeze the text before re-chunking

Preserve the historical PDFs, index, chunks and runs. Create a versioned, per-document snapshot of extracted and normalized text for the main study. Every new chunking configuration must use that same snapshot.

The three-stage workflow is now implemented; see [the document pipeline guide](DATA_PIPELINE.md). `extract_documents.py` saves raw and cleaned text, `chunk_documents.py` reuses the cleaned snapshot, and `index_documents.py` vectorizes the chunks. Do not rerun PDF extraction independently for each chunk size. Extract once into a new snapshot and compare its 1024/150 chunks with the historical artifacts before selecting the study reference. Do not blindly concatenate overlapping historical chunks.

Keep existing transliteration and whitespace handling fixed, including their limitations. Do not repair OCR, formulas, spelling or substantive text selectively between configurations.

### Minimum evaluation before selecting winners

Full metric automation is not required to start collecting raw outputs. It is required to have consistent reference annotations and at least a manually usable scoring rubric before choosing winners.

| Measurement | Definition and use |
|---|---|
| Required-evidence coverage | For each question, fraction of required evidence units fully supported by the union of retrieved passages; average over questions requiring corpus evidence |
| All-evidence rate | Fraction of those questions for which all required evidence units, including binding conditions, are retrieved |
| Context retention | Whether retrieved evidence survives in the actual prompt; must show no application-level truncation in main experiments |
| Strict answer accuracy | Fraction of questions answered correctly and sufficiently, with no material unsupported claims or contradictions; expected partial answers and abstentions are scored according to their reference behavior |
| Partial correctness | Additional label for useful but incomplete answers; report separately from strict accuracy |
| Unsupported-claim rate | Fraction of responses containing at least one substantive unsupported claim |
| Insufficient-information behavior | Correct abstention, clarification or limited answer, reported on the applicable subset |
| Efficiency | Warm query latency, total response latency, actual input/output length, index size and build time; separate setup costs from query costs |

Anchor required evidence to stable source passages, page references and snapshot offsets where available, not only chunk IDs. An evidence unit may be covered jointly by adjacent chunks. Repeated copies count once. A matching PDF name alone is not evidence success. Empty-reference questions must not count as automatically successful retrieval cases.

For damaged or contradictory passages, flag the case and inspect it instead of scoring it solely by string overlap. Track whether reference evidence is intact in the frozen text at all. Report extraction-limited cases separately while retaining them in end-to-end results.

## 3. Fixed study settings

These are proposed settings for a **new controlled reference**, not settings already applied to the application.

| Setting | Proposed value or policy |
|---|---|
| Corpus/OCR | One frozen text snapshot; no OCR tuning |
| Question preprocessing | Existing behavior, frozen and versioned |
| Initial chunks | Fixed character windows, size 1,024, overlap 150 |
| Initial retrieval depth | `top_k = 5` |
| Retrieval backend | Existing exact cosine search; do not tune a similarity threshold in the main study |
| Threshold implementation | Disable score filtering for the study, or use a verified pass-through threshold such as -1 for normalized cosine scores; record it explicitly |
| Initial LLM | Server `mistral:latest`; verify and record its actual digest |
| Prompt | Existing system prompt and `zero_shot`, unchanged |
| Temperature | 0.0 for the controlled study; do not mix historical 0.7 runs into a causal comparison |
| `top_p` | 0.9, held fixed |
| Output budget | `num_predict = 2048`; record output-limit terminations as failures to complete, not clean successes |
| Application context cap | 20,000 characters, including separators, excluding prompt/question |
| Ollama token window | Initially request `num_ctx = 16384` for all tested LLMs; validate support and memory feasibility before freezing it |
| Seed | 42 where supported; record unsupported/ignored seed behavior. Adding seed support is a preparation task |
| Embedding execution | Same laptop CPU and fixed thread/batch policy across candidates |
| Generation execution | Same faculty server; no simultaneous competing study runs |

The largest planned input from retrieved text is at most `8 * 2048 + 7 * 2 = 16398` characters. The 20,000-character cap avoids application truncation without padding smaller contexts. A character cap is not a token guarantee. Preflight the actual complete inputs, model tokenization/template overhead and output allowance. If the token window is insufficient, increase the common window and repeat the controlled reference before comparisons; never silently shorten selected evidence.

Embedding token limits are a **separate** issue: the encoder may only encode a prefix of a long chunk even when the whole chunk later reaches the LLM. Log native sequence limits, tokenized lengths and truncation frequency. For the main embedding comparison, use documented native model behavior and describe the candidates as encoder configurations, not a perfectly isolated comparison of weights alone. Do not raise encoder limits without validating support and recording a new configuration.

Existing `baselineNo1` and `baseline_context8k` remain historical engineering comparisons. The proposed reference changes temperature, context capacity and potentially the extraction snapshot; do not attribute the difference from those historical runs to a single factor.

## 4. Phase 0 — readiness and diagnostic baseline

**Purpose:** establish reproducible inputs and a way to distinguish retrieval failures from generation failures.

1. Freeze data, reference annotations, evaluation rules and prompts.
2. Complete the missing tooling listed in Section 11.
3. Validate the planned model window and output allowance using a few development inputs, including the longest expected contexts.
4. Collect one new 60-question controlled reference using the initial configuration.
5. Run diagnostic D0 on the 20-question diagnostic subset with Mistral and curated evidence.

**Checkpoint C0:** inputs are auditable, all selected text is retained, model identities are known, and at least a manual evaluation is possible. Otherwise collect raw outputs only; do not advance by declaring a winner.

## 5. Phase 1 — embedding models

Keep chunks at 1,024 characters with 150 overlap and `top_k = 5`. No LLM calls are needed for the initial retrieval comparison.

| ID | Candidate | Purpose and implementation requirement |
|---|---|---|
| E0 | `sentence-transformers/all-MiniLM-L6-v2` | Historical embedding reference |
| E1 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Multilingual comparison; audit its native sequence limit |
| E2 | `intfloat/multilingual-e5-small` | Retrieval-oriented multilingual candidate; implement `query: ` and `passage: ` prefixes correctly |
| E3 — optional | `intfloat/multilingual-e5-base` | Add only if the core phase finishes on time and the extra CPU cost is acceptable |

The first three are the core proposal. Each model needs its own index. Apply E5 prefixes only to encoder inputs, not to the source text passed to the LLM. The current generic embedding wrapper does not implement that distinction. Follow the model's normalization and encoding instructions. Do not compare absolute cosine-score thresholds across models as if their score scales were calibrated.

Measure evidence coverage, all-evidence rate, warm question-embedding plus search latency, index size, build time and encoder truncation. Inspect questions where models disagree.

**Checkpoint C1:** retain two encoder candidates: the strongest by evidence quality and a competitive faster alternative. These are provisional retrieval candidates, not proven end-to-end winners. If the optional E3 is included and provides a distinct trade-off, a third may be retained, but the core count below assumes two.

## 6. Phase 2 — chunk size, boundaries and overlap

### Phase 2A: fixed-window size

Use the provisional quality encoder from C1 and `top_k = 5`.

| Size, characters | Overlap, characters | Interpretation |
|---:|---:|---|
| 512 | 150 | Short windows; inspect split conditions and relatively high redundancy |
| 1024 | 150 | Reference setting |
| 1536 | 150 | More surrounding text |
| 2048 | 150 | Long windows; inspect topic mixing and encoder truncation |

Absolute overlap stays fixed here to change only window size. Its relative percentage necessarily changes; report this and examine it separately in Phase 2C.

### Phase 2B: preserving boundaries

Repeat the same four sizes with a boundary-preserving splitter and overlap target 150. Compare each result with its matching fixed-window size from 2A.

Proposed splitter: prefer article/paragraph boundaries, then sentence boundaries for overlong blocks, with fixed-character fallback for blocks that still exceed the hard size cap. Preserve source text; do not insert version labels or rewrite OCR. Record actual lengths and actual overlap. Article splitting needs validation because line breaks and headings can be damaged by extraction.

**Checkpoint C2:** retain two distinct `(strategy, size)` candidates across the eight evaluated settings. Favor evidence quality and a useful difference in latency/context length. Do not select solely because one has the highest number of matching chunks.

### Phase 2C: overlap

For each retained candidate, test overlap targets of **0%, 10%, and 20% of its size**, rounded down to an integer number of characters. Also retain its already measured **150-character** result as a reference. Reuse identical configurations rather than running duplicates.

| Retained size | 0% overlap | 10% overlap | 20% overlap | Existing reference |
|---:|---:|---:|---:|---:|
| 512 | 0 | 51 | 102 | 150 |
| 1024 | 0 | 102 | 204 | 150 |
| 1536 | 0 | 153 | 307 | 150 |
| 2048 | 0 | 204 | 409 | 150 |

Only run the rows corresponding to the two retained strategy/size candidates, not every row.

For the boundary-preserving splitter, implement overlap as an explicit suffix budget before packing the next new content; preserve the hard size cap, ensure forward progress, and log actual overlap. Do not imply that boundary-preserving chunks must be completely independent articles.

**Checkpoint C3:** retain two full chunking configurations `(strategy, size, overlap)`. Review evidence lost at boundaries, duplicated evidence and encoder truncation before carrying them forward.

## 7. Phase 3 — embedding × chunking cross-check

Cross the **two retained encoders** with the **two retained chunking configurations** at `top_k = 5`. This is a four-cell comparison; reuse cells already evaluated.

This checkpoint explicitly tests whether the embedding ranking changes after re-chunking. If a discarded encoder was close to the shortlist or encoder truncation explains a reversal, allow one documented rescue comparison; label it adaptive development work.

**Checkpoint C4:** retain up to three complete retrieval configurations with useful quality/efficiency trade-offs. The decision concerns the pair of encoder and chunking settings, not an encoder selected in isolation.

## 8. Phase 4 — retrieval depth and downstream checkpoint

For each retained retrieval configuration, compare **`top_k = 1, 3, 5, 8`**. Keep the full selected text and preserve retrieval rank order.

For a fixed index and query, the top-1/3/5 results can be obtained from a saved top-8 ranking. Reuse this work for evidence evaluation. Measure latency separately if reporting per-`k` search timing; do not invent timings for sliced rankings.

Inspect both added evidence and added irrelevant/repeated text. More chunks can increase evidence coverage while making generation less accurate.

**Checkpoint C5a:** use retrieval metrics to shortlist up to three complete `(encoder, chunking, k)` configurations. Do not make the final `k` choice from retrieval coverage alone.

**Downstream checkpoint:** generate answers for all 60 development questions using Mistral and each shortlisted configuration, then score correctness, grounding and latency.

**Checkpoint C5b:** select two distinct saved-context configurations for the model comparison. One should favor quality and the other efficiency. If all configurations remain weak, carry forward the strongest candidates for diagnosis, but do not label them deployment-ready.

## 9. Phase 5 — generation models and diagnostic D1

Use the faculty-server tags previously supplied by the user; check availability and freeze model digests at execution time. A tag is not a permanent model identity.

| ID | Candidate | Role |
|---|---|---|
| L0 | `mistral:latest` | Existing generation reference |
| L1 | `qwen3.5:latest` | Different model family; verify the intended installed weights |
| L2 | `mistral-small:latest` | Larger Mistral candidate; validate server memory and common context-window support |
| L3 | `mistral-large:latest` | Large-model comparison requested by the user; installed artifact reported as 73 GB |
| L4 | `qwen3.6:latest` | Additional Qwen candidate from the installed list; installed artifact reported as 23 GB; freeze its actual identity |

For the main comparison, use **two saved-context configurations × five LLMs** on all 60 development questions: ten cells and 600 responses. The two Mistral cells from Phase 4 can be reused if every effective setting matches, leaving 480 additional calls. No retrieval should be rerun simply to change the LLM.

Reserve `llama4:latest` exclusively as the fixed judge, outside the generator comparison, following the user's decision to separate these roles. Keep `mistral-large:latest` in the generator comparison; replace the earlier Llama4 generator slot with `qwen3.6:latest`. This is a proposed allocation, not a claim that Llama4 is the most accurate Serbian judge. Verify the installed variant, memory feasibility and agreement with human labels before freezing the evaluation protocol. The judge receives no generator name in its prompt, and scoring rejects known judge/generator model or digest overlap.

The user's installed names identify candidates, but do not establish their exact architecture, quantization or runtime memory requirements. Before execution, record their digests and model metadata, check the available server memory, and verify actual GPU/CPU placement with the common context window. Installed file size is not a runtime memory estimate. Run models sequentially and report any offloading, since latency then reflects the deployed configuration as well as the model. If a candidate cannot run, document the feasibility result and revisit the execution setup rather than silently dropping it.

The central comparison is whether the larger deployments improve strict accuracy, reduce unsupported claims, and resolve rule/exception or multi-passage failures enough to justify their measured latency. Report paired per-question gains and regressions against L0 and L2. Do not assume that a larger model must perform better. Use curated-evidence results to separate improved evidence use from failures caused by missing evidence in normal contexts.

Keep the system/user prompt contents and generation limits fixed. Model-specific chat templates remain part of each model deployment and must be recorded. Where a model supports thinking mode, explicitly disable it for this primary comparison if supported; leave the option absent for models that do not support it. Verify the effective behavior rather than assuming it from the model family name.

Run diagnostic D1 using the same 20 curated inputs for all five models: 100 curated responses in total. Reuse D0's Mistral calls only when all settings and inputs match. These 20 cases remain diagnostic; assess overall quality on the full development set and frozen held-out evaluation.

**Checkpoint C6:** identify complete accuracy, speed and, if useful, balanced configurations using the rules in Section 12. Repeat selected complete configurations with independent requests, then freeze the finalists before held-out evaluation.

## 10. Diagnostic protocol: D0, intermediate inspection and D1

### Proposed diagnostic questions

Use the following provisional development IDs, subject to reference verification before freezing D0:

```text
REAL_001 REAL_003 REAL_009 REAL_011 REAL_012 REAL_018 REAL_028 REAL_030
REAL_033 REAL_036 REAL_037 REAL_043 REAL_044 REAL_047 REAL_053 REAL_055
REAL_056 REAL_057 REAL_058 REAL_060
```

The first 16 cover rules, thresholds, calculations, exceptions and multi-passage/version-sensitive cases. The final four test absent or only partially available information. This is an intentionally diagnostic selection, not a representative sample for an overall accuracy estimate.

### Constructing a curated input

1. Verify the question and expected answer against the PDF.
2. Select readable, unchanged passages from the frozen extracted text that jointly contain the necessary evidence. Include binding conditions, exceptions and amendment wording when required.
3. Store source coordinates and the exact curated context separately from the expected answer. Do not put the expected answer, scoring rubric or reviewer explanation into the prompt.
4. Keep the same system prompt, question preprocessing, user template and generation settings used by the normal run.
5. For questions with no answer in the corpus, supply an appropriate related passage or explicitly document an empty-context control. Do not create fictional evidence. For partial-answer questions, include the available general rule.

If OCR damage makes an evidence unit unreadable, mark the case extraction-limited. Do not silently repair it for an experiment described as retrieval-only isolation. Replace an unsuitable diagnostic question before freezing the set or report it separately.

### Interpretation

| Normal context | Curated context | Interpretation to investigate |
|---|---|---|
| Incorrect | Correct | Evidence selection or context composition was likely a barrier |
| Incorrect | Incorrect | Error remains with curated evidence; inspect completeness, rule application, prompt and generation behavior |
| Correct | Correct | Successful evidence retrieval and use in this case |
| Correct | Incorrect | Check curated evidence, helpful information removed, and generation variability |

Curated evidence is a diagnostic reference, not a guaranteed upper bound on accuracy. A single answer does not establish causality. At intermediate checkpoints, inspect disagreements on the same IDs without changing their references to favor a configuration.

## 11. Tooling readiness: available versus needed

| Capability | Current state | Action before dependent experiments |
|---|---|---|
| Local/SSH answer collection and explicit model selection | Available | Keep user-controlled execution; do not launch runs as part of planning |
| Character budget and Ollama token-window overrides | Available | Preflight the common study limits |
| Full source text, exact prompts/context, chunk usage and Ollama counts | Available for new direct runs | Preserve records and verify no omissions |
| Separate index output directories and embedding selection | Available, including input hashes and basic manifests | Extend provenance with the resolved encoder revision before the study |
| Frozen extraction snapshot and re-chunking without another OCR pass | Implemented as separate extraction and chunking scripts | Produce and review the new snapshot before Phase 2 |
| E5 query/passage input handling | Missing in current generic encoder wrapper | Implement and verify before testing E2/E3 |
| Encoder input-token/truncation logging | Missing | Add before interpreting size/model comparisons |
| Boundary-preserving chunker | Missing | Implement and inspect before Phase 2B |
| Retrieval-only batch collection and evidence scoring | Not yet a complete study workflow | Add collection and a manual/scored reference format before C1 |
| Replay curated source contexts across LLMs | Implemented in the collector with a two-case pilot | Review and freeze all 20 cases; arbitrary retrieval-run replay still needs a separate workflow |
| Seed support and explicit per-model thinking settings | Incomplete | Implement requested options and record support before the controlled reference |
| Human rubric, annotation table and profile selection | Not yet formalized | Freeze definitions before selecting winners |

Do not present planned flags, runners or metrics as already implemented. Creating this plan does not authorize automatic server runs or model downloads.

## 12. Candidate retention and final profiles

At each retrieval checkpoint, inspect evidence quality alongside latency and context length. Keep candidates that are not clearly worse on every relevant dimension. Preserve near-ties when the sample is too small to distinguish them confidently.

For the final development-set selection, use these **proposed operational rules**, frozen before viewing final results:

- **Accuracy:** highest strict answer accuracy; use unsupported-claim rate and then latency to resolve ties.
- **Speed:** lowest median warm end-to-end latency among configurations within **5 percentage points** of the best strict accuracy and with no higher observed unsupported-claim rate than the accuracy candidate.
- **Balanced:** lowest median latency among configurations within **2 percentage points** of the best strict accuracy and with no higher observed unsupported-claim rate; keep it only if distinct from the other two.

These are selection tolerances, not statistical-equivalence claims. On 60 development questions, small percentage differences correspond to only a few answers. Report paired counts and uncertainty rather than declaring tiny gaps decisive. Review insufficient-information behavior before retaining a candidate whose aggregate score hides a serious regression.

If no distinct candidate meets a profile's rule, leave that profile empty or let one configuration serve multiple goals. A relative winner in a weak pool is not evidence that an application is reliable enough for deployment.

Repeat each finalist for **three total development runs**, with the same fixed seed where supported. These are repeated measurements on the same questions, not three times as many independent questions. Then freeze settings and evaluate each finalist on the **50 held-out questions**, also targeting three repetitions if resources permit. Do not select new settings or rename winners using held-out results.

Report median and p95 warm latency, separate cold/model-load latency, and record server contention and GPU/CPU offloading. Alternate the order of model/configuration blocks across repetitions to reduce time-of-day and load-order bias. Warm up each model using a separate non-benchmark input; do not warm it with the exact scored question.

## 13. Run records and decision checkpoints

Suggested ID format:

```text
p04_dev_e2_boundary_c1024_o102_k5_l0_r1
p05_dev_e2_boundary_c1024_o102_k5_l2_r1
d1_curated_dev_l2_r1
p06_test_accuracy_r1
```

IDs are labels, not substitutes for complete saved configuration. Store model digests, encoder revisions, code revision, snapshot/chunk/index hashes, exact prompts and contexts, requested/effective options, timing and raw responses. Keep evaluation outputs separate so that metric updates do not require regenerating answers.

After C1–C6, record:

1. Hypothesis and configurations compared.
2. Dataset and metric versions.
3. Evidence, accuracy/grounding when available, and efficiency results.
4. Retained and rejected candidates, including near-ties.
5. Representative improvements, regressions and remaining failure causes.
6. The next test and the uncertainty it is intended to resolve.

When metrics are incomplete, mark a checkpoint as **pending evaluation**. Raw data collection may continue, but selections remain provisional. Re-score all affected runs whenever reference or scoring corrections are introduced.

## 14. Workload estimate and stopping rules

For the core plan, reusing identical settings gives approximately:

| Work | Estimated unique settings or generation calls |
|---|---:|
| Phase 1, three encoders | 3 retrieval settings |
| Phase 2A/B, eight size/strategy cells | At most 7 additional retrieval settings |
| Phase 2C, two candidates and overlap alternatives | At most 6 additional settings |
| Phase 3, two encoders × two chunkers | At most 2 additional settings |
| Phase 4, up to three candidates × four `k` values | At most 9 additional settings; some reuse the same ranking |
| Retrieval total | About 27 evaluated settings on 60 development questions, excluding optional rescues |
| Controlled reference | 60 LLM calls |
| Phase 4 downstream checkpoint | Up to 180 calls |
| Phase 5 additional models on two contexts | 480 calls; reuse matching Mistral cells |
| D0/D1 curated contexts | 100 calls total across five models, with matching Mistral results reused |
| Development finalists, two additional repetitions | Up to 360 calls for three finalists |
| Held-out evaluation, three finalists × 50 × three runs | Up to 450 calls |
| Planned generation upper estimate | About 1,630 calls, before failures/retries and optional work |

This is a workload estimate, not a runtime guarantee. Human evaluation and reference checking may dominate the schedule. If time is short, first drop E3, rescue comparisons and the optional metadata experiment; then reduce the number of finalists. Preserve the test-set separation, common-input comparisons and evidence verification.

Stop adding configurations when they do not address a documented unresolved question. Keep negative results rather than searching until the desired narrative appears.

## 15. Optional final experiment and calendar

Only after the core results and first paper draft are complete, compare the chosen system with and without source labels containing document name, article and version/date when verified. Keep selected source passages and model fixed. The additional labels intentionally change the prompt; log their text and length. Internal provenance required for evaluation is not the same as adding these labels to the LLM context.

Use development data for this optional experiment. If the held-out set has already been examined, report subsequent work as exploratory; do not claim another untouched final test on the same questions.

Proposed schedule from 13 September, assuming the previously checked 4 October submission deadline remains in effect:

| Dates | Main objective | Writing output |
|---|---|---|
| Sep 13–15 | Preparation, reference validation, tooling and D0 | Dataset and protocol draft |
| Sep 16–18 | Embedding and size/strategy screening | Retrieval tables and methods |
| Sep 19–21 | Overlap and encoder/chunker cross-check | Error analysis and shortlist rationale |
| Sep 22–24 | `top_k`, downstream checkpoint and model comparison/D1 | Main development results |
| Sep 25–28 | Repetitions, freeze finalists, held-out evaluation | Final tables and figures |
| Sep 29–Oct 2 | Analysis and supervisor review; optional labels only if feasible | Complete paper and revisions |
| Oct 3–4 | Submission buffer and final checks | Submission-ready paper |

Recheck the official deadline before submission. The existing research plan provides the broader paper structure; this document specifies the proposed operational experiments.

## References for implementation and methodology

- [Multilingual MiniLM model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2) — includes its published architecture and native sequence-length setting.
- [Multilingual E5 small model card](https://huggingface.co/intfloat/multilingual-e5-small) and [E5 base model card](https://huggingface.co/intfloat/multilingual-e5-base) — verify query/passage prefixes, normalization and input limits before implementation.
- [Searching for Best Practices in Retrieval-Augmented Generation](https://aclanthology.org/2024.emnlp-main.981/) — prior work on RAG configurations and efficiency trade-offs.
- [RAGChecker](https://arxiv.org/abs/2408.08067) — component-level diagnostic evaluation.
- [TELFOR author information](https://www.telfor.rs/sr/autori/) — recheck current submission requirements.
