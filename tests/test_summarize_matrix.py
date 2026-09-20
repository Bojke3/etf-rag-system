"""The matrix summary must not count questions that have no target document."""

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.summarize_matrix import describe, group, normalise_document


def write_run(root, name, rows, label="c101", execution="local"):
    run = Path(root) / name
    run.mkdir(parents=True)
    (run / "run_config.json").write_text(json.dumps({
        "label": label, "top_k": 5,
        "component_config": {"embedding_model": "BAAI/bge-m3"},
        "backend": {"execution": execution, "model": "mistral:latest",
                    "context_max_chars": 22000,
                    "generation_options": {"num_ctx": 16384},
                    "retrieval_provenance": {"embedding_model": "BAAI/bge-m3",
                                             "effective_strategy": "hierarchical"}},
    }), encoding="utf-8")
    (run / "answers.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return run


def answer(qid, behaviour, reference, retrieved, status="success", done_reason="stop"):
    return {"id": qid, "expected_behavior": behaviour, "status": status,
            "reference_sources": [{"document": reference}] if reference else [],
            "sources": [{"document": d} for d in retrieved],
            "diagnostics": {"context_chars": 1000, "context_truncated": False,
                            "generation": {"done_reason": done_reason, "eval_count": 100}}}


class SummariseMatrixTests(unittest.TestCase):
    def test_document_names_match_across_extension_case_and_punctuation(self):
        self.assertEqual(normalise_document("Pravilnik_o_OAS_preciscen_jun_2023.pdf"),
                         normalise_document("pravilnik o oas preciscen jun 2023"))
        self.assertNotEqual(normalise_document("Pravilnik o upisu studenata"),
                            normalise_document("Pravilnik o osnovnim akademskim studijama"))

    def test_only_answer_questions_count_towards_retrieval(self):
        # The abstain question retrieves nothing relevant. Counting it would drag
        # doc-hit down for a question whose correct behaviour is to say "not in the
        # documents" -- the REAL_056 case.
        rows = [answer("Q1", "answer", "Pravilnik.pdf", ["Pravilnik"]),
                answer("Q2", "abstain", "Pravilnik.pdf", ["Nesto drugo"]),
                answer("Q3", "clarify", "Pravilnik.pdf", ["Nesto drugo"])]
        with TemporaryDirectory() as tmp:
            result = describe(write_run(tmp, "run_a", rows))
        self.assertEqual(result["questions_scored"], 1)
        self.assertEqual(result["doc_hit"], 1.0)
        self.assertEqual(result["answers"], 3)

    def test_mrr_follows_the_rank_of_the_reference_document(self):
        rows = [answer("Q1", "answer", "Cilj.pdf", ["A", "B", "Cilj"]),      # rank 3 -> 1/3
                answer("Q2", "answer", "Cilj.pdf", ["Cilj"]),                # rank 1 -> 1
                answer("Q3", "answer", "Cilj.pdf", ["A", "B"])]              # promasaj -> 0
        with TemporaryDirectory() as tmp:
            result = describe(write_run(tmp, "run_a", rows))
        self.assertAlmostEqual(result["doc_hit"], 2 / 3)
        self.assertAlmostEqual(result["mrr"], (1 / 3 + 1 + 0) / 3)

    def test_identical_repetitions_report_no_retrieval_spread(self):
        rows = [answer("Q1", "answer", "Cilj.pdf", ["Cilj"])]
        with TemporaryDirectory() as tmp:
            a = describe(write_run(tmp, "run_a", rows))
            b = describe(write_run(tmp, "run_b", rows))
        summary = group([a, b])[0]
        self.assertEqual(summary["runs"], 2)
        self.assertFalse(summary["retrieval_varies"])

    def test_differing_repetitions_are_flagged_because_retrieval_is_deterministic(self):
        hit = [answer("Q1", "answer", "Cilj.pdf", ["Cilj"])]
        miss = [answer("Q1", "answer", "Cilj.pdf", ["Drugo"])]
        with TemporaryDirectory() as tmp:
            a = describe(write_run(tmp, "run_a", hit))
            b = describe(write_run(tmp, "run_b", miss))
        summary = group([a, b])[0]
        self.assertTrue(summary["retrieval_varies"],
                        "same index and questions must give the same passages every time")

    def test_counters_separate_errors_truncation_and_cut_answers(self):
        rows = [answer("Q1", "answer", "Cilj.pdf", ["Cilj"]),
                answer("Q2", "answer", "Cilj.pdf", [], status="error", done_reason=None),
                answer("Q3", "answer", "Cilj.pdf", ["Cilj"], done_reason="length")]
        with TemporaryDirectory() as tmp:
            result = describe(write_run(tmp, "run_a", rows))
        self.assertEqual(result["errors"], 1)
        self.assertEqual(result["cut"], 1)
        self.assertEqual(result["successes"], 2)


if __name__ == "__main__":
    unittest.main()
