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
    retrieved, delivered, pieces, chunks = {}, {}, [], []
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
        mapped = {"rank": rank, "document": key, "retrieved": (start, end), "delivered": None}
        chunks.append(mapped)
        if used:
            pieces.append(text[:used])
            prefix = normalize(text[:used])
            if prefix:
                delivered.setdefault(key, []).append((start, start + len(prefix)))
                mapped["delivered"] = (start, start + len(prefix))
    if "\n\n".join(pieces) != context:
        raise ValueError("Reconstructed delivered chunks differ from recorded context")
    return retrieved, delivered, len(context), chunks


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


def requirement_locations(requirement, chunks, stage, documents):
    """Report output-list ranks, not index IDs or pre-deduplication child ranks.

Supporting ranks form one sufficient set within the earliest complete prefix.
They need not be the only sufficient set or the smallest possible set.
"""
    def present(selected):
        intervals = {}
        for chunk in selected:
            if chunk[stage] is not None:
                intervals.setdefault(chunk["document"], []).append(chunk[stage])
        return requirement_present(requirement, intervals, documents)

    contributing = []
    for chunk in chunks:
        if chunk[stage] is None:
            continue
        left, right = chunk[stage]
        for option in requirement["alternatives"]:
            if any(document_key(s["document"]) == chunk["document"]
                   and max(left, s["start"]) < min(right, s["end"])
                   and documents[chunk["document"]][max(left, s["start"]):min(right, s["end"])].strip()
                   for s in option["spans"]):
                contributing.append(chunk)
                break
    full = [chunk["rank"] for chunk in contributing if present([chunk])]
    supporting, completion_rank = [], None
    prefix = []
    for chunk in contributing:
        prefix.append(chunk)
        if present(prefix):
            completion_rank = chunk["rank"]
            supporting = list(prefix)
            # Remove redundant hits without mixing incomplete alternatives.
            for candidate in reversed(prefix):
                remaining = [c for c in supporting if c["rank"] != candidate["rank"]]
                if present(remaining):
                    supporting = remaining
            break
    return {"full_chunk_ranks": full,
            "contributing_chunk_ranks": [c["rank"] for c in contributing],
            "supporting_chunk_ranks": [c["rank"] for c in supporting],
            "complete_by_rank": completion_rank}


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
        retrieved, delivered, chars, chunks = map_context(row, documents)
    except ValueError as error:
        return {**result, "status": "unscorable", "reason": str(error)}
    items = [{"id": r["id"], "retrieved": requirement_present(r, retrieved, documents),
              "delivered": requirement_present(r, delivered, documents),
              "retrieved_locations": requirement_locations(r, chunks, "retrieved", documents),
              "delivered_locations": requirement_locations(r, chunks, "delivered", documents)}
             for r in case["requirements"]]
    count = sum(r["delivered"] for r in items)
    return {**result, "status": "scored", "requirements": items,
            "retrieved_coverage": sum(r["retrieved"] for r in items) / len(items),
            "delivered_coverage": count / len(items), "complete": count == len(items),
            "all_evidence_by_rank": max(r["delivered_locations"]["complete_by_rank"] for r in items)
            if count == len(items) else None,
            "verdict": "complete" if count == len(items) else "partial" if count else "none",
            "context_chars": chars, "context_sha256": digest(row["diagnostics"]["context"])}


def aggregate(results, scope):
    eligible = [r for r in results if r["scope"] == scope]
    scored = [r for r in eligible if r["status"] == "scored"]
    # Missing cases never silently disappear from the denominator of a final metric.
    valid = bool(eligible) and len(scored) == len(eligible)
    requirements = [r for q in scored for r in q["requirements"]]
    found_ranks = [r["delivered_locations"]["complete_by_rank"] for r in requirements if r["delivered"]]
    complete_ranks = [q["all_evidence_by_rank"] for q in scored if q["complete"]]
    return {"eligible_questions": len(eligible), "scored_questions": len(scored),
            "complete_questions": sum(r["complete"] for r in scored),
            "mean_evidence_coverage": statistics.mean(r["delivered_coverage"] for r in scored) if valid else None,
            "complete_evidence_rate": statistics.mean(r["complete"] for r in scored) if valid else None,
            "mean_retrieved_coverage": statistics.mean(r["retrieved_coverage"] for r in scored) if valid else None,
            "context_chars_mean": statistics.mean(r["context_chars"] for r in scored) if scored else None,
            "scored_requirement_count": len(requirements),
            "found_requirement_count": len(found_ranks),
            "missing_requirement_count": len(requirements) - len(found_ranks),
            "mean_found_evidence_rank": statistics.mean(found_ranks) if valid and found_ranks else None,
            "found_evidence_rank_counts": {str(rank): found_ranks.count(rank) for rank in sorted(set(found_ranks))},
            "mean_all_evidence_rank": statistics.mean(complete_ranks) if valid and complete_ranks else None,
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


def location_summary(locations):
    if locations["complete_by_rank"] is None:
        ranks = ", ".join(map(str, locations["contributing_chunk_ranks"]))
        return f"nepotpun (delovi: {ranks})" if ranks else "nije pronađen"
    if locations["full_chunk_ranks"]:
        details = "ceo u: " + ", ".join(map(str, locations["full_chunk_ranks"]))
        if len(locations["supporting_chunk_ranks"]) > 1:
            details += "; ranije zajedno: " + " + ".join(map(str, locations["supporting_chunk_ranks"]))
    else:
        details = "zajedno: " + " + ".join(map(str, locations["supporting_chunk_ranks"]))
    return f"{details}; potpun do #{locations['complete_by_rank']}"


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
    lines += ["", "## Prosečne pozicije dostavljenih dokaza (answer pitanja)", "",
              "Prosek dokaza računa se samo preko potpuno pronađenih jedinica, svaka jednom. "
              "Za dokaz raspoređen u chunkovima 2 i 4 računa se 4; duplikati ne dodaju uzorke. "
              "Niži prosek znači raniji dolazak pronađenih dokaza, ali ne dokazuje bolju pretragu "
              "ako je mnogo drugih dokaza izostalo. Zato ga čitajte uz coverage i complete rate.", "",
              "Prosek za sve dokaze računa se samo preko potpuno pokrivenih pitanja: "
              "do koje pozicije treba uzeti rezultate da svi dokazi budu dostupni. "
              "Brojači se odnose na ocenjena pitanja; N/A označava nepotpun skup ili prazan imenilac.", "",
              "| Run | Pronađeni / ocenjeni dokazi | Prosečna pozicija dokaza | Potpuna pitanja | Prosečna pozicija za sve dokaze |",
              "|---|---:|---:|---:|---:|"]
    for run in report["runs"]:
        a = run["answer_questions"]
        found = "N/A" if a["mean_found_evidence_rank"] is None else f"{a['mean_found_evidence_rank']:.3f}"
        complete = "N/A" if a["mean_all_evidence_rank"] is None else f"{a['mean_all_evidence_rank']:.3f}"
        lines.append(f"| {Path(run['run']).name} | {a['found_requirement_count']} / {a['scored_requirement_count']} | "
                     f"{found} | {a['complete_questions']} | {complete} |")
    for run in report["runs"]:
        lines += ["", f"## {Path(run['run']).name}", "",
                  "| Question | Scope | Result | Missing delivered requirements / issue |",
                  "|---|---|---|---|"]
        for q in run["questions"]:
            missing = ", ".join(r["id"] for r in q.get("requirements", []) if not r["delivered"])
            note = q.get("reason", missing).replace("|", "\\|")
            lines.append(f"| {q['question_id']} | {q['scope']} | {q.get('verdict', q['status'])} | {note} |")
        lines += ["", "### Pozicije dokaza u vraćenim chunkovima", "",
                  "Pozicije su 1-based redosled sačuvanih rezultata. Kod hijerarhijskog retrievala "
                  "to je redosled roditeljskih odlomaka posle proširenja i uklanjanja duplikata. "
                  "Kolona 'Poslato LLM-u' računa samo stvarno dostavljeni tekst.", "",
                  "'Ceo u' navodi chunkove koji sami sadrže ceo dokaz. 'Zajedno' navodi jednu "
                  "dovoljnu kombinaciju. 'Potpun do #k' znači da prvih k rezultata zajedno sadrži "
                  "dokaz; ne mora ceo biti u chunku k. 'Nepotpun' ne donosi poene.", "",
                  "| Question | Dokaz | Pre skraćivanja konteksta | Poslato LLM-u |",
                  "|---|---|---|---|"]
        for q in run["questions"]:
            for r in q.get("requirements", []):
                lines.append(f"| {q['question_id']} | {r['id']} | "
                             f"{location_summary(r['retrieved_locations'])} | "
                             f"{location_summary(r['delivered_locations'])} |")
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
