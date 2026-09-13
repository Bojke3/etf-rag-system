# TELFOR Research and Writing Plan

**Operational update, 13 September 2026:** See [TELFOR Experiment Plan](TELFOR_EXPERIMENT_PLAN.md) for the proposed candidate values, phase order, checkpoints, diagnostic tests, workload and dated schedule. Its detailed protocol supersedes the preliminary experiment examples below.

## Purpose and working title

**Working title:** *Effects of Context Quality and Language Model Selection on a Serbian-Language RAG System for University Regulations*

The paper will be written in English. The source documents, benchmark questions, and generated answers concern university regulations in Serbian.

The objective is to evaluate how retrieval, context construction, and language model selection affect answer quality, explain the observed changes, and identify the best configuration **among those evaluated on this dataset**. The study will not claim universally optimal RAG parameters.

## Current position: a functional proof of concept

The project already implements the complete workflow: PDF processing, text chunking, embedding, retrieval, context construction, and answer generation using a local or SSH-accessible LLM. Some end-to-end examples retrieve an appropriate rule and produce a correct answer.

This supports a claim of technical feasibility. It does not yet establish reliable performance on realistic student questions. Current evidence identifies several distinct limitations:

- Relevant evidence can be absent from the retrieved results even when it exists in the index.
- The initial 2,000-character context limit removed evidence that retrieval had already found. Context limits are now configurable; the subsequent 8,000-character run retained all five selected chunks for all 60 questions. This fixes context delivery, but does not establish aggregate answer accuracy.
- Extracted text contains some damaged formulas and OCR errors.
- Mistral sometimes misapplies a rule even when the relevant evidence is present.

Two curated-evidence probes illustrate this distinction: supplying the grading scale enabled a correct answer for 81 points, while supplying the rule allowing only one thesis-topic change still produced an incorrect answer. These are diagnostic examples, not an aggregate performance estimate.

Existing implementation defects must be described transparently. Fixing context truncation is an engineering correction; the research contribution comes from controlled measurements, error attribution, and reproducible findings beyond that correction.

## Proposed research questions

1. **Retrieval:** How do embedding model selection, chunking, and retrieval depth affect the availability of evidence required to answer Serbian-language regulatory questions?
2. **Context construction:** How much retrieved evidence reaches the LLM, and how does preserving complete relevant passages affect answer quality?
3. **Generation:** How do selected LLMs compare when given identical contexts, including manually verified sufficient evidence?
4. **Optional source-label analysis:** Does adding verified document, article and version information to the selected context improve rule applicability and answer quality?

Keep the first three questions as the main scope. Keep OCR output fixed as a realistic corpus limitation and label extraction-related failures. Leave additional source labels until the core experiments and first paper draft are complete.

## Dataset and reference answers

Use the existing 60 benchmark questions as the development set because their outcomes have already informed debugging and design decisions.

Prepare approximately 40–60 additional, independently checked questions as a held-out test set. Freeze this set before final evaluation and do not use its results to choose configurations. Keep close paraphrases or variations of the same scenario together when separating development and test questions.

Include representative cases involving:

- Direct factual rules and numerical thresholds.
- Conditions, exceptions, deadlines, and calculations.
- Evidence distributed across multiple passages.
- Amendments, document versions, and cohort-dependent provisions.
- Questions requiring clarification, partial answers, or abstention.

For each question, verify the expected answer against the PDFs and record the source document, page, relevant passage, required facts, and unsupported claims to avoid. Identify reference evidence independently of generated chunk IDs so that changing chunk boundaries does not invalidate the evaluation labels.

Clearly disclose whether questions are synthetic, human-authored, or collected from users. Synthetic realistic questions must not be described as observed user queries. Where possible, have a second reviewer check reference answers, version applicability, and ambiguous cases.

## Experimental program

### Phase A: reproducible baseline and instrumentation

- Preserve the existing `baselineNo1` run as the initial prototype result.
- Record the implementation corrections separately and establish a clearly documented baseline for subsequent comparisons.
- Save full retrieved chunks, their ranks and scores, source metadata, the exact context, the complete prompts, and model responses.
- Record model digests, embedding model versions, generation parameters, context limits, index and dataset hashes, and the code revision.
- Verify embedding/index consistency whenever the embedding configuration changes. Rebuild the index for each different embedding model.
- Keep the system prompt and prompt strategy fixed during the main retrieval and model comparisons.

### Phase B: retrieval experiments

Screen a modest set of configurations on the development questions. A practical starting scope is two embedding models, two chunking approaches, and several retrieval depths, such as `top_k` values of 3, 5, and 8. Expand only when the results motivate a specific question.

Compare the existing embedding configuration with a multilingual alternative. Compare fixed-length chunks with an approach that better preserves article or paragraph boundaries. Keep the source corpus fixed while studying these factors.

Measure evidence availability before running generation. Inspect misses to distinguish extraction damage, poor ranking, split evidence, and confusion between document versions. Aim for roughly 20–40 inexpensive retrieval configurations if time permits, rather than an exhaustive search.

### Phase C: context experiments

Reuse the same saved retrieval results and the same LLM while changing context construction. Compare the original context limit with a budget that admits all selected passages, and evaluate preserving complete rules rather than cutting them mid-sentence.

Track evidence at two separate stages:

1. Evidence present in retrieved results.
2. Evidence actually included in the prompt.

Avoid interpreting a higher `top_k` as a larger effective context unless the saved prompt confirms that the additional passages were included. When studying retrieval depth, control the context budget or explicitly report their interaction.

### Phase D: model comparison and curated-evidence probes

Compare five available LLMs on identical saved contexts: `mistral:latest`, `qwen3.5:latest`, `mistral-small:latest`, `mistral-large:latest`, and `qwen3.6:latest`. Reserve `llama4:latest` exclusively as the fixed judge with a Serbian rubric, subject to verification against human labels. The larger generation models are included to measure whether they improve evidence use and answer quality enough to justify their latency. Verify actual model identities and server feasibility, and keep generation settings documented and fixed across the main comparison where supported.

On a selected diagnostic subset, supply manually verified, complete source passages directly. These curated-evidence probes estimate how models behave when retrieval failures are removed. Keep their results separate from normal end-to-end performance.

Use two selected saved-context configurations per model, giving ten model-comparison cells. Repeat a small number of finalist configurations, for example three runs, to assess generation variability. Record seeds where supported and do not assume that a low temperature guarantees identical output.

### Optional Phase E: source and version labels

Compare the chosen system with and without verified document, article and version labels in its context. Preserve the selected passages and generation model; record the additional label text and resulting input length.

Run this optional comparison on development data only if time remains after the core results and first paper draft. Keep OCR and preprocessing unchanged. If held-out results have already been inspected, describe subsequent experiments as exploratory.

## Metrics and answer assessment

| Layer | Main measurements | Interpretation |
|---|---|---|
| Retrieval | Required-evidence coverage at `k`; proportion of questions with all necessary evidence retrieved | Whether retrieval supplies the facts needed for an answer |
| Context | Evidence retained in the actual prompt; context size | Whether context construction preserves retrieved evidence |
| Answer | Correct, partially correct, or incorrect; required-fact coverage | Whether the response answers the question and preserves relevant conditions |
| Grounding | Unsupported claims, contradictions, invented references | Whether claims are justified by the supplied material |
| Unanswerable questions | Appropriate abstention, clarification, or partial response | Whether the system handles insufficient information correctly |
| Efficiency | Retrieval and generation time, total latency, token counts when available | The quality–latency trade-off under the recorded hardware conditions |

Define the scoring rubric before final evaluation. Distinguish an incorrect factual claim from a missing detail, and evaluate whether omitted information is actually required by the question. A match to the expected document name alone is not evidence-level retrieval success.

Use human review for final comparisons. If an LLM judge assists with screening, validate its decisions against human assessments rather than treating them as ground truth. Where feasible, hide configuration names from reviewers and have a second reviewer independently assess a subset and resolve disagreements.

Report sample counts and uncertainty, particularly for small differences between configurations. Compare systems on the same questions. Lexical similarity metrics may be supplementary, but they should not be the main evidence of factual correctness.

## Collecting and organizing results

Keep each configuration in a separate run directory and preserve raw outputs. Derived evaluations should reference the original run and question IDs without overwriting responses.

For each run, retain:

- An experiment ID, hypothesis, and description of the changed factors.
- Dataset split, document/index versions, and configuration metadata.
- Per-question retrieved evidence and exact model input.
- Raw answer, completion status, timing, and available token counts.
- Evaluation labels, reviewer notes, and error categories.

Maintain one comparison table with configuration, evidence coverage, answer quality, unsupported-claim rate, abstention behavior, and latency. Maintain a short experiment log explaining why each follow-up was selected, including changes that did not improve performance.

Useful error categories are retrieval miss, context loss, extraction damage, version confusion, incorrect rule application, calculation error, unsupported claim, and inappropriate abstention. Allow multiple categories when a case has more than one contributing factor.

Freeze finalist configurations before evaluating the held-out test set. If test results later motivate changes, report that analysis as exploratory and do not continue presenting the same set as untouched final evaluation.

## Schedule and writing milestones

Planning date: **11 September 2026**. The published TELFOR 2026 full-paper deadline checked on that date is **4 October 2026**, leaving approximately 23 days. Recheck official notices before submission.

| Period | Research and results | Writing milestone |
|---|---|---|
| Days 1–5 | Verify references, prepare and freeze the test set, instrument full-context logging, establish baselines, review related work | Draft the introduction, research questions, and dataset/method description |
| Days 6–11 | Screen retrieval and context configurations; inspect errors and select candidates | Draft the experimental setup and prepare provisional tables |
| Days 12–17 | Compare LLMs, run curated-evidence probes, repeat finalists; consider source labels only after core work is complete | Draft results and discussion with explicit links between evidence and claims |
| Days 18–23 | Run final held-out evaluation, check labels and uncertainty, finalize figures, review with the supervisor | Complete the abstract and conclusion, revise the full paper, check formatting and submit |

Server access makes multiple iterations feasible, but annotation, verification, and interpretation are likely to require more attention than simply launching runs. If time becomes constrained, reduce the number of configurations before reducing reference quality or final evaluation rigor.

## Proposed paper structure

TELFOR currently limits regular and student papers to four A4 pages using the IEEE conference format. Keep the scope narrow enough to explain within that space.

1. **Abstract and introduction:** State the practical problem, research questions, and measured contribution. Write the final abstract after results are available.
2. **Related work:** Position the study relative to existing RAG optimization and diagnostic evaluation research.
3. **System, dataset, and methodology:** Describe the Serbian corpus, question construction, splits, reference verification, configurations, and metrics.
4. **Results and discussion:** Present a compact configuration comparison, component-level error analysis, and a few representative successes and failures.
5. **Conclusion and limitations:** Answer the research questions within the evaluated scope and identify remaining limitations.

Prioritize a small pipeline diagram, a main results table, and one figure showing an informative trade-off or breakdown. Avoid spending much of the paper on generic RAG background or implementation listings.

## Intended contribution and claim boundaries

A defensible contribution is a reproducible case study of evidence retrieval, context retention, and answer generation for Serbian university regulations, supported by a verified benchmark and controlled comparisons.

Existing RAG optimization and evaluation methods must be acknowledged. Novelty should not be claimed merely for building a RAG chatbot, increasing context length, or searching a parameter grid.

The final paper should explain which changes improved which question categories, what remained difficult, and the associated efficiency trade-offs. Negative findings are useful when supported by controlled experiments. Acceptance is not guaranteed, and neither a perfect system nor universally optimal settings are prerequisites for an informative experimental paper.

## Sources and starting literature

- [TELFOR 2026: official author information, deadlines, sections, and paper length](https://www.telfor.rs/sr/autori/)
- [TELFOR: submission and author instructions](https://registration.telfor.rs/Info/InstructionsForAuthors)
- [Searching for Best Practices in Retrieval-Augmented Generation — EMNLP 2024](https://aclanthology.org/2024.emnlp-main.981/)
- [RAGChecker: A Fine-grained Framework for Diagnosing Retrieval-Augmented Generation](https://arxiv.org/abs/2408.08067)
- [RAGAs: Automated Evaluation of Retrieval Augmented Generation — EACL 2024](https://aclanthology.org/2024.eacl-demo.16/)

These references are a starting point, not a completed literature review. Verify the specific relationship between prior work and the eventual contribution before finalizing the novelty statement.
