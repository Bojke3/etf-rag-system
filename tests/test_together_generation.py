"""Offline Together generation, provenance and resume checks; no paid requests."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts import benchmark_execution as execution
from scripts import benchmark_provenance as provenance
from scripts import collect_benchmark_answers as collector
from src.config import Config
from src.llm.together import TogetherClient
from src.rag import RAGPipeline


MODEL = 'Qwen/Qwen3.5-9B'


def response(content='Odgovor', finish='stop', status=200):
    body = {'id': 'chat-test', 'model': MODEL, 'created': 123,
            'choices': [{'message': {'role': 'assistant', 'content': content,
                                     'reasoning': ''}, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 200, 'completion_tokens': 20, 'total_tokens': 220}}
    return Mock(status_code=status, text=json.dumps(body), headers={'x-request-id': 'req-test'})


class TogetherTests(unittest.TestCase):
    def settings(self):
        return Config(_env_file=None, together_api_key='fake-test-secret',
                      together_model=MODEL, together_temperature=0.7,
                      together_top_p=0.9, together_max_tokens=2048, together_think=False)

    def test_payload_keeps_prompts_and_records_raw_usage_without_credentials(self):
        client = TogetherClient('fake-test-secret', MODEL)
        fake_requests = SimpleNamespace(post=Mock(return_value=response()))
        with patch.dict(sys.modules, {'requests': fake_requests}):
            self.assertEqual(client.generate('Pitanje i kontekst', system='Pravila'), 'Odgovor')
        call = fake_requests.post.call_args
        self.assertEqual(call.args[0], 'https://api.together.ai/v1/chat/completions')
        payload = call.kwargs['json']
        self.assertEqual(payload['messages'], [{'role': 'system', 'content': 'Pravila'},
                                               {'role': 'user', 'content': 'Pitanje i kontekst'}])
        self.assertEqual(payload['reasoning'], {'enabled': False})
        self.assertEqual(payload['max_tokens'], 2048)
        self.assertNotIn('num_ctx', payload)
        trace = client.last_response_metadata
        self.assertEqual(trace['usage']['total_tokens'], 220)
        self.assertEqual(trace['request_id'], 'req-test')
        self.assertEqual(trace['raw_response']['choices'][0]['message']['content'], 'Odgovor')
        self.assertNotIn('fake-test-secret', json.dumps(trace))

    def test_errors_are_redacted_and_empty_answers_are_not_success(self):
        client = TogetherClient('fake-test-secret', MODEL)
        error = Mock(status_code=401, text='bad fake-test-secret', headers={})
        fake_requests = SimpleNamespace(post=Mock(return_value=error))
        with patch.dict(sys.modules, {'requests': fake_requests}):
            with self.assertRaisesRegex(RuntimeError, '401') as caught:
                client.generate('q')
            self.assertNotIn('fake-test-secret', str(caught.exception))
            self.assertNotIn('fake-test-secret', json.dumps(client.last_response_metadata))
            fake_requests.post.return_value = response(content=None, finish='length')
            with self.assertRaisesRegex(RuntimeError, 'no final answer'):
                client.generate('q')
            self.assertEqual(client.last_response_metadata['finish_reason'], 'length')
            self.assertNotIn('error_body', client.last_response_metadata)

    def test_missing_key_and_ollama_window_fail_before_loading_or_requesting(self):
        with self.assertRaisesRegex(ValueError, 'TOGETHER_API_KEY'):
            TogetherClient('', MODEL)
        args = collector.parse_args(['--execution', 'together', '--num-ctx', '16384'])
        with patch.object(execution, 'build_local_pipeline') as build:
            with self.assertRaisesRegex(ValueError, 'Ollama setting'):
                with execution.prepare_execution(args, self.settings()):
                    self.fail('Should reject num_ctx')
            build.assert_not_called()

    def test_generation_failure_preserves_context_sources_and_provider_trace(self):
        client = TogetherClient('fake-test-secret', MODEL)
        docs = [{'document': 'rules', 'chunk_id': 1, 'text': 'Samo jednom.', 'score': 1.0}]
        pipeline = RAGPipeline(Mock(retrieve=Mock(return_value=docs)), client, None)
        fake_requests = SimpleNamespace(post=Mock(return_value=Mock(status_code=429, text='rate limit', headers={})))
        with patch.dict(sys.modules, {'requests': fake_requests}):
            result = pipeline.process_query('Koliko puta?', include_diagnostics=True)
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['sources'][0]['text'], 'Samo jednom.')
        self.assertIn('Samo jednom.', result['diagnostics']['user_prompt'])
        self.assertEqual(result['diagnostics']['generation']['http_status'], 429)

    def test_hosted_collection_resume_and_parameter_guard(self):
        settings = self.settings()
        docs = [{'document': 'rules', 'chunk_id': 1, 'text': 'Samo jednom.', 'score': 1.0}]
        def build(*args, **kwargs):
            pipeline = RAGPipeline(Mock(retrieve=Mock(return_value=docs)), kwargs['llm_client'], None,
                                   context_max_chars=kwargs['context_max_chars'])
            pipeline.collection_provenance = {}
            return pipeline
        fake_requests = SimpleNamespace(post=Mock(return_value=response()))
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            benchmark = root / 'questions.json'
            benchmark.write_text(json.dumps({'questions': [
                {'id': 'Q1', 'question': 'Koliko puta?', 'expected_answer': 'Jednom.'}]}), encoding='utf-8')
            argv = ['--execution', 'together', '--model', MODEL, '--benchmark', str(benchmark),
                    '--output-dir', str(root), '--run-id', 'api-run', '--context-max-chars', '22000']
            with patch.object(execution, 'build_local_pipeline', side_effect=build), \
                 patch.object(execution, 'list_models', side_effect=AssertionError('No Ollama calls')), \
                 patch.object(provenance, 'runtime_record', return_value={}), \
                 patch.object(collector, 'config', settings), \
                 patch.dict(sys.modules, {'requests': fake_requests}):
                def collect(cfg):
                    args = collector.parse_args(argv)
                    with execution.prepare_execution(args, cfg) as (query, metadata):
                        return collector.collect_benchmark_answers(args, query_fn=query, backend_info=metadata)
                run = collect(settings)
                collect(settings)
                self.assertEqual(fake_requests.post.call_count, 1)
                record = json.loads((run / 'answers.jsonl').read_text(encoding='utf-8'))
                self.assertEqual(record['config']['provider'], 'together')
                self.assertEqual(record['diagnostics']['generation']['usage']['total_tokens'], 220)
                self.assertIsNone(record['config']['model_digest'])
                self.assertEqual(record['config']['published_model_info']['quantization'], 'FP8')
                self.assertNotIn('fake-test-secret', (run / 'run_config.json').read_text())
                with self.assertRaisesRegex(ValueError, 'different configuration'):
                    collect(settings.model_copy(update={'together_think': True}))
                self.assertEqual(fake_requests.post.call_count, 1)

    def test_repeat_restores_hosted_settings_without_claiming_weight_verification(self):
        original = {'backend': {'execution': 'together', 'provider': 'together', 'model': MODEL,
                               'context_max_chars': 22000, 'generation_options': {
                                   'temperature': 0.7, 'top_p': 0.9, 'max_tokens': 2048,
                                   'reasoning': {'enabled': False}}},
                    'component_config': {'embedding_model': 'BAAI/bge-m3', 'embedding_device': 'cpu',
                                         'chunk_size': 1024, 'chunk_overlap': 150, 'retrieval_threshold': 0.0},
                    'top_k': 5, 'prompt_strategy': 'zero_shot', 'timeout': 900}
        args = collector.parse_args(['--repeat-from', 'reference', '--run-id', 'next-run'])
        paths = {'benchmark.json': Path('questions.json'), 'vectorstore/index.faiss': Path('index/index.faiss')}
        with patch.object(provenance, 'validate_inputs', return_value=paths), \
             patch.object(provenance, 'read_json', return_value=original), \
             contextlib.redirect_stdout(io.StringIO()):
            settings = provenance.apply_repeat_settings(args, self.settings())
        self.assertEqual(args.execution, 'together')
        self.assertIsNone(args.num_ctx)
        self.assertIsNone(args.expected_model_digest)
        self.assertEqual(settings.embedding_model, 'BAAI/bge-m3')
        self.assertEqual(settings.together_temperature, 0.7)
        self.assertFalse(settings.together_think)


if __name__ == '__main__':
    unittest.main()
