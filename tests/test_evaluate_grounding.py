"""Offline tests: all API traffic goes to a loopback mock, never a real provider."""
import contextlib
import hashlib
import http.server
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from scripts import evaluate_grounding as g


RECORD = {"question": "Imam 42 poena. Koliki je rok?", "answer": "Rok je 30 dana.", "context": "Pravilo: Rok je 30 dana."}


def verdict(label="supported", quote="Rok je 30 dana."):
    return {"answer_kind": "substantive", "coverage_complete": True, "coverage_note": "Proveren ceo odgovor.",
            "claims": [{"claim": "Rok je 30 dana.", "answer_quote": "Rok je 30 dana.", "label": label,
                        "context_quotes": [quote] if label != "unsupported" else [], "question_quotes": [], "reason": "Podrska u dostavljenom pasusu."}]}


class ValidationTests(unittest.TestCase):
    def test_supported(self):
        m = g.validate_verdict(verdict(), RECORD)
        self.assertEqual(m["faithfulness"], 1)
        self.assertEqual(m["supported_count"], 1)

    def test_unsupported_is_zero_not_error(self):
        self.assertEqual(g.validate_verdict(verdict("unsupported"), RECORD)["faithfulness"], 0)

    def test_contradiction_count(self):
        m = g.validate_verdict(verdict("contradicted"), RECORD)
        self.assertEqual(m["contradiction_fraction"], 1)
        self.assertEqual(m["faithfulness"], 0)

    def test_fabricated_quote_rejected(self):
        with self.assertRaisesRegex(ValueError, "nonliteral"):
            g.validate_verdict(verdict(quote="Rok je 15 dana."), RECORD)

    def test_answer_quote_rejected(self):
        v = verdict(); v["claims"][0]["answer_quote"] = "Ne postoji rok."
        with self.assertRaisesRegex(ValueError, "answer_quote"):
            g.validate_verdict(v, RECORD)

    def test_supported_needs_context(self):
        v = verdict(); v["claims"][0]["context_quotes"] = []
        with self.assertRaisesRegex(ValueError, "context evidence"):
            g.validate_verdict(v, RECORD)

    def test_no_claims_is_na(self):
        v = {"answer_kind": "abstention", "coverage_complete": True, "coverage_note": "Samo uzdrzavanje.", "claims": []}
        m = g.validate_verdict(v, RECORD)
        self.assertEqual(m["status"], "no_claims")
        self.assertIsNone(m["faithfulness"])

    def test_substantive_empty_rejected(self):
        v = verdict(); v["claims"] = []
        with self.assertRaisesRegex(ValueError, "zero"):
            g.validate_verdict(v, RECORD)

    def test_partial_coverage_rejected(self):
        v = verdict(); v["coverage_complete"] = False
        with self.assertRaisesRegex(ValueError, "complete claim extraction"):
            g.validate_verdict(v, RECORD)

    def test_duplicate_claim_rejected(self):
        v = verdict(); v["claims"] *= 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            g.validate_verdict(v, RECORD)

    def test_same_claim_with_different_answer_excerpt_rejected(self):
        v = verdict()
        repeated = dict(v["claims"][0], claim="ROK JE 30 DANA.", answer_quote="Rok je 30 dana")
        v["claims"].append(repeated)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            g.validate_verdict(v, RECORD)

    def test_opposing_claims_are_not_merged(self):
        record = {**RECORD, "answer": "Rok je 30 dana. Rok nije 30 dana."}
        v = verdict()
        v["claims"].append(dict(v["claims"][0], claim="Rok nije 30 dana.",
                                answer_quote="Rok nije 30 dana.", label="contradicted"))
        metrics = g.validate_verdict(v, record)
        self.assertEqual(metrics["claim_count"], 2)
        self.assertEqual(metrics["faithfulness"], .5)

    def test_whitespace_normalization(self):
        v = verdict(); v["claims"][0]["context_quotes"] = ["Rok\nje 30    dana."]
        self.assertEqual(g.validate_verdict(v, RECORD)["faithfulness"], 1)

    def test_question_quote_must_be_literal(self):
        v = verdict(); v["claims"][0]["question_quotes"] = ["Imam 100 poena."]
        with self.assertRaisesRegex(ValueError, "question_quotes"):
            g.validate_verdict(v, RECORD)

    def test_strict_json(self):
        self.assertEqual(g.strict_json("```json\n{\"a\": 1}\n```"), {"a": 1})
        for text in ['{"a":1,"a":2}', '{"a":NaN}', '{} trailing']:
            with self.assertRaises(ValueError):
                g.strict_json(text)

    def test_no_old_judge_or_reference_in_request(self):
        record = {**RECORD, "expected_answer": "SECRET_REFERENCE", "llm_score": 5, "cell": "MODEL_LABEL", "expected_behavior": "clarify"}
        body = g.request_body(record, "test", 4096, None)
        text = body["messages"][0]["content"]
        self.assertNotIn("SECRET_REFERENCE", text)
        self.assertNotIn("MODEL_LABEL", text)
        self.assertNotIn("expected_behavior", text)
        self.assertNotIn("temperature", body)

    def test_endpoint_security(self):
        self.assertEqual(g.endpoint_from_base("https://api.anthropic.com/v1"), "https://api.anthropic.com/v1/messages")
        for base in ["http://example.org", "https://key@host", "https://host?key=secret"]:
            with self.assertRaises(ValueError):
                g.endpoint_from_base(base)

    def test_nonclaims_and_errors_excluded(self):
        records = [{"blind_id": "a"}, {"blind_id": "b"}, {"blind_id": "c"}]
        scored = {"status": "ok", "metrics": {"claim_count": 2, "supported_count": 1, "unsupported_count": 1, "contradicted_count": 0, "faithfulness": .5, "all_claims_supported": False}}
        summary = g.aggregate(records, {"a": scored, "b": {"status": "no_claims"}, "c": {"status": "error"}})
        self.assertEqual(summary["macro_faithfulness"], .5)
        self.assertEqual(summary["micro_faithfulness"], .5)
        self.assertEqual(summary["no_claims"], 1)
        self.assertEqual(summary["errors"], 1)


class SourceProtocolTests(unittest.TestCase):
    def setUp(self):
        self.answers = g.source_segments(RECORD["answer"], "A")
        self.contexts = g.source_segments(RECORD["context"], "C")
        self.questions = g.source_segments(RECORD["question"], "Q")
        self.extraction = {"answer_kind": "substantive", "coverage_complete": True, "coverage_note": "Ceo odgovor.",
                           "claims": [{"claim_id": "T1", "claim": "Rok je 30 dana.", "answer_ids": ["A0001"]}]}
        self.verification = {"extraction_ok": True, "extraction_note": "Proveren opseg.",
                             "judgments": [{"claim_id": "T1", "label": "supported", "context_ids": ["C0001"],
                                            "question_ids": ["Q0001"], "reason": "Potvrdjeno."}]}

    def combine(self):
        return g.combine_stages(self.extraction, self.verification, self.answers, self.contexts, self.questions)

    def test_sources_preserve_cyrillic_ocr_and_long_text(self):
        original = "На буџету сам.\nS = N x 60\n" + "a" * 1700
        segments = g.source_segments(original, "C")
        self.assertTrue(all(part in original for part in segments.values()))
        self.assertEqual("".join("".join(segments.values()).split()), "".join(original.split()))

    def test_citations_are_reconstructed_from_source(self):
        result = self.combine()
        self.assertEqual(result["claims"][0]["context_quotes"], [RECORD["context"]])
        self.assertEqual(g.validate_verdict(result, RECORD)["faithfulness"], 1)

    def test_unknown_answer_id_rejected(self):
        self.extraction["claims"][0]["answer_ids"] = ["A9999"]
        with self.assertRaisesRegex(ValueError, "source IDs"):
            g.validate_extraction(self.extraction, self.answers)

    def test_unknown_context_id_rejected(self):
        self.verification["judgments"][0]["context_ids"] = ["C9999"]
        with self.assertRaisesRegex(ValueError, "source IDs"):
            self.combine()

    def test_missing_claim_judgment_rejected(self):
        self.verification["judgments"] = []
        with self.assertRaisesRegex(ValueError, "exactly once"):
            self.combine()

    def test_failed_extraction_audit_has_no_score(self):
        self.verification["extraction_ok"] = False
        self.verification["extraction_note"] = "Missing conclusion."
        with self.assertRaisesRegex(ValueError, "Manual review required"):
            self.combine()

    def test_context_not_sent_to_extraction(self):
        body = g.request_body({**RECORD, "context": "SECRET_CONTEXT"}, "test", 8192, None)
        self.assertNotIn("SECRET_CONTEXT", body["messages"][0]["content"])


class MockHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        server = self.server
        server.calls.append(body)
        mode = server.modes.pop(0) if server.modes else "ok"
        if mode in {"401", "429"}:
            self.send_response(int(mode)); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"type": "error", "error": {"message": "mock error"}}).encode())
            return
        if body["system"] == g.EXTRACT_PROMPT:
            v = {"answer_kind": "substantive", "coverage_complete": True, "coverage_note": "Ceo odgovor.",
                 "claims": [{"claim_id": "T1", "claim": "Rok je 30 dana.", "answer_ids": ["A0001"]}]}
            if mode == "invalid_quote":
                v["claims"][0]["answer_ids"] = ["A9999"]
        else:
            v = {"extraction_ok": True, "extraction_note": "Proverene sve tvrdnje.",
                 "judgments": [{"claim_id": "T1", "label": "supported", "context_ids": ["C0001"],
                                "question_ids": [], "reason": "Direktna podrska."}]}
            if mode == "audit_fail":
                v["extraction_ok"] = False
                v["extraction_note"] = "A material claim was omitted."
        raw = {"type": "message", "id": "msg_mock", "model": body["model"],
               "content": [{"type": "text", "text": json.dumps(v)}],
               "stop_reason": "max_tokens" if mode == "truncated" else "end_turn", "usage": {"input_tokens": 100, "output_tokens": 80}}
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(json.dumps(raw).encode())


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        (self.root / "benchmarking").mkdir()
        g.write_json(self.root / "benchmarking/judge_profile.json", {"model": "test-judge"})
        self.sample = self.root / "sample.json"
        key = {}
        cells = ["Mistral flat", "Mistral hierarchical", "Qwen flat", "Qwen hierarchical", "Llama flat", "Llama hierarchical"]
        for cell_index, cell in enumerate(cells):
            run = f"run_{cell_index}"
            folder = self.root / "benchmarking/runs" / run
            folder.mkdir(parents=True)
            rows = []
            for i in range(20):
                q = f"REAL_{(cell_index*20+i)%60+1:03}"
                blind = hashlib.sha256(f"{run}:{q}".encode()).hexdigest()[:12]
                key[blind] = {"run": run, "question_id": q, "cell": cell, "llm_score": 99}
                behavior = "answer" if i < 17 else ["partial_answer", "abstain", "clarify"][i-17]
                rows.append({"id": q, "status": "success", "question": RECORD["question"], "actual_answer": RECORD["answer"],
                             "expected_answer": "NOT_SENT", "expected_behavior": behavior,
                             "diagnostics": {"context": RECORD["context"], "context_chars": len(RECORD["context"])}})
            (folder / "answers.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        g.write_json(self.sample, key)
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), MockHandler)
        self.server.calls = []; self.server.modes = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.output = Path(self.temp.name) / "results"
        self.base = [sys.executable, str(Path(g.__file__)), "--project-root", str(self.root), "--sample", str(self.sample),
                     "--output-root", str(self.output), "--api-base-url", f"http://127.0.0.1:{self.server.server_port}",
                     "--delay", "0", "--retry-sleep", "0", "--format-retries", "0"]
        self.env = {**os.environ, "ANTHROPIC_API_KEY": "mock-key-never-real", "PYTHONIOENCODING": "utf-8"}
        self.env.pop("GROUNDING_MODEL", None)

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.temp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(self.base + list(args), capture_output=True, text=True, env=self.env, timeout=30)

    def test_pilot_resume_and_protocol_guard(self):
        dry = self.run_cli("--dry-run", "--limit", "10")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertFalse(self.output.exists()); self.assertEqual(len(self.server.calls), 0)
        pilot = self.run_cli("--limit", "10")
        self.assertEqual(pilot.returncode, 0, pilot.stderr)
        self.assertEqual(len(self.server.calls), 20)
        manifest = g.read_json(self.output / "grounding_v3/manifest.json")
        records = g.read_jsonl(self.output / "grounding_v3/inputs.jsonl")
        self.assertEqual(len({r['cell'] for r in records[:10]}), 6)
        self.assertEqual({r['expected_behavior'] for r in records[:10]}, {"answer", "partial_answer", "abstain", "clarify"})
        full = self.run_cli("--limit", "120")
        self.assertEqual(full.returncode, 0, full.stderr)
        self.assertEqual(len(self.server.calls), 240)  # Only 110 new answers, two stages each.
        self.assertEqual(manifest, g.read_json(self.output / "grounding_v3/manifest.json"))
        summary = g.read_json(self.output / "grounding_v3/summary.json")
        self.assertEqual(summary["overall"]["successful_scored"], 120)
        self.assertEqual(summary["overall"]["macro_faithfulness"], 1)
        self.assertEqual(self.run_cli("--limit", "120").returncode, 0)
        self.assertEqual(len(self.server.calls), 240)
        self.assertEqual(self.run_cli("--report-only").returncode, 0)
        self.assertEqual(len(self.server.calls), 240)
        changed = self.run_cli("--limit", "120", "--max-tokens", "4096")
        self.assertNotEqual(changed.returncode, 0); self.assertIn("NEW --run-id", changed.stderr)
        self.assertEqual(len(self.server.calls), 240)
        for request in self.server.calls:
            self.assertNotIn("NOT_SENT", request["messages"][0]["content"])
            self.assertNotIn("llm_score", request["messages"][0]["content"])

    def test_retry_on_rate_limit(self):
        self.server.modes = ["429", "ok"]
        result = self.run_cli("--limit", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.server.calls), 3)
        self.assertEqual(len(list((self.output / "grounding_v3/attempts").glob('*.json'))), 3)

    def test_bad_key_no_retry(self):
        self.server.modes = ["401"]
        result = self.run_cli("--limit", "10")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.server.calls), 1)
        summary = g.read_json(self.output / "grounding_v3/summary.json")["overall"]
        self.assertEqual(summary["errors"], 1); self.assertIsNone(summary["macro_faithfulness"])

    def test_truncated_output_has_no_score_and_can_resume(self):
        self.server.modes = ["truncated"]
        result = self.run_cli("--limit", "1")
        self.assertNotEqual(result.returncode, 0)
        bad = g.read_jsonl(self.output / "grounding_v3/results.jsonl")[0]
        self.assertEqual(bad["status"], "error"); self.assertNotIn("metrics", bad)
        resumed = self.run_cli("--limit", "1")
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        self.assertEqual(len(self.server.calls), 3)
        self.assertEqual(len(g.read_jsonl(self.output / "grounding_v3/results.jsonl")), 2)
        self.assertEqual(g.read_json(self.output / "grounding_v3/summary.json")["overall"]["errors"], 0)

    def test_nonliteral_evidence_is_not_accepted(self):
        self.server.modes = ["invalid_quote"]
        result = self.run_cli("--limit", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source IDs", g.read_jsonl(self.output / "grounding_v3/results.jsonl")[0]["error"])

    def test_changed_inputs_refused_before_next_api_call(self):
        self.assertEqual(self.run_cli("--limit", "1").returncode, 0)
        p = self.root / "benchmarking/runs/run_0/answers.jsonl"
        rows = g.read_jsonl(p); rows[0]["actual_answer"] += " Nova tvrdnja."
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        result = self.run_cli("--limit", "120")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.server.calls), 2)

    def test_missing_exact_context_refused(self):
        p = self.root / "benchmarking/runs/run_0/answers.jsonl"
        rows = g.read_jsonl(p); del rows[0]["diagnostics"]["context"]
        p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        result = self.run_cli("--dry-run")
        self.assertNotEqual(result.returncode, 0); self.assertIn("diagnostics.context missing", result.stderr)
        self.assertEqual(len(self.server.calls), 0)

    def test_invalid_source_id_can_be_repaired_with_bounded_retry(self):
        self.server.modes = ["invalid_quote", "ok", "ok"]
        result = self.run_cli("--limit", "1", "--format-retries", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.server.calls), 3)
        self.assertEqual(len(self.server.calls[1]["messages"]), 3)
        rows = g.read_jsonl(self.output / "grounding_v3/results.jsonl")
        self.assertEqual(rows[-1]["status"], "ok")
        self.assertEqual(len(rows[-1]["raw_attempts"]), 3)

    def test_semantic_audit_failure_is_not_retried_until_it_passes(self):
        self.server.modes = ["ok", "audit_fail"]
        result = self.run_cli("--limit", "1", "--format-retries", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.server.calls), 2)
        row = g.read_jsonl(self.output / "grounding_v3/results.jsonl")[-1]
        self.assertIn("Manual review required", row["error"])
        self.assertNotIn("metrics", row)

    def test_source_id_repair_stops_at_configured_budget(self):
        self.server.modes = ["invalid_quote", "invalid_quote"]
        result = self.run_cli("--limit", "1", "--format-retries", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.server.calls), 2)
        self.assertNotIn("metrics", g.read_jsonl(self.output / "grounding_v3/results.jsonl")[-1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
