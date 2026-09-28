"""Evidence coverage must not mistake a document hit or clipped rule for proof."""

import copy
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import evaluate_retrieval as ev


def requirement(source, phrase, doc="Rules", name="E01"):
    start = source.index(phrase)
    return {"id": name, "description": "rule", "alternatives": [{"spans": [
        {"document": doc, "start": start, "end": start + len(phrase), "sha256": ev.digest(phrase)}]}]}


def case(reqs, qid="Q1", status="approved", scope="answer"):
    return {"question_id": qid, "expected_behavior": "answer", "scope": scope,
            "review_status": status, "reviewed_by": "test reviewer" if status == "approved" else "",
            "review_note": "test", "requirements": reqs}


def answer(texts, used=None, docs=None):
    used = used if used is not None else [len(t) for t in texts]
    docs = docs or ["Rules"] * len(texts)
    return {"id": "Q1", "question": "Question?", "actual_answer": "irrelevant",
            "sources": [{"document": d, "chunk_id": i, "text": t}
                        for i, (d, t) in enumerate(zip(docs, texts))],
            "diagnostics": {"context": "\n\n".join(t[:u] for t, u in zip(texts, used) if u),
                            "context_mode": "retrieved", "chunk_usage": [
                {"rank": i + 1, "document": d, "chunk_id": i, "text_chars": len(t), "context_chars_used": u}
                for i, (d, t, u) in enumerate(zip(docs, texts, used))]}}


class EvidenceTests(unittest.TestCase):
    def score(self, source, reqs, row):
        return ev.score_case(case(reqs), row, {"rules": ev.normalize(source)}, {"question": "Question?"})

    def test_wrong_passage_in_right_document_is_not_evidence(self):
        source = "Admission: mathematics. Tuition: paid annually."
        result = self.score(source, [requirement(source, "Admission: mathematics.")], answer(["Tuition: paid annually."]))
        self.assertEqual(result["verdict"], "none")

    def test_rule_split_across_overlapping_chunks_is_complete(self):
        source = "Before. Student cannot take exams during leave. After."
        r = requirement(source, "Student cannot take exams during leave.")
        result = self.score(source, [r], answer([source[:32], source[23:]]))
        self.assertTrue(result["complete"])

    def test_rule_split_on_whitespace_is_complete(self):
        source = "Student cannot take exams."
        result = self.score(source, [requirement(source, source)], answer(["Student cannot", "take exams."]))
        self.assertTrue(result["complete"])

    def test_omitted_negation_is_not_covered_by_surrounding_chunks(self):
        source = "Student cannot take exams."
        result = self.score(source, [requirement(source, source)], answer(["Student", "take exams."]))
        self.assertFalse(result["complete"])

    def test_duplicate_chunks_do_not_fill_missing_rule(self):
        source = "Mathematics for SI. Physics for ER."
        reqs = [requirement(source, "Mathematics for SI."), requirement(source, "Physics for ER.", name="E02")]
        result = self.score(source, reqs, answer(["Mathematics for SI."] * 5))
        self.assertEqual(result["delivered_coverage"], 0.5)

    def test_truncated_chunk_counts_only_delivered_prefix(self):
        source = "Rule. Important exception."
        result = self.score(source, [requirement(source, "Important exception.")], answer([source], [5]))
        self.assertEqual(result["retrieved_coverage"], 1)
        self.assertEqual(result["delivered_coverage"], 0)

    def test_omitted_chunk_is_retrieved_but_not_delivered(self):
        source = "First rule. Second rule."
        result = self.score(source, [requirement(source, "Second rule.")], answer(["First rule.", "Second rule."], [11, 0]))
        self.assertEqual(result["retrieved_coverage"], 1)
        self.assertEqual(result["delivered_coverage"], 0)

    def test_whitespace_and_newlines_do_not_change_mapping(self):
        source = "Student cannot take exams."
        result = self.score(source, [requirement(source, source)], answer(["Student\r\n cannot   take exams."]))
        self.assertTrue(result["complete"])

    def test_hierarchical_numeric_usage_matches_serialized_child_id(self):
        row = answer(["Rule."])
        row["sources"][0]["chunk_id"] = "Rules::hierarchical::child::0000"
        result = self.score("Rule.", [requirement("Rule.", "Rule.")], row)
        self.assertTrue(result["complete"])
        self.assertEqual(result["requirements"][0]["delivered_locations"]["full_chunk_ranks"], [1])
        row["sources"][0]["chunk_id"] = "Rules::hierarchical::child::0001"
        self.assertEqual(self.score("Rule.", [requirement("Rule.", "Rule.")], row)["status"], "unscorable")

    def test_rank_five_and_all_evidence_completion_rank(self):
        parts = ["First.", "Second.", "Third.", "Fourth.", "Fifth."]
        source = " ".join(parts)
        reqs = [requirement(source, "Second."), requirement(source, "Fifth.", name="E02")]
        row = answer(parts)
        # IDs are not ranks in the returned list.
        row["sources"][4]["chunk_id"] = 901
        row["diagnostics"]["chunk_usage"][4]["chunk_id"] = 901
        result = self.score(source, reqs, row)
        self.assertEqual(result["all_evidence_by_rank"], 5)
        location = result["requirements"][1]["delivered_locations"]
        self.assertEqual(location["full_chunk_ranks"], [5])
        self.assertEqual(location["supporting_chunk_ranks"], [5])

    def test_split_rule_reports_sufficient_ranks_and_earliest_complete_prefix(self):
        source = "Before. Student cannot take exams during leave. After."
        req = requirement(source, "Student cannot take exams during leave.")
        result = self.score(source, [req], answer([source[:32], "Before.", source[23:], source]))
        loc = result["requirements"][0]["delivered_locations"]
        self.assertEqual(loc["contributing_chunk_ranks"], [1, 3, 4])
        self.assertEqual(loc["supporting_chunk_ranks"], [1, 3])
        self.assertEqual(loc["full_chunk_ranks"], [4])
        self.assertEqual(loc["complete_by_rank"], 3)
        self.assertEqual(result["all_evidence_by_rank"], 3)

    def test_clipped_and_omitted_evidence_keep_retrieved_and_delivered_ranks_separate(self):
        source = "Rule. Important exception."
        result = self.score(source, [requirement(source, "Important exception.")],
                            answer([source, "Important exception."], [5, 0]))
        r = result["requirements"][0]
        self.assertEqual(r["retrieved_locations"]["full_chunk_ranks"], [1, 2])
        self.assertEqual(r["delivered_locations"]["contributing_chunk_ranks"], [])
        self.assertIsNone(r["delivered_locations"]["complete_by_rank"])
        self.assertIsNone(result["all_evidence_by_rank"])

    def test_incomplete_alternatives_cannot_be_combined_into_false_complete_rank(self):
        source = "One. Two. Three. Four."
        req = requirement(source, "One.")
        req["alternatives"][0]["spans"] += requirement(source, "Two.")["alternatives"][0]["spans"]
        alt = requirement(source, "Three.")["alternatives"][0]
        alt["spans"] += requirement(source, "Four.")["alternatives"][0]["spans"]
        req["alternatives"].append(alt)
        result = self.score(source, [req], answer(["One.", "Three."]))
        loc = result["requirements"][0]["delivered_locations"]
        self.assertEqual(loc["contributing_chunk_ranks"], [1, 2])
        self.assertEqual(loc["supporting_chunk_ranks"], [])
        self.assertIsNone(loc["complete_by_rank"])

    def test_markdown_explains_complete_joint_and_partial_locations(self):
        source = "Student cannot take exams."
        req = requirement(source, source)
        result = self.score(source, [req], answer(["Student cannot", "take exams."]))
        self.assertEqual(ev.location_summary(result["requirements"][0]["delivered_locations"]),
                         "zajedno: 1 + 2; potpun do #2")
        partial = self.score(source, [req], answer(["Student cannot"]))
        self.assertEqual(ev.location_summary(partial["requirements"][0]["delivered_locations"]),
                         "nepotpun (delovi: 1)")
        run = {"run": "example", "preliminary": False, "answer_questions": ev.aggregate([result], "answer"),
               "questions": [result]}
        md = ev.report_markdown({"evidence": "evidence.json", "runs": [run]})
        self.assertIn("| Q1 | E01 | zajedno: 1 + 2; potpun do #2 |", md)

    def test_rank_means_exclude_missing_evidence_and_count_duplicates_once(self):
        source = "One. Two. Three. Four. Missing."
        reqs = [requirement(source, "One."), requirement(source, "Four.", name="E02"),
                requirement(source, "Missing.", name="E03")]
        partial = self.score(source, reqs, answer(["One.", "Two.", "Three.", "Four.", "One."]))
        complete = self.score(source, [requirement(source, "One.")], answer(["Two.", "One."]))
        a = ev.aggregate([partial, complete], "answer")
        self.assertEqual(a["scored_requirement_count"], 4)
        self.assertEqual(a["found_requirement_count"], 3)
        self.assertEqual(a["missing_requirement_count"], 1)
        self.assertAlmostEqual(a["mean_found_evidence_rank"], (1+4+2)/3)
        self.assertEqual(a["found_evidence_rank_counts"], {"1": 1, "2": 1, "4": 1})
        self.assertEqual(a["mean_all_evidence_rank"], 2)
        self.assertEqual(a["complete_questions"], 1)

    def test_rank_means_are_null_for_no_matches_or_unscored_questions(self):
        source = "Found. Missing."
        absent = self.score(source, [requirement(source, "Missing.")], answer(["Found."]))
        a = ev.aggregate([absent], "answer")
        self.assertIsNone(a["mean_found_evidence_rank"])
        self.assertIsNone(a["mean_all_evidence_rank"])
        self.assertEqual(a["found_evidence_rank_counts"], {})
        found = self.score(source, [requirement(source, "Found.")], answer(["Found."]))
        a = ev.aggregate([found, {"scope": "answer", "status": "missing_run_question"}], "answer")
        self.assertIsNone(a["mean_found_evidence_rank"])
        self.assertIsNone(a["mean_all_evidence_rank"])

    def test_identical_text_in_wrong_document_is_not_a_match(self):
        source = "Student cannot take exams."
        result = ev.score_case(case([requirement(source, source)]), answer([source], docs=["Other"]),
                               {"rules": source, "other": source}, {"question": "Question?"})
        self.assertFalse(result["complete"])

    def test_one_alternative_suffices_but_all_its_spans_are_required(self):
        source = "First. Second. Alternative."
        req = requirement(source, "First.")
        req["alternatives"][0]["spans"] += requirement(source, "Second.")["alternatives"][0]["spans"]
        req["alternatives"] += requirement(source, "Alternative.")["alternatives"]
        self.assertFalse(self.score(source, [req], answer(["First."]))["complete"])
        self.assertTrue(self.score(source, [req], answer(["Alternative."]))["complete"])

    def test_repeated_source_text_is_unscorable_not_guessed(self):
        source = "Rule. Rule."
        self.assertEqual(self.score(source, [requirement(source, "Rule.")], answer(["Rule."]))["status"], "unscorable")

    def test_missing_or_inconsistent_context_does_not_receive_zero(self):
        for mutate in (lambda r: r.pop("diagnostics"),
                       lambda r: r["diagnostics"].update(context="different"),
                       lambda r: r["diagnostics"].update(context_mode="curated")):
            row = answer(["Rule."])
            mutate(row)
            self.assertEqual(self.score("Rule.", [requirement("Rule.", "Rule.")], row)["status"], "unscorable")

    def test_answer_quality_and_generation_failure_do_not_change_retrieval_score(self):
        row = answer(["Rule."])
        reqs = [requirement("Rule.", "Rule.")]
        before = self.score("Rule.", reqs, row)
        row.update(actual_answer="wrong", status="error", error="generation timed out")
        self.assertEqual(before, self.score("Rule.", reqs, row))

    def test_missing_question_does_not_inflate_aggregate(self):
        scored = self.score("Rule.", [requirement("Rule.", "Rule.")], answer(["Rule."]))
        result = ev.aggregate([scored, {"scope": "answer", "status": "missing_run_question"}], "answer")
        self.assertEqual(result["complete_questions"], 1)
        self.assertIsNone(result["complete_evidence_rate"])

    def test_draft_requires_opt_in_and_latest_attempt_wins(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            first = answer(["Rule."])
            last = {"id": "Q1", "question": "Question?"}
            (root/"answers.jsonl").write_text(json.dumps(first)+"\n"+json.dumps(last), encoding="utf-8")
            data = {"cases": [case([requirement("Rule.", "Rule.")], status="draft")]}
            with patch.object(ev, "ROOT", root):
                args = root, data, {"rules": "Rule."}, {"Q1": {"question": "Question?"}}
                self.assertEqual(ev.evaluate_run(*args)["questions"][0]["status"], "needs_review")
                result = ev.evaluate_run(*args, allow_draft=True)
                self.assertEqual(result["questions"][0]["status"], "unscorable")
                self.assertTrue(result["preliminary"])

    def test_repository_annotations_validate_against_frozen_sources(self):
        data, documents, questions = ev.load_evidence(ev.ROOT/ev.DEFAULT_EVIDENCE)
        self.assertEqual(len(questions), 60)
        self.assertEqual(sum(c["scope"] == "answer" for c in data["cases"]), 52)

    def test_reject_changed_sources_benchmark_or_span(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            b = {"questions": [{"id": "Q1", "question": "Question?", "expected_behavior": "answer"}]}
            (root/"benchmark.json").write_text(json.dumps(b), encoding="utf-8")
            (root/"source.txt").write_text("Rule.\r\n", encoding="utf-8")
            evidence = {"schema_version": 1, "normalization": "whitespace_v1", "benchmark": "benchmark.json",
                        "benchmark_sha256": ev.object_hash(b), "documents": [
                            {"document": "Rules", "path": "source.txt", "normalized_sha256": ev.digest("Rule.")}],
                        "cases": [case([requirement("Rule.", "Rule.")])]}
            path = root/"evidence.json"
            with patch.object(ev, "ROOT", root):
                path.write_text(json.dumps(evidence), encoding="utf-8")
                ev.load_evidence(path)
                for key in ("source", "benchmark", "span", "reviewer"):
                    changed = copy.deepcopy(evidence)
                    if key == "source": changed["documents"][0]["normalized_sha256"] = "bad"
                    if key == "benchmark": changed["benchmark_sha256"] = "bad"
                    if key == "span": changed["cases"][0]["requirements"][0]["alternatives"][0]["spans"][0]["sha256"] = "bad"
                    if key == "reviewer": changed["cases"][0]["reviewed_by"] = ""
                    path.write_text(json.dumps(changed), encoding="utf-8")
                    with self.assertRaises(ValueError): ev.load_evidence(path)


if __name__ == "__main__":
    unittest.main()
