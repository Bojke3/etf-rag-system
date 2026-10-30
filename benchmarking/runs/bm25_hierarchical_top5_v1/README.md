# BM25 hierarchical retrieval-only baseline

Executed locally on all 60 benchmark questions, without generation, embeddings or API calls. Same evidence evaluator as the flat BM25 and existing vector runs. Main metrics use the 52 answer-scope questions.

| Retriever | Mean evidence coverage | Complete-evidence questions | Mean context characters |
|---|---:|---:|---:|
| bm25_hierarchical_top5_v1 | 0.865385 | 44/52 | 14849 |
| dev_combined_c107_r01 | 0.980769 | 51/52 | 15284 |
| dev_combined_c105_r01 | 0.858974 | 41/52 | 5116 |
| dev_combined_c111_r01 | 0.637821 | 28/52 | 5093 |
| dev_combined_c113_r01 | 0.865385 | 44/52 | 15716 |

## Setup

- Search the 176 original child chunks with BM25, then expand to the 51 original parent chunks using the existing ParentAwareRetriever.
- Select top 5 child hits, preserve rank, deduplicate repeated parents, and do not refill the list. This matches the existing vector hierarchical policy.
- The exact indexed metadata and parent files are SHA256-checked against the recorded BGE hierarchical run. Both are cross-checked against the frozen hierarchical chunk manifest.
- Same context builder and maximum 22,000 characters as BGE hierarchical. The full text is evaluated after the existing truncation policy, including separators.
- BM25 parameters and tokenizer are unchanged from the flat baseline: k1=1.2, b=0.75, positive IDF, unique query terms, Serbian script/diacritic normalization, no stemming, stopword removal or tuning. Text is normalized only for lexical scoring; original context text is preserved.
- Equal scores use the pinned child metadata order. No-overlap queries receive no arbitrary zero-score padding.
- One deterministic pass; repeated identical runs are not independent observations.

## Interpretation

BM25 hierarchical coverage is 0.865385 (86.54%), compared with 0.788462 (78.85%) for BM25 flat. The hierarchical result has 44/52 questions with complete evidence. BGE hierarchical reaches 0.980769 (98.08%), an observed difference of 11.54 percentage points. GTE hierarchical has the same aggregate coverage and complete-evidence rate as BM25 hierarchical; this does not imply identical per-question retrieval or equivalence. These are descriptive differences, without significance testing.

Hierarchical versus flat comparisons also change the delivered context length. The main controlled lexical/vector comparison here is BM25 hierarchical against BGE hierarchical with the same child/parent corpus and expansion policy. Coverage concerns annotated evidence presence, not answer accuracy or faithfulness.

## Reproduce

From the project root, use a NEW run ID:

```powershell
.\.venv\Scripts\python.exe scripts/run_bm25_retrieval.py --strategy hierarchical --run-id bm25_hierarchical_top5_v2
```

Add `--dry-run` to validate without writing output. The default run is already saved and will not be overwritten. Outputs include run_config.json, retrieval.jsonl, retrieval_report.json and retrieval_report.md. Old flat outputs were preserved.

Validation: 10 BM25 tests and 25 evidence-evaluator tests passed; all 60 returned contexts map to frozen source text.
