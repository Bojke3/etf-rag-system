# BM25 retrieval-only baseline

Executed locally on the existing 60 benchmark questions, without answer generation, embeddings, model downloads or API calls. The principal coverage metric uses the same 52 answer-scope questions as existing retrieval reports. Five supported-part questions and three not-applicable cases are handled separately by the existing evidence evaluator.

| Retriever | Mean delivered evidence coverage (52 questions) | Complete-evidence questions | Mean context characters |
|---|---:|---:|---:|
| BM25 flat | 0.788462 | 38/52 | 5118 |
| BGE-M3 flat (`c105_r01`) | 0.858974 | 41/52 | 5116 |
| GTE flat (`c111_r01`) | 0.637821 | 28/52 | 5093 |
| BGE-M3 hierarchical (`c107_r01`) | 0.980769 | 51/52 | 15284 |
| GTE hierarchical (`c113_r01`) | 0.865385 | 44/52 | 15716 |

The BM25/BGE flat difference is -0.070513 in mean evidence coverage (7.05 percentage points). This is an observed descriptive difference, not an established statistically significant difference. BM25 exceeds GTE flat, so results do not justify a general claim that lexical retrieval underperforms every vector retriever. Hierarchical rows are descriptive references with larger expanded contexts, not corpus/representation-matched comparisons.

Coverage is the mean, across eligible questions, of the fraction of annotated evidence requirements fully present in the constructed context. It is not document hit rate, answer correctness or atomic-claim faithfulness. The full per-question evidence results are in `retrieval_report.json`; the corresponding detailed table is in `retrieval_report.md`.

## Frozen setup

- Corpus: all 205 original flat chunks from `data/chunks_v1_c1024_o150`, verified against their manifest and the metadata SHA256 pinned in the BGE flat run. The complete chunk multiset is identical.
- Same `top_k=5`, same context builder and same maximum 22,000 characters as BGE flat. No context reaches this cap in the flat setup.
- Standard-library BM25 implementation, `k1=1.2`, `b=0.75`, positive IDF `ln(1 + (N-df+0.5)/(df+0.5))`, term-frequency saturation and document-length normalization. Parameters fixed before running; no benchmark-driven tuning.
- Tokenizer: Serbian Cyrillic-to-Latin conversion, Unicode case folding, diacritic folding (`đ` to `dj`), ASCII alphanumeric tokens. Applied identically to chunks and queries, without changing original saved text. No stemming, stopword removal, query expansion or reranking.
- Each unique query term contributes once. Equal scores retain the frozen chunk manifest order. No-overlap queries return no results; zero-score chunks are not used as padding.
- The corpus is not deduplicated or OCR-repaired anew. All lexical and vector comparisons use the existing frozen source/evidence annotations.
- One deterministic retrieval pass. Repeating it would not create independent observations.

The positive IDF and default parameters follow the documented BM25 form: https://lucene.apache.org/core/9_12_3/core/org/apache/lucene/search/similarities/BM25Similarity.html . This is a small explicit implementation of the formula, not a claim to reproduce Lucene's entire analyzer/index scoring pipeline.

## Outputs and rerunning

`retrieval.jsonl` contains only questions, retrieved chunks, scores, and constructed-context diagnostics. There are no generated answers. `run_config.json` records parameters and provenance hashes. `retrieval_report.json` and `.md` reuse the existing evaluator and compare saved vector runs; those vector runs are not rerun or modified.

From the project root, a new run can be made with:

```powershell
.\.venv\Scripts\python.exe scripts/run_bm25_retrieval.py --run-id bm25_flat_top5_v2
```

Use a new run ID to preserve old outputs. `--dry-run` validates corpus hashes, all source mappings and comparison records without writing files. Optional `--compare-run` arguments override the extra hierarchical/GTE reference runs; the corpus-matched flat reference remains included.

Validation: eight focused BM25 tests and 25 existing evidence-evaluator tests passed. A full preflight and the actual 60-question run both completed successfully with every eligible question scorable.
