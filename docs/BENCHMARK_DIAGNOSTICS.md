# Diagnostic collection and fixed-judge scoring

**15 September update:** New collection records paths and hashes of its original benchmark and direct-retrieval index in `provenance.json`, without making per-run copies. `baseline_context8k` has received these references retrospectively without modifying raw answers. Scoring verifies the referenced files and joins missing reference criteria by exact ID/question/reference text. Its new scores therefore include criteria absent from historical scoring; rescore all compared runs under the same protocol. See [the run register](BENCHMARK_RUN_REGISTER.md) for the repetition command and provenance limits.

Answer collection and scoring remain separate. The collector saves raw responses; scoring can be repeated without generating those answers again. Neither changing scripts nor preparing a context/profile file sends requests to models.

## Diagnostic pilot

`benchmarking/diagnostic_contexts_pilot.json` contains two cases: REAL_033 (81 points and the grading scale) and REAL_043 (a second voluntary thesis-topic change). Evidence comes from readable, unchanged passages in the existing cleaned extraction snapshot. These cases reuse previously inspected evidence; this change does not constitute a new full PDF audit. The other 18 planned diagnostic cases are not yet prepared.

Each case identifies a benchmark question and source character offsets, not an expected answer embedded into the context. The collector checks the snapshot hash, source text hash, question hash, review status and passage boundaries before connecting to a model. Expected answers and scoring criteria are retained for evaluation but never passed to the answer generator.

Run ordinary retrieval on the pilot questions:

```powershell
python scripts/collect_benchmark_answers.py --execution ssh --model mistral:latest --diagnostic-contexts benchmarking/diagnostic_contexts_pilot.json --diagnostic-mode retrieved --top-k 5 --context-max-chars 8000 --num-ctx 8192 --run-id diagnostic_pilot_retrieved
```

Then run the same questions with curated evidence:

```powershell
python scripts/collect_benchmark_answers.py --execution ssh --model mistral:latest --diagnostic-contexts benchmarking/diagnostic_contexts_pilot.json --diagnostic-mode curated --top-k 5 --context-max-chars 8000 --num-ctx 8192 --run-id diagnostic_pilot_curated
```

Both commands use the same current generation settings from `.env` and the same system/user templates. Keep those settings unchanged between the paired runs. In curated mode `top_k` is not used: all specified passages are sent, retrieval and embedding initialization are bypassed, and oversized curated context fails before generation rather than being shortened. A reviewed `empty_context` control may deliberately supply no passages.

The existing API mode does not accept curated evidence. Use local or SSH execution. The `--model` argument selects the answer generator, not the judge.

The pilot selects only its two question IDs. A normal run without `--diagnostic-contexts` still uses the full benchmark. Each diagnostic mode must use a separate run ID, so diagnostic scores cannot silently inflate an ordinary 60-question result. Resume checks include the context-file hash and diagnostic mode. Adding cases or changing their passages requires a new run ID.

### Extending to 20 cases

Copy the pilot to a new context file. For each added case, verify the reference against the PDF and locate all necessary unchanged passages in the frozen cleaned text, including conditions and applicable amendments. Record:

- `question_id` and SHA-256 of the original UTF-8 question string.
- `review_status`: `ready` only after evidence verification.
- `passages`: source `document`, `start` (inclusive) and `end` (exclusive), counted as Python string characters, not bytes.
- A review note explaining evidence sufficiency or the intended insufficient-information control.

Do not repair OCR inside diagnostic prompts or put reviewer explanations in the passages. Pending cases are rejected, not silently skipped. `--limit` deliberately selects the first N cases; it does not certify the entire file. If the extraction snapshot changes, verify and re-anchor passages in a new context file.

Compare the two answers per question, not only averages. A wrong ordinary answer and correct curated answer suggest an evidence-selection/context-composition barrier; a wrong curated answer requires examining evidence sufficiency and generation behavior. A single pair does not prove causality. Curated results are diagnostic and must not be presented as ordinary retrieval performance.

## Existing scoring script and fixes

`scripts/score_benchmark_run.py` implements ROUGE, BLEU, BERTScore and LLM-as-a-judge. Its default is still ROUGE only; select `--metrics all` or a comma-separated list to enable more metrics.

The previous judge default followed `OLLAMA_MODEL` (currently `mistral:7b`), not necessarily the model used for SSH generation. It compared question, reference and candidate on a 0–5 scale, used temperature 0 and a 10-token output cap, and averaged requested samples. Its permissive parser could take an unrelated digit as the grade, and a failed judge call could become a zero. Those failures are now explicit metric errors, excluded from averages and composite scores. Raw judge responses, prompts and generation metadata are retained.

The new judge also sees required facts, disallowed claims and expected behavior when those fields were saved by the new collector. Historical answer files lack these extra fields and are scored against the reference alone; do not compare the two input protocols as identical. The judge checks agreement with reference criteria, not independent grounding against the PDFs. Human checks are still needed for incorrect references, ambiguity and unsupported claims not covered by the reference.

Other metric fixes:

- BERTScore now explicitly uses `bert-base-multilingual-cased` with Serbian language selection and a cached scorer, instead of English-default scoring. The encoder and BERTScore configuration hash are saved. This is a separate metric encoder, unrelated to the retrieval embedding model. Long texts can still exceed the metric encoder's token limit; inspect this limitation before treating long-answer scores as complete.
- ROUGE uses one Unicode-aware implementation without English stemming, rather than changing behavior according to installed packages. Cyrillic is retained. Latin/Cyrillic equivalents still differ lexically; ROUGE is supplementary, not a correctness verdict.
- BLEU uses the same Unicode tokenization without requiring a downloaded NLTK sentence tokenizer. It remains unsmoothed sentence BLEU-4, which can be zero for short correct answers. Library failures are errors, not zero scores.
- A composite is calculated only when all three required component scores are available. The existing weights are an exploratory aggregate, not validated accuracy percentages.

The output protocol is now `reference_metrics_v3`, reflecting the reserved Llama4 judge and Serbian rubric. Rescore all compared runs with the same judge profile and prompt rather than combining historical and new judge values. Scoring files receive unique timestamps, preserving earlier results. Summaries include per-metric valid/error counts; a run with missing metric values is not fully scored. Previously generated answers can be reused; changing the judge does not require regenerating them.

## Fixed judge profile

`benchmarking/judge_profile.json` is independent of `.env`'s answer-generator model:

| Setting | Value |
|---|---|
| Judge | `llama4:latest`, reserved outside the generator comparison |
| Required installed digest prefix | `bf31604e25c2`, from the user's server list |
| Execution | SSH, using existing SSH connection settings |
| Temperature / top_p | 0.0 / 0.9 |
| Seed | 42 |
| Output / context token limits | 32 / 16384 |
| Samples per answer | 1 |
| Prompt | Fixed Serbian reference-based rubric and Serbian input labels, identified by SHA-256 |

This is a proposed consistent grader, not an empirically validated best judge. Check its agreement with human labels before drawing paper conclusions. The generator shortlist is Mistral, Qwen3.5, Mistral-small, Mistral-large and Qwen3.6; Llama4 is used only for judging. Keeping the roles separate avoids direct self-grading but does not eliminate all preference or reasoning biases. Generator identities are not included in judge prompts. A fixed seed and temperature reduce uncontrolled changes but do not guarantee identical outputs. Switching the rubric to Serbian aligns instructions with the material; no measured accuracy gain from that language change is claimed.

Scoring verifies the installed model and digest prefix before any judge request and records the complete digest. It refuses a different model or a changed judge prompt instead of silently switching graders. If server weights change, choose a new profile and rescore all compared runs. `--judge-model` and `--judge-samples` are optional assertions and cannot silently override the profile. A separate `--judge-profile` explicitly selects a different evaluation protocol.

Scoring also checks recorded generator names and digests before connecting. A Llama4 generator or an alias carrying the judge digest is rejected. Old records without model provenance cannot be conclusively checked, so verify their origin manually. The detailed module comment in `src/evaluation/llm_judge.py` describes the rubric, its methodological background and its limits; it does not claim to replicate a published scoring scale.

For the pilot, start with judge and ROUGE:

```powershell
python scripts/score_benchmark_run.py --run-id diagnostic_pilot_curated --metrics rouge,llm_judge --judge-execution ssh
python scripts/score_benchmark_run.py --run-id diagnostic_pilot_retrieved --metrics rouge,llm_judge --judge-execution ssh
```

For all implemented metrics on an existing run:

```powershell
python scripts/score_benchmark_run.py --run-id baseline_context8k --metrics all --judge-execution ssh
```

BERTScore runs on the laptop CPU and may download its encoder on first use. Only judge requests use the SSH server. Availability, memory feasibility and actual scoring quality of the proposed large judge have not been tested by this implementation work.

To use an already established tunnel, select `--judge-execution local --judge-base-url http://127.0.0.1:11435`. Here `local` means a directly reachable endpoint; the fixed judge identity remains unchanged. A web API's answer-generator setting does not control this scorer.

## Verification and references

The old and new 1024/150 chunk files were compared after user-generated chunking: 205 versus 205, with identical decoded content and no missing or extra chunk files. The redundant per-file hash report was removed during cleanup; the conclusion is retained here.

Historical investigations live under each relevant run's `analysis/` folder, separate from the active diagnostic input file. `baselineNo1/analysis/` preserves the retrieval review (including the index-consistency check), reconstructed baseline contexts and two original curated-evidence responses. `baseline_context8k/analysis/context_budget_comparison.json` preserves the context-budget comparison. The old one-off scripts were removed; use the maintained scripts under `scripts/` for new collection and scoring. Reconstructed contexts are historical reconstructions, not directly logged prompts.

Offline regression checks:

```powershell
python -m unittest discover -s tests -p test_diagnostic_evaluation.py -v
```

- [BERTScore implementation and model/language selection](https://github.com/Tiiiger/bert_score)
- [ROUGE scorer and tokenizer interface](https://github.com/google-research/google-research/blob/master/rouge/rouge_scorer.py)
- [Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)
