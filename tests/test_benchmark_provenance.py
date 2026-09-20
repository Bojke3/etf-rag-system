"""Offline protection against mixing benchmark inputs and losing historical criteria."""

import contextlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts import benchmark_provenance as provenance
from scripts import benchmark_execution as execution
from scripts import collect_benchmark_answers as collector
from scripts import score_benchmark_run as scorer
from scripts import run_benchmark as runner
from src.config import Config
from src.data.preprocessing import TextPreprocessor
from src.llm.prompts import PromptTemplate


@pytest.fixture
def reference(tmp_path):
    question = {'id': 'Q1', 'question': 'Може ли поново?', 'expected_answer': 'Ne.',
                'required_facts': ['Samo jednom.'], 'disallowed_claims': ['Moze ponovo.'],
                'expected_behavior': 'answer'}
    benchmark = tmp_path / 'questions.json'
    provenance.write_json(benchmark, {'questions': [question]})
    index_dir = tmp_path / 'index'
    index_dir.mkdir()
    (index_dir / 'index.faiss').write_bytes(b'fake index for reference testing')
    source = {'document': 'rules', 'chunk_id': 1, 'text': 'Samo jednom.', 'score': 0.9}
    provenance.write_json(index_dir / 'metadatas.json', [source])
    run = tmp_path / 'run'
    run.mkdir()
    cfg = {'run_id': 'run', 'benchmark': str(benchmark),
           'benchmark_sha256': provenance.sha256(benchmark), 'limit': None,
           'top_k': 5, 'prompt_strategy': 'zero_shot', 'timeout': 900,
           'backend': {'execution': 'local', 'model': 'mistral:latest', 'model_digest': 'original',
                       'context_max_chars': 8000,
                       'generation_options': {'temperature': 0.7, 'top_p': 0.9,
                                              'num_predict': 2048, 'num_ctx': 8192, 'think': None}},
           'component_config': {'embedding_model': 'historical-model', 'embedding_device': 'cpu',
                                'chunk_size': 1024, 'chunk_overlap': 150, 'retrieval_threshold': 0.0,
                                'vector_store_path': str(index_dir)}}
    provenance.write_json(run / 'run_config.json', cfg)
    normalized = TextPreprocessor(ocr_cleanup=False).clean(question['question'])
    row = {'id': 'Q1', 'question': question['question'], 'expected_answer': 'Ne.',
           'actual_answer': 'Ne, samo jednom.', 'status': 'success', 'sources': [source],
           'diagnostics': {'context': source['text'], 'system_prompt': PromptTemplate.SYSTEM,
                           'user_prompt': PromptTemplate.format_zero_shot(normalized, source['text'])}}
    (run / 'answers.jsonl').write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
    with patch.object(provenance, 'runtime_record', return_value={'git_revision': 'test'}):
        provenance.annotate_run(run)
    return run, question, source


def test_annotation_preserves_raw_answers_and_supplies_historical_criteria(reference):
    run, question, _ = reference
    before = (run / 'answers.jsonl').read_bytes()
    rows = provenance.add_reference_fields(run, list(provenance.latest_answers(run).values()))
    assert rows[0]['required_facts'] == question['required_facts']
    assert rows[0]['expected_behavior'] == 'answer'
    assert (run / 'answers.jsonl').read_bytes() == before
    assert provenance.read_json(run / 'provenance.json')['recording'] == 'retrospective_audit'
    assert provenance.verify_saved_inputs(run)['questions_checked'] == 1


def test_records_original_paths_without_copies_and_detects_changed_input(reference):
    run, _, _ = reference
    cfg = provenance.read_json(run / 'run_config.json')
    paths = provenance.validate_inputs(run)
    assert paths['vectorstore/index.faiss'] == Path(cfg['component_config']['vector_store_path']) / 'index.faiss'
    assert paths['benchmark.json'] == Path(cfg['benchmark'])
    assert not (run / 'inputs').exists()
    paths['vectorstore/index.faiss'].write_bytes(b'changed')
    with pytest.raises(ValueError, match='missing or changed'):
        provenance.validate_inputs(run)


def test_changed_question_or_criteria_cannot_be_silently_backfilled(reference):
    run, _, _ = reference
    row = provenance.latest_answers(run)['Q1']
    with pytest.raises(ValueError, match='Reference mismatch'):
        provenance.add_reference_fields(run, [{**row, 'question': 'Another question'}])
    with pytest.raises(ValueError, match='criteria mismatch'):
        provenance.add_reference_fields(run, [{**row, 'required_facts': ['Wrong']}])


def test_repeat_uses_frozen_settings_instead_of_changed_env(reference):
    run, _, _ = reference
    args = collector.parse_args(['--repeat-from', str(run), '--run-id', 'dev_base_c001_r02'])
    cfg = Config(_env_file=None, embedding_model='new-model', ollama_temperature=0.0,
                 ollama_top_p=0.1, ollama_think=True, retrieval_threshold=0.7)
    repeated = provenance.apply_repeat_settings(args, cfg)
    assert repeated.ollama_temperature == 0.7
    assert repeated.ollama_top_p == 0.9
    assert repeated.ollama_think is None
    assert repeated.embedding_model == 'historical-model'
    assert repeated.retrieval_threshold == 0.0
    assert Path(repeated.vector_store_path) == run.parent / 'index'
    assert Path(args.benchmark) == run.parent / 'questions.json'
    assert args.top_k == 5 and args.num_ctx == 8192
    assert args.expected_model_digest == 'original'
    assert cfg.ollama_temperature == 0.0
    args.limit = 1
    with pytest.raises(ValueError, match='cannot use limit'):
        provenance.apply_repeat_settings(args, cfg)


def test_fresh_retrieval_or_prompt_change_is_rejected_without_generation(reference):
    run, _, source = reference
    retriever = Mock()
    retriever.retrieve.return_value = [source]
    assert provenance.verify_saved_inputs(run, retriever)['fresh_retrieval_checked']
    retriever.retrieve.return_value = [{**source, 'chunk_id': 99}]
    with pytest.raises(ValueError, match='Retrieval changed'):
        provenance.verify_saved_inputs(run, retriever)
    with patch.object(PromptTemplate, 'SYSTEM', 'A changed instruction'):
        with pytest.raises(ValueError, match='Model input changed'):
            provenance.verify_saved_inputs(run)


def test_model_digest_change_stops_before_pipeline_and_generation(reference):
    run, _, _ = reference
    args = collector.parse_args(['--repeat-from', str(run), '--run-id', 'dev_base_c001_r02'])
    cfg = provenance.apply_repeat_settings(args, Config(_env_file=None))
    with patch.object(execution, 'list_models', return_value=[{'name': 'mistral:latest', 'digest': 'changed'}]), \
         patch.object(execution, 'build_local_pipeline') as build:
        with pytest.raises(ValueError, match='digest differs'):
            with execution.prepare_execution(args, cfg):
                pytest.fail('Changed generator accepted')
        build.assert_not_called()


def test_resume_retries_latest_error_even_after_older_success(tmp_path):
    answers = tmp_path / 'answers.jsonl'
    answers.write_text('\n'.join(json.dumps({'id': 'Q1', 'status': s})
                                  for s in ('success', 'error')), encoding='utf-8')
    assert collector.load_completed_ids(answers) == set()


def test_no_run_mutation_when_index_changes_after_loading(tmp_path):
    benchmark = tmp_path / 'questions.json'
    provenance.write_json(benchmark, {'questions': []})
    index = tmp_path / 'index'
    index.mkdir()
    (index / 'index.faiss').write_bytes(b'changed')
    provenance.write_json(index / 'metadatas.json', [])
    run = tmp_path / 'run'
    with pytest.raises(ValueError, match='Index changed after loading'):
        provenance.record_inputs(run, benchmark, index, expected_files={'index.faiss': 'old'})
    assert not run.exists()


def test_scorer_uses_referenced_criteria_without_rewriting_historical_answers(reference):
    run, question, _ = reference
    before = (run / 'answers.jsonl').read_bytes()
    metric = Mock()
    metric.calculate_details.return_value = {'score': 5.0}
    args = SimpleNamespace(output_dir=str(run.parent), run_id=run.name, metrics='llm_judge')
    with patch.object(scorer, 'build_metric_instances', return_value={'llm_judge': metric}), \
         contextlib.redirect_stdout(io.StringIO()):
        output = scorer._score_run(args)
    assert metric.calculate_details.call_args.kwargs['required_facts'] == question['required_facts']
    assert provenance.read_json(output)['reference_benchmark_sha256'] == provenance.sha256(run.parent / 'questions.json')
    assert (run / 'answers.jsonl').read_bytes() == before


def test_hierarchical_collection_refuses_to_fall_back_to_a_flat_index(tmp_path):
    """A strategy must never quietly collect against another strategy's index.

    The legacy unsuffixed pair is a valid flat index, so falling back to it for
    CHUNK_STRATEGY=hierarchical would produce a complete, plausible run that
    measured flat chunking under a hierarchical label.
    """
    index_dir = tmp_path / 'index'
    index_dir.mkdir()
    (index_dir / 'index.faiss').write_bytes(b'')
    (index_dir / 'metadatas.json').write_text('[]', encoding='utf-8')
    cfg = SimpleNamespace(chunk_strategy='hierarchical', vector_store_path=str(index_dir))
    with pytest.raises(ValueError, match='No hierarchical index'):
        execution.build_local_pipeline(cfg, 'http://localhost:11434', 'mistral', 900)


def test_collection_records_relative_paths_and_resumes_legacy_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'PROJECT_ROOT', tmp_path)
    monkeypatch.setattr(provenance, 'ROOT', tmp_path)
    monkeypatch.chdir(tmp_path)
    benchmark = tmp_path / 'questions.json'
    provenance.write_json(benchmark, {'questions': [
        {'id': 'Q1', 'question': 'Pitanje?', 'expected_answer': 'Odgovor.'}
    ]})
    monkeypatch.setattr(collector, 'config', Config(
        _env_file=None, vector_store_path=str(tmp_path / 'index')))
    monkeypatch.setattr(provenance, 'runtime_record', lambda: {})
    args = collector.parse_args(['--benchmark', str(benchmark), '--run-id', 'new',
                                 '--output-dir', str(tmp_path / 'runs'),
                                 '--repeat-from', str(tmp_path / 'reference')])
    query = Mock(return_value={'status': 'success', 'answer': 'Odgovor.'})
    run = collector.collect_benchmark_answers(args, query_fn=query)
    cfg = provenance.read_json(run / 'run_config.json')
    assert cfg['benchmark'] == 'questions.json'
    assert cfg['repeat_from'] == 'reference'
    assert cfg['component_config']['vector_store_path'] == 'index'
    assert provenance.read_json(run / 'collection_summary.json')['config'] == cfg
    assert provenance.validate_inputs(run)['benchmark.json'] == benchmark
    raw = (run / 'answers.jsonl').read_bytes()
    # Resume must accept the absolute spelling used by existing repetitions.
    cfg['benchmark'] = str(benchmark)
    cfg['repeat_from'] = str(tmp_path / 'reference')
    cfg['component_config']['vector_store_path'] = str(tmp_path / 'index')
    provenance.write_json(run / 'run_config.json', cfg)
    collector.collect_benchmark_answers(args, query_fn=query)
    query.assert_called_once()
    assert (run / 'answers.jsonl').read_bytes() == raw
    assert provenance.read_json(run / 'run_config.json')['benchmark'] == 'questions.json'
    # A copied repository resolves question references at its new location.
    import shutil
    moved = tmp_path / 'moved_project'
    moved.mkdir()
    shutil.copy2(benchmark, moved / 'questions.json')
    shutil.copytree(run, moved / 'runs' / 'new')
    monkeypatch.setattr(provenance, 'ROOT', moved)
    assert provenance.validate_inputs(moved / 'runs' / 'new')['benchmark.json'] == moved / 'questions.json'


def test_windows_recorded_hash_verifies_after_line_ending_repair(tmp_path):
    """A CRLF-recorded text input must not block an otherwise intact run."""
    path = tmp_path / 'questions.json'
    path.write_bytes(b'{"questions": []}\n')
    crlf_digest = provenance.hashlib.sha256(b'{"questions": []}\r\n').hexdigest()

    assert provenance.match_kind(path, provenance.sha256(path)) == 'exact'
    assert provenance.match_kind(path, crlf_digest) == 'line_endings'
    assert provenance.match_kind(path, '0' * 64) is None


def test_renamed_index_directory_is_resolved_only_by_matching_hash(reference, monkeypatch):
    run, _, _ = reference
    record = provenance.read_json(run / 'provenance.json')
    original = Path(record['inputs']['vectorstore/index.faiss']['path'])
    moved = original.parent.parent / 'renamed'
    original.parent.rename(moved)

    monkeypatch.setattr(provenance, 'ROOT', moved.parent)
    monkeypatch.setattr('src.embedding.load_registry',
                        lambda *a, **k: {'cX': {'index_dir': 'renamed'}})
    notes = []
    paths = provenance.validate_inputs(run, notes=notes)
    assert paths['vectorstore/index.faiss'] == (moved / 'index.faiss').resolve()
    assert {n['match'] for n in notes} == {'relocated'}

    (moved / 'index.faiss').write_bytes(b'different bytes entirely')
    with pytest.raises(ValueError, match='missing or changed'):
        provenance.validate_inputs(run)


def test_repeating_a_hierarchical_run_restores_its_strategy():
    """Repeating must not relabel a hierarchical reference as flat."""
    flat = {'retrieval_provenance': {'effective_strategy': 'flat_legacy_or_staged'}}
    hierarchical = {'retrieval_provenance': {'effective_strategy': 'hierarchical'}}
    assert provenance.recorded_strategy(flat) == 'flat_baseline'
    assert provenance.recorded_strategy({}) == 'flat_baseline'
    assert provenance.recorded_strategy(hierarchical) == 'hierarchical'

    paths = {'benchmark.json': Path('q.json'),
             'vectorstore/index_hierarchical.faiss': Path('idx/index_hierarchical.faiss'),
             'vectorstore/metadatas_hierarchical.json': Path('idx/metadatas_hierarchical.json'),
             'vectorstore/parents_hierarchical.json': Path('idx/parents_hierarchical.json')}
    index, metadata, parents = provenance.recorded_index(paths)
    assert index.name == 'index_hierarchical.faiss'
    assert metadata.name == 'metadatas_hierarchical.json'
    assert parents.name == 'parents_hierarchical.json'
