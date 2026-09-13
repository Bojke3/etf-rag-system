"""Offline checks for context delivery, configuration overrides and run recording."""

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
from scripts import collect_benchmark_answers as collector
from src.llm.ollama import OllamaClient
from src.rag import RAGPipeline
from src.retrieval.context import ContextBuilder


class ContextBudgetTests(unittest.TestCase):
    def setUp(self):
        self.docs = [{'document': 'rules', 'chunk_id': i, 'text': f'Rule {i}: ' + 'x' * 1016,
                      'score': 0.9} for i in range(5)]

    def test_expanded_budget_delivers_all_five_chunks(self):
        limited = ContextBuilder.build_context_details(self.docs, 2000)
        expanded = ContextBuilder.build_context_details(self.docs, 8000)
        self.assertTrue(limited['context_truncated'])
        self.assertEqual(limited['chunks_fully_included'], 1)
        self.assertEqual(limited['chunks_partially_included'], 1)
        self.assertEqual(limited['chunks_omitted'], 3)
        self.assertLessEqual(len(limited['context']), 2000)
        self.assertFalse(expanded['context_truncated'])
        self.assertEqual(expanded['chunks_fully_included'], 5)
        self.assertEqual(expanded['context'], '\n\n'.join(d['text'] for d in self.docs))

    def test_separator_boundary_empty_docs_and_invalid_budget(self):
        docs = [{'text': 'a' * 120}, {}, {'text': ''}, {'text': 'b' * 120}]
        exact = ContextBuilder.build_context_details(docs, 242)
        self.assertEqual(len(exact['context']), 242)
        self.assertFalse(exact['context_truncated'])
        shortened = ContextBuilder.build_context_details(docs, 241)
        self.assertEqual(shortened['chunk_usage'][-1]['context_chars_used'], 119)
        self.assertEqual(len(shortened['context']), 241)
        self.assertEqual(ContextBuilder.build_context([], 8000), '')
        with self.assertRaises(ValueError):
            ContextBuilder.build_context(docs, 0)

    def test_recorded_context_and_prompts_match_the_actual_llm_call(self):
        retriever = Mock()
        retriever.retrieve.return_value = self.docs
        client = Mock(last_response_metadata={'prompt_eval_count': 3500, 'eval_count': 25})
        client.generate.return_value = 'Example answer'
        pipeline = RAGPipeline(retriever, client, None, context_max_chars=8000)
        result = pipeline.process_query('What does rule 4 say?', include_diagnostics=True)
        self.assertEqual(result['status'], 'success')
        trace = result['diagnostics']
        self.assertIn(self.docs[-1]['text'], client.generate.call_args.args[0])
        self.assertEqual(trace['user_prompt'], client.generate.call_args.args[0])
        self.assertEqual(trace['system_prompt'], client.generate.call_args.kwargs['system'])
        self.assertEqual(trace['input_chars'], len(trace['user_prompt']) + len(trace['system_prompt']))
        self.assertEqual(trace['generation']['prompt_eval_count'], 3500)
        self.assertEqual(result['sources'][-1]['text'], self.docs[-1]['text'])
        self.assertEqual(result['sources'][-1]['chunk_id'], 4)

    def test_num_ctx_is_sent_to_ollama_and_response_counts_are_recorded(self):
        response = Mock(status_code=200)
        response.json.return_value = {'response': 'Answer', 'done': True,
                                      'prompt_eval_count': 3500, 'eval_count': 30}
        requests = SimpleNamespace(post=Mock(return_value=response))
        client = OllamaClient(num_ctx=8192)
        with patch.dict(sys.modules, {'requests': requests}):
            client.generate('Question', system='System')
            payload = requests.post.call_args.kwargs['json']
            self.assertEqual(payload['options']['num_ctx'], 8192)
            self.assertNotIn('num_ctx', payload)
            self.assertEqual(client.last_response_metadata['prompt_eval_count'], 3500)
            response.status_code = 500
            response.text = 'Failure'
            self.assertEqual(client.generate('Another question'), '')
            self.assertEqual(client.last_response_metadata, {})

    def test_cli_overrides_env_and_records_effective_settings(self):
        cfg = SimpleNamespace(benchmark_execution='local', ollama_base_url='http://localhost:11434',
                              ollama_model='mistral:latest', context_max_chars=4000, ollama_num_ctx=4096,
                              ollama_temperature=0.7, ollama_max_tokens=2048, ollama_top_p=0.9,
                              ollama_think=None)
        for cli_chars, cli_tokens, expected_chars, expected_tokens in [
            (8000, 8192, 8000, 8192), (None, None, 4000, 4096)
        ]:
            args = SimpleNamespace(execution='local', endpoint=None, model='mistral:latest',
                                   timeout=900, context_max_chars=cli_chars, num_ctx=cli_tokens)
            with patch.object(execution, 'list_models', return_value=[{'name': 'mistral:latest', 'digest': 'abc'}]), \
                 patch.object(execution, 'build_local_pipeline') as build, \
                 contextlib.redirect_stdout(io.StringIO()):
                with execution.prepare_execution(args, cfg) as (_, info):
                    self.assertEqual(info['context_max_chars'], expected_chars)
                    self.assertEqual(info['generation_options']['num_ctx'], expected_tokens)
                    self.assertEqual(build.call_args.kwargs, {'context_max_chars': expected_chars, 'num_ctx': expected_tokens})

    def test_invalid_cli_limits_and_unsupported_api_override_fail_before_network(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for flag in ('--context-max-chars', '--num-ctx'):
                with self.assertRaises(SystemExit):
                    collector.parse_args([flag, '0'])
        args = collector.parse_args(['--execution', 'api', '--context-max-chars', '8000'])
        with patch.object(execution, 'urlopen') as network:
            with self.assertRaisesRegex(ValueError, 'require --execution local or ssh'):
                with execution.prepare_execution(args, None):
                    self.fail('Unsupported override should fail')
            network.assert_not_called()

    def test_full_diagnostics_persist_and_changed_limits_cannot_resume(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            root = Path(directory)
            benchmark = root / 'questions.json'
            benchmark.write_text(json.dumps({'questions': [{'id': 'Q1', 'question': 'Question',
                                                           'expected_answer': 'Answer'}]}), encoding='utf-8')
            args = collector.parse_args(['--benchmark', str(benchmark), '--output-dir', str(root / 'runs'),
                                         '--run-id', 'context8k', '--execution', 'local'])
            args.endpoint = 'http://localhost:11434'
            info = {'context_max_chars': 8000, 'generation_options': {'num_ctx': 8192}}
            details = ContextBuilder.build_context_details(self.docs, 8000)
            details['input_chars'] = len(details['context']) + 1000
            query = Mock(return_value={'status': 'success', 'answer': 'Answer',
                                       'sources': self.docs, 'diagnostics': details})
            run = collector.collect_benchmark_answers(args, query_fn=query, backend_info=info)
            row = json.loads((run / 'answers.jsonl').read_text(encoding='utf-8'))
            self.assertEqual(row['diagnostics']['context'], details['context'])
            self.assertEqual(len(row['sources']), 5)
            original = (run / 'answers.jsonl').read_bytes()
            for changed in ({**info, 'context_max_chars': 16000},
                            {**info, 'generation_options': {'num_ctx': 16384}}):
                with self.assertRaisesRegex(ValueError, 'different configuration'):
                    collector.collect_benchmark_answers(args, query_fn=query, backend_info=changed)
            self.assertEqual((run / 'answers.jsonl').read_bytes(), original)
            query.assert_called_once()


if __name__ == '__main__':
    unittest.main()
