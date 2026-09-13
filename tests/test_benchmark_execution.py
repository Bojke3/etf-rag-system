"""Focused tests; run with python -m unittest discover -s tests -p test_benchmark_execution.py."""

import contextlib
import io
import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts import benchmark_execution as execution
from scripts import collect_benchmark_answers as collector
from scripts import score_benchmark_run as scorer
from src.llm.ollama import OllamaClient
from src.llm.ssh_tunnel import SSHTunnel


MODELS = [
    {'name': 'mistral:latest', 'digest': 'sha256:abc', 'details': {'parameter_size': '7B'}},
    {'name': 'qwen3.5:latest', 'digest': 'sha256:def'},
]


class ExecutionTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('pydantic_settings'), 'Project settings package unavailable')
    def test_project_settings_load_and_support_ssh_and_thinking(self):
        from src.config import Config
        self.assertIsNotNone(collector.config)
        settings = Config(_env_file=None, ssh_host='faculty', ssh_port=2222, ollama_think='low')
        self.assertEqual(settings.ssh_port, 2222)
        self.assertEqual(settings.ollama_think, 'low')
        self.assertFalse(Config(_env_file=None, ollama_think='false').ollama_think)

    def test_interactive_mode_and_env_override(self):
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='2'):
            self.assertEqual(execution.choose_execution(None), 'ssh')
        with patch('builtins.input', side_effect=AssertionError('Should not prompt')):
            self.assertEqual(execution.choose_execution(None, 'ssh'), 'ssh')
            self.assertEqual(execution.choose_execution('local', 'ssh'), 'local')
            self.assertEqual(execution.choose_execution(None, endpoint='http://localhost/query'), 'api')

    def test_noninteractive_requires_mode(self):
        with patch('sys.stdin.isatty', return_value=False):
            with self.assertRaisesRegex(ValueError, '--execution'):
                execution.choose_execution(None)
        with self.assertRaisesRegex(ValueError, '--endpoint'):
            execution.choose_execution('ssh', endpoint='http://localhost/query')

    def test_model_selection_is_real_not_a_label(self):
        selected, record = execution.choose_model(MODELS, 'mistral', '')
        self.assertEqual(selected, 'mistral:latest')
        self.assertEqual(record['digest'], 'sha256:abc')
        with self.assertRaisesRegex(ValueError, 'is not installed'):
            execution.choose_model(MODELS, 'not-installed', 'mistral:latest')
        with patch('sys.stdin.isatty', return_value=False):
            with self.assertRaisesRegex(ValueError, 'Default model'):
                execution.choose_model(MODELS, None, 'mistral:7b')
        with patch('sys.stdin.isatty', return_value=True), patch('builtins.input', return_value='2'):
            selected, _ = execution.choose_model(MODELS, None, 'mistral:latest')
        self.assertEqual(selected, 'qwen3.5:latest')

    def test_api_does_not_silently_relabel_another_model(self):
        args = SimpleNamespace(execution='api', endpoint='http://localhost:8000/query', model='qwen3.5:latest')
        with patch.object(execution, 'urlopen', return_value=io.BytesIO(b'{"ollama_model":"mistral:latest"}')):
            with self.assertRaisesRegex(ValueError, 'The API uses'):
                with execution.prepare_execution(args, None):
                    self.fail('Different model should fail')

    def test_direct_mode_runs_local_pipeline_with_selected_server_model(self):
        args = SimpleNamespace(execution='ssh', endpoint=None, model='qwen3.5:latest', timeout=45)
        cfg = SimpleNamespace(benchmark_execution='ask', ollama_base_url='http://localhost:11434',
                              ollama_model='mistral:7b', ssh_host='faculty-alias', ssh_user='student',
                              ssh_port=22, ssh_identity_file='', ssh_local_port=11435,
                              ssh_ollama_host='127.0.0.1', ssh_ollama_port=11434,
                              ssh_startup_timeout=120, ssh_ollama_model='mistral:latest',
                              ollama_temperature=0.1, ollama_max_tokens=2048, ollama_top_p=0.9,
                              ollama_think=False)
        tunnel = Mock(base_url='http://127.0.0.1:11435')
        tunnel.process.poll.return_value = None
        manager = Mock()
        manager.base_url = tunnel.base_url
        manager.__enter__ = Mock(return_value=tunnel)
        manager.__exit__ = Mock(return_value=False)
        pipeline = Mock()
        pipeline.process_query.return_value = {'status': 'success', 'answer': 'Odgovor'}
        with patch.object(execution, 'SSHTunnel', return_value=manager), \
             patch.object(execution, 'list_models', return_value=MODELS), \
             patch.object(execution, 'build_local_pipeline', return_value=pipeline) as build:
            with execution.prepare_execution(args, cfg) as (query, metadata):
                result = query(question='Pitanje', top_k=5, prompt_strategy='zero_shot')
                self.assertEqual(result['answer'], 'Odgovor')
                self.assertEqual(metadata['model_digest'], 'sha256:def')
                self.assertEqual(metadata['generation_options']['num_predict'], 2048)
                build.assert_called_once_with(cfg, tunnel.base_url, 'qwen3.5:latest', 45,
                                              context_max_chars=2000, num_ctx=None)
                pipeline.process_query.assert_called_once_with(question='Pitanje', top_k=5,
                                                               prompt_strategy='zero_shot', include_sources=True,
                                                               include_diagnostics=True)
                tunnel.process.poll.return_value = 1
                with self.assertRaises(ConnectionError):
                    query(question='Pitanje', top_k=5, prompt_strategy='zero_shot')
        manager.__exit__.assert_called_once()

    def test_actual_final_questions_load(self):
        questions = collector.load_benchmark('benchmarking/finalna_pitanja.json')
        self.assertEqual(len(questions), 60)
        self.assertTrue(all(q['sources'] or q['expected_behavior'] == 'abstain' for q in questions))


class TunnelTests(unittest.TestCase):
    def test_command_uses_loopback_no_shell_and_keeps_host_verification(self):
        with patch('shutil.which', return_value='ssh'), patch('sys.stdin.isatty', return_value=False):
            command = SSHTunnel('faculty', user='student', port=2222).command()
        self.assertIn('127.0.0.1:11435:127.0.0.1:11434', command)
        self.assertIn('ExitOnForwardFailure=yes', command)
        self.assertIn('BatchMode=yes', command)
        self.assertNotIn('StrictHostKeyChecking=no', command)
        self.assertEqual(command[-1], 'faculty')
        self.assertEqual(command[command.index('-p') + 1], '2222')

    def test_invalid_hosts_and_ports_rejected(self):
        for host in ('-oProxyCommand=bad', 'faculty; command', '', 'user@host'):
            with self.assertRaises(ValueError):
                SSHTunnel(host)
        with self.assertRaises(ValueError):
            SSHTunnel('faculty', local_port=0)

    def test_busy_port_rejected_before_launching_ssh(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with patch('subprocess.Popen') as launch:
                with self.assertRaisesRegex(RuntimeError, 'already in use'):
                    with SSHTunnel('faculty', local_port=listener.getsockname()[1]):
                        self.fail('Port conflict should fail')
                launch.assert_not_called()

    def test_success_and_user_interrupt_close_owned_process(self):
        process = Mock()
        process.poll.return_value = None
        with patch('src.llm.ssh_tunnel.socket.socket') as sock, \
             patch('src.llm.ssh_tunnel.list_models', return_value=MODELS), \
             patch('subprocess.Popen', return_value=process) as launch, \
             patch.object(SSHTunnel, 'command', return_value=['ssh', 'faculty']):
            with self.assertRaises(KeyboardInterrupt):
                with SSHTunnel('faculty'):
                    raise KeyboardInterrupt()
            launch.assert_called_once_with(['ssh', 'faculty'])
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=5)

    def test_auth_failure_is_not_treated_as_ready(self):
        process = Mock()
        process.poll.return_value = 255
        with patch('src.llm.ssh_tunnel.socket.socket'), \
             patch('subprocess.Popen', return_value=process), \
             patch.object(SSHTunnel, 'command', return_value=['ssh', 'faculty']), \
             patch('src.llm.ssh_tunnel.list_models') as models:
            with self.assertRaisesRegex(RuntimeError, 'SSH connection failed'):
                with SSHTunnel('faculty'):
                    self.fail('Failed auth should not enter')
            models.assert_not_called()

    def test_startup_timeout_cleans_process(self):
        process = Mock()
        process.poll.return_value = None
        with patch('src.llm.ssh_tunnel.socket.socket'), \
             patch('subprocess.Popen', return_value=process), \
             patch.object(SSHTunnel, 'command', return_value=['ssh', 'faculty']), \
             patch('src.llm.ssh_tunnel.time.monotonic', side_effect=[0, 200]):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                with SSHTunnel('faculty'):
                    self.fail('Timeout should not enter')
            process.terminate.assert_called_once()


class OllamaRequestTests(unittest.TestCase):
    def test_runtime_options_and_think_are_sent_in_correct_fields(self):
        response = Mock(status_code=200)
        response.json.return_value = {'response': 'Odgovor'}
        requests = SimpleNamespace(post=Mock(return_value=response))
        client = OllamaClient(model='mistral:latest', temperature=0.2, max_tokens=1000,
                              top_p=0.8, think=False)
        with patch.dict(sys.modules, {'requests': requests}):
            self.assertEqual(client.generate('Pitanje', system='Sistem'), 'Odgovor')
            payload = requests.post.call_args.kwargs['json']
            self.assertEqual(payload['options'], {'temperature': 0.2, 'num_predict': 1000, 'top_p': 0.8})
            self.assertFalse(payload['think'])
            self.assertNotIn('temperature', {k: v for k, v in payload.items() if k != 'options'})
            client.generate('Pitanje', temperature=0.0, max_tokens=30)
            self.assertEqual(requests.post.call_args.kwargs['json']['options']['temperature'], 0.0)
            self.assertEqual(requests.post.call_args.kwargs['json']['options']['num_predict'], 30)

    def test_http_failure_can_be_reported_without_empty_success(self):
        requests = SimpleNamespace(post=Mock(return_value=Mock(status_code=404, text='model missing')))
        with patch.dict(sys.modules, {'requests': requests}):
            with self.assertRaisesRegex(RuntimeError, '404'):
                OllamaClient(raise_errors=True).generate('Pitanje')
            self.assertEqual(OllamaClient().generate('Pitanje'), '')


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.question = {'id': 'Q1', 'question': 'Pitanje', 'expected_answer': 'Tacan odgovor',
                         'sources': [{'document': 'pravila.pdf', 'section': 'Clan 1', 'pdf_pages': [1]}]}
        self.benchmark = self.root / 'questions.json'
        self.benchmark.write_text(json.dumps({'questions': [self.question]}), encoding='utf-8')
        self.args = collector.parse_args(['--execution', 'local', '--benchmark', str(self.benchmark),
                                         '--model', 'mistral:latest', '--run-id', 'run',
                                         '--output-dir', str(self.root / 'runs')])
        self.args.endpoint = 'http://127.0.0.1:11434'
        self.metadata = {'execution': 'local', 'model': 'mistral:latest', 'model_digest': 'abc'}
        self.quiet = contextlib.redirect_stdout(io.StringIO())
        self.quiet.__enter__()

    def tearDown(self):
        self.quiet.__exit__(None, None, None)
        self.temp.cleanup()

    def run_collection(self, query):
        return collector.collect_benchmark_answers(self.args, query_fn=query, backend_info=self.metadata)

    def test_collect_retry_and_resume_preserve_reference_and_model(self):
        first = Mock(return_value={'status': 'error', 'error': 'connection lost'})
        run = self.run_collection(first)
        self.assertEqual(collector.load_completed_ids(run / 'answers.jsonl'), set())
        second = Mock(return_value={'status': 'success', 'answer': 'Tacan odgovor'})
        self.run_collection(second)
        second.assert_called_once()
        self.run_collection(second)
        second.assert_called_once()  # Successful answer is not generated again.
        answers = list(collector.iter_answers(run / 'answers.jsonl'))
        self.assertEqual(len(answers), 2)
        self.assertEqual(answers[-1]['reference_sources'], self.question['sources'])
        self.assertEqual(answers[-1]['config']['model_digest'], 'abc')
        summary = json.loads((run / 'collection_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['completed_questions'], 1)
        self.assertEqual(summary['successful_questions'], 1)
        self.assertEqual(summary['failed_questions'], 0)

    def test_resume_rejects_changed_model_before_writing(self):
        run = self.run_collection(Mock(return_value={'status': 'success', 'answer': 'Odgovor'}))
        before = (run / 'run_config.json').read_bytes()
        self.metadata['model_digest'] = 'different-weights'
        with self.assertRaisesRegex(ValueError, 'new --run-id'):
            self.run_collection(Mock())
        self.assertEqual((run / 'run_config.json').read_bytes(), before)

    def test_empty_answer_is_retryable_error(self):
        run = self.run_collection(Mock(return_value={'status': 'success', 'answer': ' '}))
        self.assertEqual(collector.load_completed_ids(run / 'answers.jsonl'), set())

    def test_exception_is_recorded_as_error(self):
        run = self.run_collection(Mock(side_effect=ConnectionError('SSH disconnected')))
        record = list(collector.iter_answers(run / 'answers.jsonl'))[0]
        self.assertEqual(record['status'], 'error')
        self.assertIn('SSH disconnected', record['error'])

    def test_no_resume_refuses_existing_answers(self):
        self.run_collection(Mock(return_value={'status': 'success', 'answer': 'Odgovor'}))
        self.args.no_resume = True
        with self.assertRaisesRegex(ValueError, 'Answers already exist'):
            self.run_collection(Mock())

    def test_scoring_counts_only_last_attempt(self):
        self.run_collection(Mock(return_value={'status': 'error', 'error': 'connection lost'}))
        self.run_collection(Mock(return_value={'status': 'success', 'answer': 'Tacan odgovor'}))
        score_args = SimpleNamespace(output_dir=str(self.root / 'runs'), run_id='run', metrics='rouge')
        metric = Mock()
        metric.calculate.return_value = {'rouge1': 1.0, 'rouge2': 1.0, 'rougeL': 1.0}
        with patch.object(scorer, 'build_metric_instances', return_value={'rouge': metric}):
            path = scorer.score_run(score_args)
        output = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(output['summary']['total_answers'], 1)
        self.assertEqual(output['summary']['failed_answers'], 0)
        self.assertEqual(output['results'][0]['reference_sources'], self.question['sources'])

    def test_main_returns_failure_when_collection_has_errors(self):
        query = Mock(return_value={'status': 'error', 'error': 'timeout'})
        with patch.object(collector, 'parse_args', return_value=self.args), \
             patch.object(execution, 'prepare_execution', return_value=contextlib.nullcontext((query, self.metadata))):
            self.assertEqual(collector.main(), 1)

    def test_resume_rejects_changed_benchmark(self):
        self.run_collection(Mock(return_value={'status': 'success', 'answer': 'Odgovor'}))
        self.benchmark.write_text(json.dumps({'questions': [{**self.question, 'question': 'Drugo pitanje'}]}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'benchmark_sha256'):
            self.run_collection(Mock())


if __name__ == '__main__':
    unittest.main()
