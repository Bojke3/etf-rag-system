"""Offline checks for frozen human grounding forms and exported ratings."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_grounding_annotation as g


class HumanGroundingTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"blind_id": f"{cell * 20 + i:012x}", "cell": f"cell{cell}", "question_id": f"Q{i}",
                         "run": f"run{cell}", "question": "Питање?", "answer": "Pravilo.",
                         "context": "Pravilo. Drugi deo.", "llm_score": 99, "expected_answer": "SECRET"}
                        for cell in range(6) for i in range(20)]
        self.key = g.build_key(self.records)

    def export(self, annotator="A"):
        ids = self.key[annotator.lower() + "_ids"]
        return {"protocol": g.PROTOCOL, "annotator": annotator, "sample_sha256": self.key["sample_sha256"],
                "subset_sha256": g.digest(ids), "grades": {i: {"label": "fully_supported", "note": "", "evidence": "Pravilo."} for i in ids}}

    def test_fixed_overlap_has_five_per_configuration(self):
        self.assertEqual(len(self.key["b_ids"]), 30)
        self.assertEqual({cell: sum(self.key["items"][bid]["cell"] == cell for bid in self.key["b_ids"])
                          for cell in {r["cell"] for r in self.records}}, {f"cell{i}": 5 for i in range(6)})
        self.assertEqual(self.key, g.build_key(list(reversed(self.records))))

    def test_payload_is_blinded_and_order_varies(self):
        a = g.make_payload(self.records, "A", self.key["sample_sha256"], "hash")
        b = g.make_payload(self.records, "B", self.key["sample_sha256"], "hash")
        for row in a["items"]:
            self.assertEqual(set(row), {"blind_id", "question", "answer", "context"})
        self.assertNotEqual([r["blind_id"] for r in a["items"]], [r["blind_id"] for r in b["items"]])

    def test_incomplete_export_cannot_be_reported_as_complete(self):
        data = self.export(); data["grades"].pop(next(iter(data["grades"])))
        with self.assertRaisesRegex(ValueError, "every assigned"):
            g.validate_ratings(data, self.key, self.records, "A")

    def test_wrong_annotator_and_changed_context_rejected(self):
        with self.assertRaisesRegex(ValueError, "wrong protocol"):
            g.validate_ratings(self.export("B"), self.key, self.records, "A")
        changed = copy.deepcopy(self.records); changed[0]["context"] += " Novo pravilo."
        self.assertNotEqual(g.sample_fingerprint(changed), self.key["sample_sha256"])

    def test_nonliteral_evidence_rejected_but_whitespace_allowed(self):
        data = self.export(); bid = next(iter(data["grades"]))
        data["grades"][bid]["evidence"] = "Pravilo. ... deo."
        with self.assertRaisesRegex(ValueError, "exact single excerpt"):
            g.validate_ratings(data, self.key, self.records, "A")
        data["grades"][bid]["evidence"] = "Pravilo.\n Drugi deo."
        self.assertEqual(len(g.validate_ratings(data, self.key, self.records, "A")), 120)

    def test_negative_ratings_require_explanation_not_fabricated_evidence(self):
        data = self.export(); bid = next(iter(data["grades"]))
        data["grades"][bid] = {"label": "unsupported", "note": "", "evidence": ""}
        with self.assertRaisesRegex(ValueError, "Explain"):
            g.validate_ratings(data, self.key, self.records, "A")
        data["grades"][bid]["note"] = "Zakljucak se ne navodi u kontekstu."
        g.validate_ratings(data, self.key, self.records, "A")

    def test_no_claims_separate_from_supported_denominator(self):
        data = self.export(); ids = list(data["grades"])
        data["grades"][ids[0]]["label"] = "no_claims"
        report = g.distributions(data["grades"], self.key)["overall"]
        self.assertEqual(report["counts"]["fully_supported"], 119)
        self.assertEqual(report["answers_with_claims"], 119)
        self.assertEqual(report["fully_supported_fraction_among_answers_with_claims"], 1)

    def test_kappa_and_degenerate_case(self):
        x = ["fully_supported", "unsupported"]
        self.assertEqual(g.kappa(x, x), 1)
        self.assertEqual(g.kappa(x, list(reversed(x))), -1)
        self.assertIsNone(g.kappa(["no_claims"], ["no_claims"]))

    def test_complete_reports_keep_primary_and_independent_overlap_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            g.write(output / "analysis_key_private.json", self.key)
            a, b = self.export(), self.export("B")
            bid = next(iter(b["grades"]))
            b["grades"][bid] = {"label": "unsupported", "note": "Nedostaje dokaz.", "evidence": ""}
            g.write(output / "a.json", a); g.write(output / "b.json", b)
            with patch.object(g, "load_inputs", return_value=(self.records, {})), patch("builtins.print"):
                g.summarize(output, output, output / "a.json", output / "b.json")
            result = g.read(output / "summary.json")
            self.assertEqual(result["primary_distributions"]["overall"]["counts"]["fully_supported"], 120)
            self.assertEqual(result["independent_overlap_agreement"]["n"], 30)
            self.assertEqual(result["independent_overlap_agreement"]["exact_agreement"], 29 / 30)
            self.assertEqual(len(g.read(output / "disagreements.json")), 1)


if __name__ == "__main__":
    unittest.main()
