"""Resolve curated evidence from a frozen extraction snapshot, never from answers."""

import hashlib
import json
from pathlib import Path

from src.data.stages import file_hash, read_manifest, verified_file

ROOT = Path(__file__).resolve().parents[1]


def select_questions(questions, args):
    path = getattr(args, "diagnostic_contexts", None)
    if not path:
        return (questions[:args.limit] if args.limit is not None else questions), None
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported diagnostic context schema")
    snapshot_dir = ROOT / data["snapshot"]
    if file_hash(snapshot_dir / "manifest.json") != data["snapshot_manifest_sha256"]:
        raise ValueError("Diagnostic snapshot manifest has changed")
    snapshot = read_manifest(snapshot_dir, "extraction")
    documents = {d["document"]: d for d in snapshot["documents"]}
    by_id = {q["id"]: q for q in questions}
    cases = data.get("cases", [])
    if not cases or len({c["question_id"] for c in cases}) != len(cases):
        raise ValueError("Diagnostic cases must be nonempty and have unique question IDs")
    if args.limit is not None:
        cases = cases[:args.limit]
    selected = []
    for case in cases:
        question = by_id.get(case["question_id"])
        if question is None:
            raise ValueError(f"Unknown diagnostic question: {case['question_id']}")
        if case.get("review_status") != "ready":
            raise ValueError(f"Diagnostic evidence is not reviewed: {case['question_id']}")
        question_hash = hashlib.sha256(question["question"].encode("utf-8")).hexdigest()
        if case.get("question_sha256") != question_hash:
            raise ValueError(f"Diagnostic question text has changed: {case['question_id']}")
        passages = []
        for index, passage in enumerate(case.get("passages", [])):
            record = documents[passage["document"]]
            source = verified_file(snapshot_dir, record["cleaned_file"], record["cleaned_sha256"])
            text = source.read_bytes().decode("utf-8")
            start, end = passage["start"], passage["end"]
            if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text)):
                raise ValueError(f"Invalid passage offsets: {case['question_id']}")
            passages.append({"document": passage["document"], "chunk_id": f"curated_{index}",
                             "text": text[start:end], "source_start": start, "source_end": end})
        if not passages and case.get("control") != "empty_context":
            raise ValueError(f"Missing diagnostic passages: {case['question_id']}")
        selected.append({**question, "curated_documents": passages})
    metadata = {"contexts_path": str(path), "contexts_sha256": file_hash(path),
                "snapshot_manifest_sha256": data["snapshot_manifest_sha256"],
                "mode": args.diagnostic_mode, "question_ids": [q["id"] for q in selected]}
    return selected, metadata
