"""Offline checks: curated evidence, fixed judge identity and metric failures."""

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts import collect_benchmark_answers as collector
from scripts import score_benchmark_run as scorer
from scripts.benchmark_execution import build_local_pipeline
from scripts.diagnostic_benchmark import select_questions
from scripts.judge_execution import DEFAULT_PROFILE, load_profile, prepare_judge, verify_model, verify_generator_separation
from src.data.stages import extract_documents, file_hash
from src.evaluation.bertscore import BERTScoreMetric
from src.evaluation.llm_judge import LLMJudgeMetric
from src.evaluation.rouge import ROUGEMetric
from src.llm import OllamaClient
from src.rag import RAGPipeline


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root / "documents"
        source.mkdir()
        (source / "rules.txt").write_text("A topic may be changed only once.", encoding="utf-8")
        snapshot = self.root / "snapshot"
        extract_documents(source, snapshot, enable_ocr=False)
        self.question = {"id": "Q1", "question": "Can I change it a second time?",
                         "expected_answer": "GOLD ANSWER MUST NOT BE SENT", "required_facts": ["Only once"]}
        self.benchmark = self.root / "questions.json"
        self.benchmark.write_text(json.dumps({"questions": [self.question]}), encoding="utf-8")
        self.contexts = self.root / "contexts.json"
        self.data = {"schema_version": 1, "snapshot": str(snapshot),
                     "snapshot_manifest_sha256": file_hash(snapshot / "manifest.json"),
                     "cases": [{"question_id": "Q1", "review_status": "ready",
                                "question_sha256": hashlib.sha256(self.question["question"].encode()).hexdigest(),
                                "passages": [{"document": "rules", "start": 0, "end": 32}]}]}
        self.save()
        self.args = collector.parse_args(["--execution", "local", "--benchmark", str(self.benchmark),
                                         "--diagnostic-contexts", str(self.contexts), "--run-id", "diag",
                                         "--output-dir", str(self.root / "runs")])
        self.metadata = {"execution": "local", "model": "test"}

    def save(self):
        self.contexts.write_text(json.dumps(self.data), encoding="utf-8")

    def test_curated_context_bypasses_retrieval_and_never_sends_gold(self):
        questions, _ = select_questions([self.question], self.args)
        retriever = Mock()
        client = Mock(last_response_metadata={}, generate=Mock(return_value="No"))
        pipeline = RAGPipeline(retriever, client, None)
        result = pipeline.process_query(questions[0]["question"],
                                        context_documents=questions[0]["curated_documents"], include_diagnostics=True)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["diagnostics"]["context_mode"], "curated")
        retriever.retrieve.assert_not_called()
        prompt = client.generate.call_args.args[0]
        self.assertIn("only once", prompt)
        self.assertNotIn(self.question["expected_answer"], prompt)

    def test_collection_separates_modes_and_blocks_mixed_resume(self):
        query = Mock(return_value={"status": "success", "answer": "No"})
        with contextlib.redirect_stdout(io.StringIO()):
            run = collector.collect_benchmark_answers(self.args, query_fn=query, backend_info=self.metadata)
            self.assertIn("context_documents", query.call_args.kwargs)
            self.args.diagnostic_mode = "retrieved"
            with self.assertRaisesRegex(ValueError, "diagnostic_config"):
                collector.collect_benchmark_answers(self.args, query_fn=query, backend_info=self.metadata)
            self.args.run_id = "normal"
            collector.collect_benchmark_answers(self.args, query_fn=query, backend_info=self.metadata)
            self.assertNotIn("context_documents", query.call_args.kwargs)
        row = json.loads((run / "answers.jsonl").read_text(encoding="utf-8"))
        self.assertEqual(row["required_facts"], ["Only once"])

    def test_pending_changed_questions_and_invalid_offsets_fail(self):
        self.data["cases"][0]["review_status"] = "pending"
        self.save()
        with self.assertRaisesRegex(ValueError, "not reviewed"):
            select_questions([self.question], self.args)
        self.data["cases"][0]["review_status"] = "ready"
        self.save()
        with self.assertRaisesRegex(ValueError, "question text has changed"):
            select_questions([{**self.question, "question": "different"}], self.args)
        self.data["cases"][0]["passages"][0]["end"] = 10000
        self.save()
        with self.assertRaisesRegex(ValueError, "Invalid passage offsets"):
            select_questions([self.question], self.args)

    def test_truncated_curated_input_fails_before_generation_but_empty_control_works(self):
        client = Mock(last_response_metadata={}, generate=Mock(return_value="Unknown"))
        pipeline = RAGPipeline(None, client, None, context_max_chars=100)
        result = pipeline.process_query("Q", context_documents=[{"text": "x" * 200}])
        self.assertEqual(result["status"], "error")
        client.generate.assert_not_called()
        self.assertEqual(pipeline.process_query("Q", context_documents=[])["status"], "success")

    def test_curated_pipeline_does_not_load_embedding_or_index(self):
        config = SimpleNamespace(ollama_temperature=0, ollama_max_tokens=256, ollama_top_p=.9, ollama_think=None)
        with patch.dict("sys.modules", {"src.embedding": None}):
            pipeline = build_local_pipeline(config, "http://localhost", "test", 5, retrieval_enabled=False)
        self.assertIsNone(pipeline.retriever)


class EvaluationTests(unittest.TestCase):
    def judge(self, response):
        client = Mock(last_response_metadata={}, generate=Mock(return_value=response))
        return LLMJudgeMetric(client)

    def test_judge_requires_a_single_valid_number(self):
        for response in ("81 points means grade 9. Score 5", "10", "5.9", "", "Score: 4"):
            result = self.judge(response).calculate_details("R", "C", "Q")
            self.assertIsNone(result["score"])
            self.assertIn("error", result)
        self.assertEqual(self.judge("0").calculate("R", "C"), 0)
        self.assertEqual(self.judge(" 4.5 ").calculate("R", "C"), 4.5)

    def test_judge_reads_the_verdict_line_after_its_reasoning(self):
        reasoned = "Odgovor ne iznosi obavezne cinjenice.\nOCENA: 1"
        self.assertEqual(self.judge(reasoned).calculate("R", "C"), 1)
        # A judge that restates its verdict is taken at its last word.
        self.assertEqual(self.judge("OCENA: 2\nispravka\nOCENA: 4.5").calculate("R", "C"), 4.5)
        for response in ("OCENA: 9", "Obrazlozenje bez ocene.", "OCENA: nema"):
            result = self.judge(response).calculate_details("R", "C", "Q")
            self.assertIsNone(result["score"])
            self.assertIn("error", result)

    def test_judge_failure_is_not_scored_zero_or_composited(self):
        instances = {"llm_judge": self.judge("not a score"),
                     "rouge": Mock(calculate=Mock(return_value={"rougeL": 1.0})),
                     "bertscore": Mock(calculate=Mock(return_value={"f1": 1.0}))}
        answer = {"status": "success", "expected_answer": "R", "actual_answer": "C", "question": "Q"}
        scores = scorer.calculate_metrics(answer, list(instances), instances)
        self.assertNotIn("composite", scores)
        summary = scorer.summarize_scores([{**answer, "scores": scores}], list(instances))
        self.assertIsNone(summary["metric_averages"]["llm_judge"])
        self.assertEqual(summary["metric_error_counts"]["llm_judge"], 1)

    def test_fixed_judge_digest_and_model_override_checked_before_generation(self):
        profile = load_profile(DEFAULT_PROFILE)
        with self.assertRaisesRegex(ValueError, "digest differs"):
            verify_model(profile, [{"name": profile["model"], "digest": "wrong"}])
        args = SimpleNamespace(judge_model="different")
        with patch("scripts.judge_execution.list_models") as models:
            with self.assertRaisesRegex(ValueError, "must match"):
                with prepare_judge(args, None):
                    pass
            models.assert_not_called()

    def test_judge_uses_own_profile_even_when_generator_is_different(self):
        profile = load_profile(DEFAULT_PROFILE)
        args = SimpleNamespace(judge_execution="local", judge_timeout=5)
        config = SimpleNamespace(ollama_model="different-generator", ollama_base_url="http://localhost")
        models = [{"name": profile["model"], "digest": profile["digest_prefix"] + "0" * 52}]
        with patch("scripts.judge_execution.list_models", return_value=models):
            with prepare_judge(args, config):
                self.assertEqual(args.judge_client.model, profile["model"])
                self.assertEqual(args.judge_client.temperature, 0)
                self.assertEqual(args.judge_client.seed, 42)

    def test_judge_cannot_grade_itself_or_an_alias_with_the_same_weights(self):
        profile = load_profile(DEFAULT_PROFILE)
        for record in ({"model": profile["model"]}, {"model": "llama4"},
                       {"model": "alias", "model_digest": profile["digest_prefix"] + "0" * 52}):
            with self.assertRaisesRegex(ValueError, "own generated answers"):
                verify_generator_separation(profile, [record])
        verify_generator_separation(profile, [{"model": "mistral-large:latest"}])

    def test_model_facing_judge_prompt_is_serbian_and_hides_generator_identity(self):
        metric = self.judge("5")
        result = metric.calculate_details("Referenca", "Odgovor", "Pitanje?", expected_behavior="abstain",
                                          required_facts=["Pravilo"], generator_model="secret-model-name")
        prompt = result["prompt"]
        self.assertIn("Referentni odgovor", prompt)
        self.assertIn("Navedi da nema dovoljno informacija", prompt)
        self.assertNotIn("secret-model-name", prompt)
        self.assertIn("Ti ocenjuješ", metric.llm_client.generate.call_args.kwargs["system"])

    def test_seed_is_actually_sent(self):
        response = Mock(status_code=200)
        response.json.return_value = {"response": "5"}
        requests = SimpleNamespace(post=Mock(return_value=response))
        with patch.dict("sys.modules", {"requests": requests}):
            OllamaClient(seed=42).generate("Q")
        self.assertEqual(requests.post.call_args.kwargs["json"]["options"]["seed"], 42)

    def test_scoring_records_fixed_judge_and_preserves_earlier_scores(self):
        profile = load_profile(DEFAULT_PROFILE)
        models = [{"name": profile["model"], "digest": profile["digest_prefix"] + "0" * 52}]
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / "run"
            run.mkdir()
            answer = {"id": "Q1", "question": "Q", "expected_answer": "R", "actual_answer": "C",
                      "required_facts": ["a fact"], "status": "success"}
            (run / "answers.jsonl").write_text(json.dumps(answer) + "\n", encoding="utf-8")
            args = scorer.parse_args(["--run-id", "run", "--output-dir", directory,
                                      "--metrics", "llm_judge", "--judge-execution", "local"])
            with patch("scripts.judge_execution.list_models", return_value=models), \
                 patch.object(OllamaClient, "generate", return_value="5"), \
                 contextlib.redirect_stdout(io.StringIO()):
                first = scorer.score_run(args)
                second = scorer.score_run(args)
            self.assertNotEqual(first, second)
            result = json.loads(first.read_text(encoding="utf-8"))
            self.assertEqual(result["judge"]["model_digest"], models[0]["digest"])
            self.assertEqual(result["summary"]["metric_averages"]["llm_judge"], 5)
            self.assertIn("a fact", result["results"][0]["scores"]["llm_judge"]["prompt"])

    def test_rouge_preserves_cyrillic_and_bertscore_is_multilingual_and_cached(self):
        self.assertEqual(ROUGEMetric().calculate("Оцена девет", "Оцена девет")["rougeL"], 1)
        model = Mock(hash="test-hash", score=Mock(return_value=([1.0], [1.0], [1.0])))
        backend = SimpleNamespace(BERTScorer=Mock(return_value=model))
        with patch.dict("sys.modules", {"bert_score": backend}):
            metric = BERTScoreMetric()
            self.assertEqual(metric.calculate("R", "C")["f1"], 1)
            metric.calculate("R2", "C2")
        backend.BERTScorer.assert_called_once()
        self.assertEqual(backend.BERTScorer.call_args.kwargs["lang"], "sr")
        self.assertEqual(backend.BERTScorer.call_args.kwargs["model_type"], "bert-base-multilingual-cased")


if __name__ == "__main__":
    unittest.main()
