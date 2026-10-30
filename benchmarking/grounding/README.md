# Grounding / faithfulness evaluation

The current human-review workflow (no API calls) is documented in [human/README.md](human/README.md). Open `human/ocenjivac_grounding_A.html` for the primary 120-answer review and `human/ocenjivac_grounding_B.html` for the predefined independent 30-answer overlap. The automated pilots below are retained for audit and are not final validated paper results.

Run commands from the repository root using Python 3.10 or newer. The script uses only the standard library. It reads the existing judge model from `benchmarking/judge_profile.json` and `ANTHROPIC_API_KEY` from the environment or project `.env`.

The frozen sample contains the same 120 responses used for human annotation. Inputs are read from `benchmarking/runs/<source_run>/answers.jsonl`, including the exact context delivered to the generator. Reference answers and existing scores are not sent to the grounding judge.

## Current protocol v3 (2026-10-29)

Use a NEW run ID `grounding_v3`. Preserve both previous pilots; their averages are not directly comparable because criteria and successfully scored cases differ.

1. Extract unique atomic claims from the question and answer, without access to context or reference scores. Select IDs of exact answer segments instead of copying quotations.
2. In a separate call, verify the fixed claims against the entire supplied context and explicit question premises. Select context/question segment IDs. The program reconstructs exact source quotations, preserving Cyrillic, OCR and punctuation. No fuzzy matching or automatic OCR correction is used.
3. The verifier also audits claim extraction. Missing, duplicated or distorted claims flagged by the verifier produce a manual-review error, not a numeric score. This is the same judge model in two calls, not an independent human or second-model validation.
4. One bounded repair attempt per stage is allowed for invalid JSON or source IDs. All attempts are retained. Truncation and failed semantic extraction audits are not retried automatically. Invalid attempts never become zeros.

The input answer/context text and pilot order are unchanged. More explicit criteria distinguish earned from remaining credits, necessary from sufficient conditions, replaced from replacement text, conclusions from their explanations, and missing evidence from contradiction. These criteria are general, not per-question labels. They do not guarantee the judge will apply them correctly.

Each answer normally uses TWO API calls, including abstentions so their claim extraction can be audited. Optional repair or network retries add calls. Output budget remains 8192 tokens per call. The manifest pins both prompts, the script, inputs and repair settings. The pilot must be manually audited before extending the protocol to 120; passing offline tests establishes program behavior only, not judge accuracy. Remaining failures must be resolved and disclosed; do not silently report only easy successful cases.

With a successful run, `results.jsonl` retains extracted claims, final judgments, reconstructed quotes, source IDs, both stage response models and raw attempt paths. `attempts/` retains all requests and responses for auditing. `pilot_review.md` shows source context and final judgments. No prompt changes are made to the original RAG generator.

## Protocol v2 (pilot audit, 2026-10-29)

The initial v1 pilot revealed duplicate propositions, claim/label mismatches, inconsistent treatment of amendments, and an output truncated at 4096 tokens. Version 2 instructs the judge to count each unique proposition once, separate conclusions from their explanations, resolve explicit text replacements before assigning labels, distinguish absent evidence from contradictory evidence, and avoid reconstructing unreadable formulas by assumption. The output budget is now 8192 tokens. The validator rejects identical normalized claim texts even when answer excerpts differ; it cannot automatically detect paraphrases or verify entailment.

Keep `runs/grounding_v1` unchanged as the pilot audit trail. Run v2 under `grounding_v2`; do not combine v1 and v2 scores. The pilot order and all 120 source answers remain the same. The first 10 cases deliberately cover behaviors, configurations and difficult cases; their mean is not an estimate of the full sample's mean. These fixes do not establish semantic validity: manually review the new pilot before extending to 120. Accept valid low scores rather than changing criteria to increase the mean.

Validate all inputs without API calls or output writes:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_grounding.py --project-root . --run-id grounding_v3 --limit 10 --dry-run
```

Evaluate the pilot of 10 responses:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_grounding.py --project-root . --run-id grounding_v3 --limit 10
```

Inspect `benchmarking/grounding/runs/grounding_v3/pilot_review.md` and `summary.json`. Check that all material claims were extracted and their labels match the supplied context, including amendments and exceptions.

After reviewing the pilot, extend the same run to all 120 responses:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_grounding.py --project-root . --run-id grounding_v3 --limit 120
```

Successful pilot results are reused; only the remaining responses are sent. The run directory retains the manifest, frozen inputs and prompt, raw API attempts, result journal, CSV and summaries. Changes to the script, model or protocol require a new `--run-id`.

Faithfulness is the fraction of supported claims. Unsupported and contradicted claims are also reported separately. Responses without factual claims have no numeric faithfulness score; errors are not treated as zero. Review the counts of scored responses, responses without claims and errors when interpreting averages.

Offline verification (no real provider calls):

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_evaluate_grounding.py
```
