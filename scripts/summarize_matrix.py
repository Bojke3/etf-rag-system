"""Summarise the run matrix: retrieval metrics and answer counters per configuration.

Every number is read from the runs themselves, so the table cannot drift from the
data it describes.

Retrieval metrics are computed only over questions whose `expected_behavior` is
`"answer"`. The other eight of the sixty ask the system to abstain, to answer only
the supported part, or to ask for clarification -- for those no document is the one
that should have been retrieved, so a miss is not defined. Counting them made
`REAL_056` ("what is the tuition for 2026/2027", which no document in the corpus
states) look like a retrieval failure. Restricted this way the figures reproduce the
ones reported on 18-09 to three decimals.

Retrieval is deterministic: the same index and question give the same five passages
in every repetition. The spread across repetitions is therefore expected to be zero,
and the script says so when it is not, because that means something was not held
fixed.
"""

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "benchmarking" / "runs"
SCORED_BEHAVIOUR = "answer"

SHORT_EMBEDDING = {
    "sentence-transformers/all-MiniLM-L6-v2": "MiniLM-L6",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": "MiniLM-L12-multi",
    "BAAI/bge-m3": "bge-m3",
}


def normalise_document(name):
    """Compare document names without extension, case or punctuation."""
    stem = re.sub(r"\.pdf$", "", (name or "").strip(), flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", stem.lower())


def latest_answers(run_dir):
    """Last attempt per question: a resumed run appends, so earlier lines are stale."""
    path = run_dir / "answers.jsonl"
    if not path.is_file():
        return {}
    latest = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            latest[row["id"]] = row
    return latest


def run_metrics(run_dir):
    answers = latest_answers(run_dir)
    if not answers:
        return None

    hits, reciprocal_ranks, contexts, lengths = [], [], [], []
    for row in answers.values():
        if row.get("expected_behavior") != SCORED_BEHAVIOUR:
            continue
        references = {normalise_document(s.get("document"))
                      for s in (row.get("reference_sources") or []) if s.get("document")}
        if not references:
            continue
        retrieved = [normalise_document(s.get("document")) for s in (row.get("sources") or [])]
        rank = next((i + 1 for i, doc in enumerate(retrieved) if doc in references), None)
        hits.append(1.0 if rank else 0.0)
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)

    successes = [r for r in answers.values() if r.get("status") == "success"]
    for row in successes:
        diagnostics = row.get("diagnostics") or {}
        if diagnostics.get("context_chars"):
            contexts.append(diagnostics["context_chars"])
        eval_count = (diagnostics.get("generation") or {}).get("eval_count")
        if eval_count:
            lengths.append(eval_count)

    def done_reason(row):
        return ((row.get("diagnostics") or {}).get("generation") or {}).get("done_reason")

    return {
        "questions_scored": len(hits),
        "doc_hit": statistics.mean(hits) if hits else None,
        "mrr": statistics.mean(reciprocal_ranks) if reciprocal_ranks else None,
        "answers": len(answers),
        "successes": len(successes),
        "errors": len(answers) - len(successes),
        "truncated": sum(1 for r in answers.values()
                         if (r.get("diagnostics") or {}).get("context_truncated")),
        "cut": sum(1 for r in answers.values() if done_reason(r) not in (None, "stop")),
        "context_median": statistics.median(contexts) if contexts else None,
        "context_max": max(contexts) if contexts else None,
        "answer_tokens": statistics.mean(lengths) if lengths else None,
    }


def describe(run_dir):
    config_path = run_dir / "run_config.json"
    if not config_path.is_file():
        return None
    config = json.loads(config_path.read_text(encoding="utf-8"))
    backend = config.get("backend") or {}
    retrieval = backend.get("retrieval_provenance") or {}
    component = config.get("component_config") or {}
    metrics = run_metrics(run_dir)
    if not metrics:
        return None

    embedding = retrieval.get("embedding_model") or component.get("embedding_model") or "?"
    strategy = retrieval.get("effective_strategy") or "?"
    execution = backend.get("execution")
    return {
        "run": run_dir.name,
        "config": config.get("label") or "-",
        "embedding": SHORT_EMBEDDING.get(embedding, embedding),
        "chunking": "flat" if strategy == "flat_legacy_or_staged" else strategy,
        "generator": backend.get("model") or config.get("model") or "?",
        "top_k": config.get("top_k"),
        "context_budget": backend.get("context_max_chars"),
        "num_ctx": (backend.get("generation_options") or {}).get("num_ctx"),
        "machine": {"local": "Mac", "ssh": "server"}.get(execution, execution or "?"),
        **metrics,
    }


def group(rows):
    """One entry per configuration, with the spread across its repetitions."""
    groups = {}
    for row in rows:
        groups.setdefault(row["config"], []).append(row)

    summaries = []
    for config, members in sorted(groups.items()):
        def spread(key):
            values = [m[key] for m in members if m.get(key) is not None]
            if not values:
                return None, None
            return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)

        doc_hit, doc_hit_sd = spread("doc_hit")
        mrr, mrr_sd = spread("mrr")
        tokens, tokens_sd = spread("answer_tokens")
        machines = sorted({m["machine"] for m in members})
        budgets = sorted({m["context_budget"] for m in members}, key=lambda v: (v is None, v))
        summaries.append({
            "config": config,
            "runs": len(members),
            "embedding": members[0]["embedding"],
            "chunking": members[0]["chunking"],
            "generator": members[0]["generator"],
            "context_budget": budgets[0] if len(budgets) == 1 else "mesano",
            "questions_scored": members[0]["questions_scored"],
            "doc_hit": doc_hit, "doc_hit_sd": doc_hit_sd,
            "mrr": mrr, "mrr_sd": mrr_sd,
            "answer_tokens": tokens, "answer_tokens_sd": tokens_sd,
            "successes": sum(m["successes"] for m in members),
            "expected": sum(m["answers"] for m in members),
            "errors": sum(m["errors"] for m in members),
            "truncated": sum(m["truncated"] for m in members),
            "cut": sum(m["cut"] for m in members),
            "context_median": statistics.median([m["context_median"] for m in members
                                                 if m["context_median"] is not None] or [0]),
            "context_max": max([m["context_max"] for m in members
                                if m["context_max"] is not None] or [0]),
            # Retrieval is deterministic, so this should be a single machine-independent
            # value; a non-zero spread means a repetition did not use the same index.
            "retrieval_varies": (doc_hit_sd or 0) > 1e-9 or (mrr_sd or 0) > 1e-9,
            "machines": "+".join(machines),
        })
    return summaries


def fmt(value, digits=3):
    return "-" if value is None else f"{value:.{digits}f}"


def render_markdown(summaries):
    lines = [
        f"Retrieval metrics cover the {summaries[0]['questions_scored']} questions with "
        f"`expected_behavior={SCORED_BEHAVIOUR}`; the rest have no target document.",
        "",
        "| Config | Embedding | Chunking | Runs | Machine | doc-hit@5 | MRR | Answers | Err | Trunc | Cut | Context med/max | Answer tok |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| `{s['config']}` | {s['embedding']} | {s['chunking']} | {s['runs']} | {s['machines']} | "
            f"{fmt(s['doc_hit'])} | {fmt(s['mrr'])} | {s['successes']}/{s['expected']} | "
            f"{s['errors']} | {s['truncated']} | {s['cut']} | "
            f"{s['context_median']:,.0f} / {s['context_max']:,.0f} | {fmt(s['answer_tokens'], 0)} |"
        )
    warnings = [s["config"] for s in summaries if s["retrieval_varies"]]
    if warnings:
        lines += ["", "> **Retrieval differs between repetitions in: "
                      + ", ".join(f"`{c}`" for c in warnings)
                      + ".** Retrieval is deterministic, so this means something was not held "
                        "fixed across those runs. Do not report these figures before explaining it."]
    return "\n".join(lines)


def render_latex(summaries):
    lines = [
        "% Retrieval metrics over questions with expected_behavior=answer "
        f"(n={summaries[0]['questions_scored']} of 60).",
        r"\begin{tabular}{lllrrr}",
        r"\toprule",
        r"Config & Embedding & Chunking & doc-hit@5 & MRR & Answer tok. \\",
        r"\midrule",
    ]
    for s in summaries:
        chunking = s["chunking"].replace("_", r"\_")
        lines.append(f"{s['config']} & {s['embedding']} & {chunking} & "
                     f"{fmt(s['doc_hit'])} & {fmt(s['mrr'])} & {fmt(s['answer_tokens'], 0)} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs-dir", default=str(RUNS), help="Directory holding the runs")
    parser.add_argument("--config", action="append",
                        help="Only these configuration labels; repeatable")
    parser.add_argument("--latex", action="store_true", help="Emit a LaTeX tabular instead")
    parser.add_argument("--per-run", action="store_true", help="One line per run, not per config")
    parser.add_argument("--output", help="Write to this file instead of stdout")
    args = parser.parse_args(argv)

    runs_dir = Path(args.runs_dir)
    rows = [d for d in (describe(p) for p in sorted(runs_dir.iterdir())
                        if p.is_dir() and not p.name.startswith("_")) if d]
    if args.config:
        wanted = set(args.config)
        rows = [r for r in rows if r["config"] in wanted]
    rows = [r for r in rows if r["questions_scored"]]
    if not rows:
        print("No runs with scored questions found.", file=sys.stderr)
        return 1

    if args.per_run:
        lines = ["| Run | Config | Machine | doc-hit@5 | MRR | Answers | Err | Trunc | Cut |",
                 "|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| `{r['run']}` | {r['config']} | {r['machine']} | {fmt(r['doc_hit'])} | "
                         f"{fmt(r['mrr'])} | {r['successes']}/{r['answers']} | {r['errors']} | "
                         f"{r['truncated']} | {r['cut']} |")
        text = "\n".join(lines)
    else:
        summaries = group(rows)
        text = render_latex(summaries) if args.latex else render_markdown(summaries)

    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
