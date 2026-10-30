"""Run offline BM25 retrieval and the existing frozen-evidence evaluator, without an LLM."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.retrieval.bm25 import BM25Retriever, TOKENIZER_VERSION
from src.retrieval.context import ContextBuilder
from src.retrieval.parent_aware import ParentAwareRetriever
from scripts import evaluate_retrieval as ev


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def load_chunks(directory):
    directory = Path(directory).resolve()
    manifest_path = directory / "manifest.json"
    manifest = read(manifest_path)
    if manifest.get("schema_version") != 1 or manifest.get("stage") != "chunking" or manifest.get("settings", {}).get("strategy") != "fixed_characters":
        raise ValueError("This baseline requires the frozen flat fixed-character chunk manifest.")
    chunks, seen = [], set()
    for item in manifest["chunks"]:
        path = (directory / item["file"]).resolve()
        if directory not in path.parents or file_hash(path) != item["sha256"]:
            raise ValueError("Chunk path or SHA256 mismatch: " + item["file"])
        text = path.read_text(encoding="utf-8")
        if len(text) != item["chars"]:
            raise ValueError("Chunk character count mismatch: " + item["file"])
        identity = (item["document"], str(item["chunk_id"]))
        if identity in seen:
            raise ValueError("Duplicate document/chunk ID.")
        seen.add(identity)
        chunks.append({"document": item["document"], "chunk_id": item["chunk_id"], "text": text})
    return chunks, manifest


def verify_flat_comparison(chunks, reference):
    config = read(reference / "run_config.json")
    store = config["component_config"]["vector_store_path"]
    metadata_path = ev.project_path(store) / "metadatas.json"
    metadata = read(metadata_path)
    signature = lambda rows: Counter((r["document"], str(r["chunk_id"]), ev.digest(r["text"])) for r in rows)
    if signature(chunks) != signature(metadata):
        raise ValueError("BM25 corpus differs from the flat vector baseline corpus.")
    provenance = config["backend"]["retrieval_provenance"]
    pinned = provenance.get("files", {}).get("metadatas.json")
    if pinned is None or file_hash(metadata_path) != pinned:
        raise ValueError("Flat baseline metadata no longer matches its recorded SHA256.")
    return config, {"reference_run": ev.relative(reference), "metadata": ev.relative(metadata_path),
                    "metadata_sha256": pinned, "identical_chunk_multiset": True}


def load_hierarchical(directory, reference):
    """Verify frozen children and parents against the exact indexed reference artifacts."""
    directory = Path(directory).resolve()
    manifest = read(directory / "manifest.json")
    if manifest.get("schema_version") != 1 or manifest.get("stage") != "chunking" or manifest.get("settings", {}).get("strategy") != "hierarchical":
        raise ValueError("Expected the frozen hierarchical chunk manifest.")
    source = (directory / manifest["chunks_file"]).resolve()
    if directory not in source.parents or file_hash(source) != manifest["chunks_file_sha256"]:
        raise ValueError("Hierarchical chunk source path or SHA256 mismatch.")
    original = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(original) != manifest["chunk_count"] or Counter(c["level"] for c in original) != Counter(manifest["level_counts"]):
        raise ValueError("Hierarchical chunk counts changed.")
    if len({c["chunk_id"] for c in original}) != len(original):
        raise ValueError("Duplicate hierarchical chunk IDs.")
    config = read(reference / "run_config.json")
    provenance = config["backend"]["retrieval_provenance"]
    if provenance.get("effective_strategy") != "hierarchical":
        raise ValueError("Reference is not hierarchical retrieval.")
    store = ev.project_path(config["component_config"]["vector_store_path"])
    names = ("metadatas_hierarchical.json", "parents_hierarchical.json")
    hashes = {}
    for name in names:
        pinned = provenance.get("files", {}).get(name)
        if pinned is None or file_hash(store / name) != pinned:
            raise ValueError("Hierarchical index artifact changed: " + name)
        hashes[name] = pinned
    children, parents = (read(store / name) for name in names)
    expected_children = Counter((c["chunk_id"], c["metadata"]["document"], c["parent_chunk_id"], ev.digest(c["text"]))
                                for c in original if c["level"] == "child")
    actual_children = Counter((c["id"], c["document"], c["parent_chunk_id"], ev.digest(c["text"])) for c in children)
    expected_parents = {c["chunk_id"]: (c["metadata"]["document"], c["text"]) for c in original if c["level"] == "parent"}
    actual_parents = {pid: (c["document"], c["text"]) for pid, c in parents.items()}
    if expected_children != actual_children or expected_parents != actual_parents:
        raise ValueError("Indexed hierarchical children/parents differ from frozen chunks.")
    if any(c["parent_chunk_id"] not in parents or parents[c["parent_chunk_id"]]["document"] != c["document"] for c in children):
        raise ValueError("Missing or cross-document parent mapping.")
    return children, manifest, parents, config, {"reference_run": ev.relative(reference),
        "store": ev.relative(store), "files_sha256": hashes, "identical_children_and_parents": True,
        "parent_count": len(parents), "chunks_file_sha256": manifest["chunks_file_sha256"]}


def scored_report(run, rows, evidence, documents, questions):
    results = [ev.score_case(c, rows[c["question_id"]], documents, questions[c["question_id"]]) for c in evidence["cases"]]
    if any(r["status"] not in {"scored", "not_applicable"} for r in results):
        raise ValueError("Some BM25 results cannot be mapped to frozen evidence: " + str([(r['question_id'], r.get('reason')) for r in results if r['status'] == 'unscorable']))
    return {"run": ev.relative(run), "retrieval_sha256": file_hash(run / "retrieval.jsonl"), "preliminary": False,
            "answer_questions": ev.aggregate(results, "answer"),
            "supported_part_questions": ev.aggregate(results, "supported_part"), "questions": results}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", choices=("flat", "hierarchical"), default="flat")
    parser.add_argument("--run-id", help="Default: bm25_<strategy>_top5_v1")
    parser.add_argument("--chunks", help="Default: frozen chunk directory for the selected strategy")
    parser.add_argument("--evidence", default="benchmarking/retrieval_evidence.json")
    parser.add_argument("--reference", "--flat-reference", dest="reference", help="Default: corresponding BGE flat or hierarchical run")
    parser.add_argument("--compare-run", action="append", help="Additional recorded vector run; repeat as needed")
    parser.add_argument("--k1", type=float, default=1.2)
    parser.add_argument("--b", type=float, default=.75)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    args.run_id = args.run_id or f"bm25_{args.strategy}_top5_v1"
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.run_id):
        raise ValueError("Invalid run ID.")
    evidence_path = ev.project_path(args.evidence)
    evidence, documents, questions = ev.load_evidence(evidence_path)
    if any(c["review_status"] != "approved" for c in evidence["cases"]):
        raise ValueError("Evidence must already be approved; this script never approves annotations.")
    hierarchical = args.strategy == "hierarchical"
    chunks_path = ev.project_path(args.chunks or ("data/chunks_v2_hier" if hierarchical else "data/chunks_v1_c1024_o150"))
    reference = ev.project_path(args.reference or ("benchmarking/runs/dev_combined_c107_r01" if hierarchical else "benchmarking/runs/dev_combined_c105_r01"))
    parents = {}
    if hierarchical:
        chunks, manifest, parents, reference_config, corpus_verification = load_hierarchical(chunks_path, reference)
    else:
        chunks, manifest = load_chunks(chunks_path)
        reference_config, corpus_verification = verify_flat_comparison(chunks, reference)
    top_k, budget = reference_config["top_k"], reference_config["backend"]["context_max_chars"]
    comparisons = args.compare_run if args.compare_run is not None else [p for p in [
        "benchmarking/runs/dev_combined_c105_r01", "benchmarking/runs/dev_combined_c107_r01",
        "benchmarking/runs/dev_combined_c111_r01", "benchmarking/runs/dev_combined_c113_r01"] if ev.project_path(p) != reference]
    # Evaluate recorded baselines before writing anything; fail rather than silently dropping cases.
    comparison_reports = [ev.evaluate_run(path, evidence, documents, questions) for path in [reference] + [ev.project_path(p) for p in comparisons]]
    for report in comparison_reports:
        if any(q["status"] not in {"scored", "not_applicable"} for q in report["questions"]):
            raise ValueError("Comparison run is incomplete or unscorable: " + report["run"])
    lexical = BM25Retriever(chunks, args.k1, args.b)
    retriever = ParentAwareRetriever(lexical, parents) if hierarchical else lexical
    run = ROOT / "benchmarking/runs" / args.run_id
    if run.exists():
        raise ValueError("Run directory already exists. Choose a new --run-id; no outputs were overwritten.")
    retriever_name = "ParentAwareRetriever(BM25Retriever)" if hierarchical else "BM25Retriever"
    config = {"schema_version": 1, "run_id": args.run_id, "mode": "retrieval_only", "retriever": retriever_name,
              "strategy": args.strategy, "parent_expansion": hierarchical, "parent_count": len(parents),
              "parent_expansion_policy": "top-k child hits, replace with parents, deduplicate, no refill" if hierarchical else None,
              "parent_aware_sha256": file_hash(ROOT / "src/retrieval/parent_aware.py") if hierarchical else None,
              "created_at": datetime.now(timezone.utc).isoformat(), "top_k": top_k, "context_max_chars": budget,
              "k1": args.k1, "b": args.b, "idf": "ln(1 + (N - df + 0.5)/(df + 0.5))",
              "query_tf": "one contribution per unique normalized query term", "tokenizer": TOKENIZER_VERSION,
              "normalization": "Serbian Cyrillic to Latin; casefold; diacritic folding (dj for đ); ASCII alphanumeric tokens",
              "stemming": False, "stopword_removal": False, "query_expansion": False,
              "zero_overlap_policy": "return no documents; never pad with arbitrary zero-score chunks",
              "ties": "stable pinned index metadata order" if hierarchical else "stable frozen manifest order",
              "chunk_count": len(chunks), "avg_chunk_tokens": lexical.avgdl,
              "corpus": ev.relative(chunks_path), "chunk_manifest_sha256": file_hash(chunks_path / "manifest.json"),
              "corpus_verification": corpus_verification, "benchmark": evidence["benchmark"],
              "benchmark_sha256": evidence["benchmark_sha256"], "evidence": ev.relative(evidence_path),
              "evidence_sha256": ev.object_hash(evidence), "implementation_sha256": file_hash(ROOT / "src/retrieval/bm25.py"),
              "runner_sha256": file_hash(Path(__file__)), "context_builder_sha256": file_hash(ROOT / "src/retrieval/context.py"),
              "evaluator_sha256": file_hash(Path(ev.__file__)),
              "comparison_note": f"Direct corpus-matched comparison is against {args.strategy} BGE vector retrieval. Comparisons across strategies use different expansion/context size. Fixed defaults; no parameter tuning on test questions. One deterministic pass; repeated identical passes are not independent observations."}
    rows = {}
    for qid, question in questions.items():
        start = time.perf_counter()
        sources = retriever.retrieve(question["question"], top_k=top_k)
        seconds = time.perf_counter() - start
        details = ContextBuilder.build_context_details(sources, budget)
        rows[qid] = {"id": qid, "question": question["question"], "status": "retrieval_only", "sources": sources,
                     "diagnostics": {**details, "context_mode": "retrieved", "retriever": retriever_name,
                                     "retrieval_seconds": seconds}}
        # Preflight exact source mapping, including zero-overlap cases, before writing the run.
        ev.map_context(rows[qid], documents)
    print(f"BM25: {len(chunks)} chunks, {len(rows)} questions, top_k={top_k}, budget={budget}; no model/API calls.")
    if args.dry_run:
        print("DRY RUN OK: corpus hashes, comparisons, evidence and every context mapping verified; no output written.")
        return
    run.mkdir(parents=True)
    write(run / "run_config.json", config)
    (run / "retrieval.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False, allow_nan=False) + "\n" for r in rows.values()), encoding="utf-8")
    result = scored_report(run, rows, evidence, documents, questions)
    report = {"schema_version": 1, "created_at": config["created_at"], "mode": "retrieval_only",
              "evidence": ev.relative(evidence_path), "evidence_sha256": ev.object_hash(evidence),
              "comparison_note": config["comparison_note"], "runs": [result] + comparison_reports}
    write(run / "retrieval_report.json", report)
    (run / "retrieval_report.md").write_text(ev.report_markdown(report), encoding="utf-8")
    for row in report["runs"]:
        a = row["answer_questions"]
        print(f"{Path(row['run']).name}: coverage={a['mean_evidence_coverage']:.4f}; complete={a['complete_evidence_rate']:.4f}; mean_chars={a['context_chars_mean']:.0f}")
    print("Saved: " + ev.relative(run))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
