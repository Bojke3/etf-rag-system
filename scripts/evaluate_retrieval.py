"""Offline evidence coverage in recorded contexts; no model, network or generation.

Coordinates refer to whitespace-normalized frozen source text, not chunk IDs.
Every requirement needs one complete alternative; an alternative can need several
source spans. Coverage is a union of source intervals, so overlapping chunks do
not double-count text and a span may be delivered in several chunks.
"""

import argparse
import hashlib
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = "benchmarking/retrieval_evidence.json"


def normalize(text):
    # Preserve case, punctuation, negations and numbers. Only layout is ignored.
    return re.sub(r"\s+", " ", text).strip()


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def object_hash(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True))


def project_path(value):
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def relative(path):
    # Portable reports, including when invoked from a different working directory.
    return Path(path).resolve().relative_to(ROOT).as_posix()


def document_key(value):
    return re.sub(r"[\W_]+", "", re.sub(r"\.pdf$", "", value, flags=re.I).casefold())


def load_evidence(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("normalization") != "whitespace_v1":
        raise ValueError("Unsupported evidence schema or normalization")
    benchmark = json.loads(project_path(data["benchmark"]).read_text(encoding="utf-8"))
    if object_hash(benchmark) != data["benchmark_sha256"]:
        raise ValueError("Benchmark changed: review evidence before updating its hash")
    questions = {q["id"]: q for q in benchmark["questions"]}
    documents = {}
    for record in data["documents"]:
        text = normalize(project_path(record["path"]).read_text(encoding="utf-8"))
        if digest(text) != record["normalized_sha256"]:
            raise ValueError(f"Frozen source changed: {record['path']}")
        key = document_key(record["document"])
        if key in documents:
            raise ValueError(f"Duplicate document: {key}")
        documents[key] = text
    cases = data["cases"]
    if len({c["question_id"] for c in cases}) != len(cases):
        raise ValueError("Duplicate evidence question IDs")
    if {c["question_id"] for c in cases} != set(questions):
        raise ValueError("Evidence must account for every benchmark question")
    for case in cases:
        qid = case["question_id"]
        if case["expected_behavior"] != questions[qid]["expected_behavior"]:
            raise ValueError(f"Behavior mismatch: {qid}")
        if case["review_status"] not in {"draft", "approved"}:
            raise ValueError(f"Unknown review status: {qid}")
        if case["review_status"] == "approved" and not case.get("reviewed_by", "").strip():
            raise ValueError(f"Approved evidence needs reviewer identification: {qid}")
        if case["scope"] not in {"answer", "supported_part", "not_applicable"}:
            raise ValueError(f"Unknown evaluation scope: {qid}")
        if case["scope"] == "not_applicable":
            if case["requirements"]:
                raise ValueError(f"Excluded case must not contain requirements: {qid}")
            continue
        requirements = case["requirements"]
        if not requirements or len({r["id"] for r in requirements}) != len(requirements):
            raise ValueError(f"Missing or duplicate requirements: {qid}")
        for requirement in requirements:
            if not requirement["alternatives"]:
                raise ValueError(f"Empty alternatives: {qid}")
            for alternative in requirement["alternatives"]:
                if not alternative["spans"]:
                    raise ValueError(f"Empty evidence alternative: {qid}")
                for span in alternative["spans"]:
                    text = documents[document_key(span["document"])]
                    start, end = span["start"], span["end"]
                    if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
                        raise ValueError(f"Invalid evidence coordinates: {qid}")
                    if digest(text[start:end]) != span["sha256"]:
                        raise ValueError(f"Evidence span changed: {qid}")
    return data, documents, questions


def locate(text, source):
    """Require one exact location; do not guess between repeated passages."""
    start = source.find(text)
    if not text or start < 0 or source.find(text, start + 1) >= 0:
        raise ValueError("Chunk cannot be uniquely mapped to frozen source")
    return start, start + len(text)


def same_chunk_id(recorded, serialized):
    if recorded == serialized:
        return True
    # Hierarchical runs recorded the numeric child ID in usage but serialized
    # the qualified child ID in sources. Rank, document, length and exact context
    # reconstruction are still checked independently.
    match = re.fullmatch(r".+::hierarchical::child::(\d+)", str(serialized))
    return type(recorded) is int and match is not None and recorded == int(match[1])


def map_context(row, documents):
    diagnostics = row.get("diagnostics") or {}
    if diagnostics.get("context_mode", "retrieved") != "retrieved":
        raise ValueError("Diagnostic/curated context is not a retrieval result")
    context = diagnostics.get("context")
    usage = diagnostics.get("chunk_usage")
    sources = row.get("sources")
    if not isinstance(context, str) or not isinstance(usage, list) or not isinstance(sources, list):
        raise ValueError("Missing recorded context, sources or chunk usage")
    if len(usage) != len(sources):
        raise ValueError("Chunk usage does not match sources")
    retrieved, delivered, pieces = {}, {}, []
    for rank, (chunk, use) in enumerate(zip(sources, usage), 1):
        text = chunk.get("text", "")
        used = use.get("context_chars_used")
        if (use.get("rank") != rank or type(used) is not int or not 0 <= used <= len(text)
                or use.get("document") != chunk.get("document")
                or not same_chunk_id(use.get("chunk_id"), chunk.get("chunk_id"))
                or use.get("text_chars") != len(text)):
            raise ValueError("Inconsistent recorded chunk usage")
        if not normalize(text):
            continue
        key = document_key(chunk["document"])
        if key not in documents:
            raise ValueError(f"Unknown source document: {chunk['document']}")
        start, end = locate(normalize(text), documents[key])
        retrieved.setdefault(key, []).append((start, end))
        if used:
            pieces.append(text[:used])
            prefix = normalize(text[:used])
            if prefix:
                delivered.setdefault(key, []).append((start, start + len(prefix)))
    if "\n\n".join(pieces) != context:
        raise ValueError("Reconstructed delivered chunks differ from recorded context")
    return retrieved, delivered, len(context)


def covers(intervals, start, end, source=""):
    cursor = start
    for left, right in sorted(intervals):
        if right <= cursor:
            continue
        if left > cursor and not (source and source[cursor:left].isspace()):
            return False
        cursor = right
        if cursor >= end:
            return True
    return False


def requirement_present(requirement, intervals, documents):
    return any(all(covers(intervals.get(document_key(s["document"]), []), s["start"], s["end"],
                          documents[document_key(s["document"])])
                   for s in option["spans"]) for option in requirement["alternatives"])


def score_case(case, row, documents, question):
    result = {"question_id": case["question_id"], "scope": case["scope"],
              "review_status": case["review_status"]}
    if case["scope"] == "not_applicable":
        return {**result, "status": "not_applicable", "reason": case["review_note"]}
    if row is None:
        return {**result, "status": "missing_run_question"}
    if row.get("question") != question["question"]:
        return {**result, "status": "unscorable", "reason": "Recorded question differs from benchmark"}
    try:
        retrieved, delivered, chars = map_context(row, documents)
    except ValueError as error:
        return {**result, "status": "unscorable", "reason": str(error)}
    items = [{"id": r["id"], "retrieved": requirement_present(r, retrieved, documents),
              "delivered": requirement_present(r, delivered, documents)} for r in case["requirements"]]
    count = sum(r["delivered"] for r in items)
    return {**result, "status": "scored", "requirements": items,
            "retrieved_coverage": sum(r["retrieved"] for r in items) / len(items),
            "delivered_coverage": count / len(items), "complete": count == len(items),
            "verdict": "complete" if count == len(items) else "partial" if count else "none",
            "context_chars": chars, "context_sha256": digest(row["diagnostics"]["context"])}


def aggregate(results, scope):
    eligible = [r for r in results if r["scope"] == scope]
    scored = [r for r in eligible if r["status"] == "scored"]
    # Missing cases never silently disappear from the denominator of a final metric.
    valid = bool(eligible) and len(scored) == len(eligible)
    return {"eligible_questions": len(eligible), "scored_questions": len(scored),
            "complete_questions": sum(r["complete"] for r in scored),
            "mean_evidence_coverage": statistics.mean(r["delivered_coverage"] for r in scored) if valid else None,
            "complete_evidence_rate": statistics.mean(r["complete"] for r in scored) if valid else None,
            "mean_retrieved_coverage": statistics.mean(r["retrieved_coverage"] for r in scored) if valid else None,
            "context_chars_mean": statistics.mean(r["context_chars"] for r in scored) if scored else None,
            "all_cases_available": valid}


def evaluate_run(run, data, documents, questions, allow_draft=False):
    raw = (run / "answers.jsonl").read_text(encoding="utf-8")
    rows = {}
    for line in raw.splitlines():
        if line.strip():
            row = json.loads(line)
            rows[row["id"]] = row  # Latest attempt, including a failed last attempt.
    results = []
    for case in data["cases"]:
        if case["scope"] != "not_applicable" and case["review_status"] != "approved" and not allow_draft:
            results.append({"question_id": case["question_id"], "scope": case["scope"],
                            "review_status": case["review_status"], "status": "needs_review"})
        else:
            results.append(score_case(case, rows.get(case["question_id"]), documents, questions[case["question_id"]]))
    return {"run": relative(run), "answers_sha256": digest(raw),
            "preliminary": any(c["review_status"] != "approved" for c in data["cases"]),
            "answer_questions": aggregate(results, "answer"),
            "supported_part_questions": aggregate(results, "supported_part"), "questions": results}


def review_markdown(data, documents, questions):
    lines = ["# Predlozi dokaza za proveru pretrage", "",
             "Oznake je prvobitno predložio AI. Status uz svako pitanje pokazuje da li su pregledane. "
             "`draft` znači NACRT, bez potvrđene ljudske provere.", "",
             "Proverite da li su navedeni pasusi dovoljni i ne traže nepotreban tekst. "
             "Dodajte alternativne dokaze, proverite OCR/formule i verzije pravilnika prema PDF-u. "
             "Menja se retrieval_evidence.json; ovaj pregled se ponovo generiše iz njega.", ""]
    for case in data["cases"]:
        qid = case["question_id"]
        q = questions[qid]
        lines += [f"## {qid} — {case['review_status']}", "", q["question"], "",
                  f"**Očekivani odgovor:** {q['expected_answer']}", "",
                  f"**Napomena:** {case['review_note']}", ""]
        for r in case["requirements"]:
            lines += [f"### {r['id']}: {r['description']}", ""]
            for number, alternative in enumerate(r["alternatives"], 1):
                lines += [f"Alternativa {number} (svi njeni pasusi su potrebni):", ""]
                for s in alternative["spans"]:
                    quote = documents[document_key(s["document"])][s["start"]:s["end"]]
                    lines += [f"- {s['document']} — pozicije {s['start']}:{s['end']}", "", f"> {quote}", ""]
    return "\n".join(lines)


def report_markdown(report):
    lines = ["# Retrieval evidence coverage", "", "Evidence: " + report["evidence"], "",
             "DRAFT results are exploratory, not validated benchmark scores. "
             "Coverage measures annotated source text presence, not semantic understanding or absence of distracting text.", "",
             "| Run | Draft | Scored / eligible (answer) | Complete | Coverage | Complete rate |",
             "|---|---|---:|---:|---:|---:|"]
    for run in report["runs"]:
        a = run["answer_questions"]
        cov = "N/A" if a["mean_evidence_coverage"] is None else f"{a['mean_evidence_coverage']:.3f}"
        rate = "N/A" if a["complete_evidence_rate"] is None else f"{a['complete_evidence_rate']:.3f}"
        lines.append(f"| {Path(run['run']).name} | {run['preliminary']} | {a['scored_questions']} / {a['eligible_questions']} | {a['complete_questions']} | {cov} | {rate} |")
    for run in report["runs"]:
        lines += ["", f"## {Path(run['run']).name}", "",
                  "| Question | Scope | Result | Missing delivered requirements / issue |",
                  "|---|---|---|---|"]
        for q in run["questions"]:
            missing = ", ".join(r["id"] for r in q.get("requirements", []) if not r["delivered"])
            note = q.get("reason", missing).replace("|", "\\|")
            lines.append(f"| {q['question_id']} | {q['scope']} | {q.get('verdict', q['status'])} | {note} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", default=DEFAULT_EVIDENCE)
    parser.add_argument("--run", action="append", default=[], help="Run directory; repeat to compare runs")
    parser.add_argument("--allow-draft", action="store_true", help="Explore unreviewed annotations; never marks them approved")
    parser.add_argument("--output", help="JSON report path; also writes a Markdown report alongside")
    parser.add_argument("--review-output", help="Render questions and source spans for human review")
    args = parser.parse_args(argv)
    try:
        path = project_path(args.evidence)
        data, documents, questions = load_evidence(path)
        if args.review_output:
            target = project_path(args.review_output)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(review_markdown(data, documents, questions), encoding="utf-8")
            print(f"Review: {relative(target)}")
        if args.run:
            if not args.output:
                raise ValueError("Provide --output for reproducible retrieval results")
            report = {"schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
                      "evidence": relative(path), "evidence_sha256": object_hash(data),
                      "evaluator_sha256": digest(Path(__file__).read_text(encoding="utf-8")),
                      "runs": [evaluate_run(project_path(r), data, documents, questions, args.allow_draft) for r in args.run]}
            target = project_path(args.output)
            if target.suffix != ".json":
                raise ValueError("--output must end in .json")
            if target.exists() or target.with_suffix(".md").exists():
                raise ValueError("Report already exists; choose a new output name")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            target.with_suffix(".md").write_text(report_markdown(report), encoding="utf-8")
            print(f"Report: {relative(target)}")
            for run in report["runs"]:
                a = run["answer_questions"]
                print(f"{Path(run['run']).name}: {a['scored_questions']}/{a['eligible_questions']} scored; "
                      f"{a['complete_questions']} complete; draft={run['preliminary']}")
        elif not args.review_output:
            print(f"Validated evidence: {len(data['cases'])} cases (review status unchanged)")
    except (ValueError, KeyError, OSError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":
    main()
