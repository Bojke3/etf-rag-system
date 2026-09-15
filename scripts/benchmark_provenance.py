"""Record input file references and audit runs without copying datasets or indexes."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REFERENCE_FIELDS = ('required_facts', 'disallowed_claims', 'expected_behavior')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def questions_from(path):
    from scripts.run_benchmark import load_benchmark
    questions = load_benchmark(str(path))
    if len({q['id'] for q in questions}) != len(questions):
        raise ValueError('Duplicate benchmark question IDs.')
    return questions


def latest_answers(run_dir):
    # Fail on malformed records: an audit must not silently skip damaged raw data.
    return {row['id']: row for row in
            (json.loads(line) for line in (Path(run_dir) / 'answers.jsonl').read_text(
                encoding='utf-8').splitlines() if line.strip())}


def runtime_record():
    versions = {}
    for name in ('sentence-transformers', 'transformers', 'torch', 'numpy', 'faiss-cpu',
                 'pydantic-settings', 'requests'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    try:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                           text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    code = {p.relative_to(ROOT).as_posix(): sha256(p)
            for folder in ('src', 'scripts') for p in sorted((ROOT / folder).rglob('*.py'))}
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'machine': platform.machine(), 'processor': platform.processor(),
            'packages': versions, 'git_revision': revision, 'code_sha256': code,
            'server_hardware': None,
            'note': 'Client runtime only. Server hardware/runtime is not inferred from model size.'}


def retrieval_record(config, embedding, store):
    """Describe the actual legacy/staged index used by the current direct collector."""
    directory = Path(config.vector_store_path)
    model = embedding.model
    encoder_config = getattr(getattr(model[0], 'auto_model', None), 'config', None)
    return {
        'retriever': 'SimpleRetriever', 'effective_strategy': 'flat_legacy_or_staged',
        'embedding_model': config.embedding_model, 'embedding_device': config.embedding_device,
        'embedding_revision': getattr(encoder_config, '_commit_hash', None),
        'embedding_dimension': int(store.index.d),
        'embedding_max_seq_length': int(model.max_seq_length),
        'embedding_revision_note': 'Resolved from loaded encoder config when available; null means unknown.',
        'index_type': type(store.index).__name__, 'vector_count': int(store.index.ntotal),
        'normalization': 'L2-normalized document/query vectors; inner product search',
        'files': {name: sha256(directory / name) for name in ('index.faiss', 'metadatas.json')},
        'index_manifest_sha256': sha256(directory / 'manifest.json')
            if (directory / 'manifest.json').is_file() else None,
    }


def record_inputs(run_dir, benchmark, index_dir=None, expected_files=None, retrospective=False,
                  embedding=None, audit=None):
    """Record paths and hashes. Each dataset/index version stays in its own source location."""
    run_dir = Path(run_dir)
    provenance_path = run_dir / 'provenance.json'
    candidates = {'benchmark.json': Path(benchmark)}
    if index_dir is not None:
        for name in ('index.faiss', 'metadatas.json', 'manifest.json'):
            path = Path(index_dir) / name
            if path.is_file():
                candidates['vectorstore/' + name] = path
        if not all('vectorstore/' + n in candidates for n in ('index.faiss', 'metadatas.json')):
            raise ValueError('Cannot record an incomplete vector index.')
    records = {}
    for name, source in candidates.items():
        digest = sha256(source)
        if expected_files and name.startswith('vectorstore/'):
            expected = expected_files.get(Path(name).name)
            if expected is not None and expected != digest:
                raise ValueError(f'Index changed after loading: {source}')
        source = source.resolve()
        try:
            path, base = source.relative_to(ROOT).as_posix(), 'project_root'
        except ValueError:
            path, base = str(source), 'absolute'
        records[name] = {'path': path, 'path_base': base, 'sha256': digest}
    if provenance_path.exists():
        previous = read_json(provenance_path)
        if previous['inputs'] != records:
            raise ValueError('Run provenance differs; use a new run ID.')
        validate_inputs(run_dir)
        return previous
    record = {'schema_version': 2, 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'recording': 'retrospective_audit' if retrospective else 'before_collection',
              'inputs': records, 'embedding': embedding,
              'runtime_observed_now': runtime_record(), 'audit': audit,
              'historical_runtime_known': False if retrospective else None}
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(provenance_path, record)
    return record


def validate_inputs(run_dir):
    run_dir = Path(run_dir).resolve()
    record = read_json(run_dir / 'provenance.json')
    if record.get('schema_version') != 2:
        raise ValueError('Run provenance must reference original input paths (schema version 2).')
    paths = {}
    for name, artifact in record['inputs'].items():
        if artifact['path_base'] == 'project_root':
            path = (ROOT / artifact['path']).resolve()
        elif artifact['path_base'] == 'absolute' and Path(artifact['path']).is_absolute():
            path = Path(artifact['path']).resolve()
        else:
            raise ValueError(f'Invalid input path base: {name}')
        if not path.is_file() or sha256(path) != artifact['sha256']:
            raise ValueError(f'Referenced run input missing or changed: {name}')
        paths[name] = path
    cfg = read_json(run_dir / 'run_config.json')
    if sha256(paths['benchmark.json']) != cfg['benchmark_sha256']:
        raise ValueError('Referenced benchmark does not match the original run.')
    return paths


def add_reference_fields(run_dir, answers):
    """Join referenced criteria by ID and exact text, without rewriting raw answers."""
    if not (Path(run_dir) / 'provenance.json').exists():
        return answers
    paths = validate_inputs(run_dir)
    questions = {q['id']: q for q in questions_from(paths['benchmark.json'])}
    enriched = []
    for answer in answers:
        question = questions.get(answer['id'])
        if question is None or any(answer[k] != question[k] for k in ('question', 'expected_answer')):
            raise ValueError(f'Reference mismatch for {answer["id"]}')
        result = dict(answer)
        for key in REFERENCE_FIELDS:
            if key in result and result[key] != question.get(key, [] if key != 'expected_behavior' else None):
                raise ValueError(f'Reference criteria mismatch for {answer["id"]}: {key}')
            result[key] = question.get(key, [] if key != 'expected_behavior' else None)
        enriched.append(result)
    return enriched


def verify_saved_inputs(run_dir, retriever=None):
    """Check every full saved baseline prompt, optionally with fresh retrieval. No LLM calls."""
    from src.data.preprocessing import TextPreprocessor
    from src.retrieval.context import ContextBuilder
    from src.llm.prompts import PromptTemplate
    run_dir = Path(run_dir)
    cfg = read_json(run_dir / 'run_config.json')
    if cfg['prompt_strategy'] != 'zero_shot' or cfg.get('diagnostic_config') or cfg.get('limit'):
        raise ValueError('Baseline repetition currently requires a full ordinary zero-shot run.')
    paths = validate_inputs(run_dir) if (run_dir / 'provenance.json').exists() else {
        'benchmark.json': Path(cfg['benchmark']),
        'vectorstore/metadatas.json': Path(cfg['component_config']['vector_store_path']) / 'metadatas.json'}
    if sha256(paths['benchmark.json']) != cfg['benchmark_sha256']:
        raise ValueError('Benchmark differs from the historical run.')
    questions = questions_from(paths['benchmark.json'])
    answers = latest_answers(run_dir)
    if set(answers) != {q['id'] for q in questions}:
        raise ValueError('Reference run must contain exactly the full benchmark question set.')
    metadata = read_json(paths['vectorstore/metadatas.json'])
    lookup = {(m['document'], str(m['chunk_id'])): m for m in metadata}
    for question in questions:
        answer = answers[question['id']]
        if answer.get('status') != 'success' or any(answer[k] != question[k] for k in ('question', 'expected_answer')):
            raise ValueError(f'Incomplete or mismatched reference answer: {question["id"]}')
        docs = answer.get('sources', [])
        if not docs or any(lookup.get((d['document'], str(d['chunk_id'])), {}).get('text') != d['text'] for d in docs):
            raise ValueError(f'Indexed source text differs for {question["id"]}')
        normalized = TextPreprocessor(ocr_cleanup=False).clean(question['question'])
        if retriever is not None:
            fresh = retriever.retrieve(normalized, cfg['top_k'])
            signature = lambda rows: [(d['document'], str(d['chunk_id']), d['text']) for d in rows]
            if signature(fresh) != signature(docs):
                raise ValueError(f'Retrieval changed for {question["id"]}; use a new configuration.')
        context = ContextBuilder.build_context(docs, cfg['backend']['context_max_chars'])
        expected = {'context': context, 'system_prompt': PromptTemplate.SYSTEM,
                    'user_prompt': PromptTemplate.format_zero_shot(normalized, context)}
        if any(answer.get('diagnostics', {}).get(k) != v for k, v in expected.items()):
            raise ValueError(f'Model input changed for {question["id"]}; use a new configuration.')
    return {'questions_checked': len(questions), 'saved_sources_and_prompts_match': True,
            'fresh_retrieval_checked': retriever is not None}


def annotate_run(run_dir):
    run_dir = Path(run_dir)
    cfg = read_json(run_dir / 'run_config.json')
    before = sha256(run_dir / 'answers.jsonl')
    audit = verify_saved_inputs(run_dir)
    # Historical audit independently recorded the index used by this baseline family.
    historical = ROOT / 'benchmarking/runs/baselineNo1/analysis/retrieval_review.json'
    expected = None
    if run_dir.resolve() == (ROOT / 'benchmarking/runs/baseline_context8k').resolve():
        verification = read_json(historical)['verification']
        expected = {'index.faiss': verification['current_index_sha256'],
                    'metadatas.json': verification['current_metadata_sha256']}
        audit['index_matches_preserved_historical_audit'] = True
    audit['original_answers_sha256'] = before
    record_inputs(run_dir, cfg['benchmark'], cfg['component_config']['vector_store_path'],
                  expected_files=expected, retrospective=True,
                  embedding={'model': cfg['component_config']['embedding_model'],
                             'revision': None, 'note': 'Historical resolved encoder revision was not recorded.'},
                  audit=audit)
    if sha256(run_dir / 'answers.jsonl') != before:
        raise ValueError('Raw answers changed during annotation.')
    return audit


def apply_repeat_settings(args, config):
    """Restore recorded effective settings; SSH credentials still come from local config."""
    run_dir = Path(args.repeat_from)
    paths = validate_inputs(run_dir)
    original = read_json(run_dir / 'run_config.json')
    if not args.run_id or (Path(args.output_dir) / args.run_id).resolve() == run_dir.resolve():
        raise ValueError('--repeat-from requires a different explicit --run-id.')
    if args.limit or args.diagnostic_contexts or args.endpoint:
        raise ValueError('Baseline repetitions cannot use limit, diagnostic contexts or API endpoint.')
    backend, component = original['backend'], original['component_config']
    if backend['execution'] not in ('local', 'ssh') or not backend.get('model_digest'):
        raise ValueError('Reference requires direct execution and recorded model digest.')
    options = backend['generation_options']
    if options.get('seed') is not None:
        raise ValueError('Repeating an explicitly seeded reference is not supported yet.')
    args.benchmark = str(paths['benchmark.json'])
    args.execution, args.model = backend['execution'], backend['model']
    args.context_max_chars, args.num_ctx = backend['context_max_chars'], options['num_ctx']
    args.top_k, args.prompt_strategy, args.timeout = original['top_k'], original['prompt_strategy'], original['timeout']
    args.expected_model_digest = backend['model_digest']
    overrides = {key: component[key] for key in
                 ('embedding_model', 'embedding_device', 'chunk_size', 'chunk_overlap', 'retrieval_threshold')}
    overrides.update(vector_store_path=str(paths['vectorstore/index.faiss'].parent),
                     chunk_strategy='flat_baseline', ollama_temperature=options['temperature'],
                     ollama_top_p=options['top_p'], ollama_max_tokens=options['num_predict'],
                     ollama_think=options.get('think'))
    return config.model_copy(update=overrides)


def verify_run_locally(run_dir):
    """Use cached encoder weights only. Constructing the LLM client sends no requests."""
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    from src.config import config
    from scripts.collect_benchmark_answers import parse_args
    from scripts.benchmark_execution import build_local_pipeline
    args = parse_args(['--repeat-from', str(run_dir), '--run-id', 'verification_only'])
    settings = apply_repeat_settings(args, config)
    print('Loading cached encoder and referenced index; no model downloads or LLM requests.', flush=True)
    pipeline = build_local_pipeline(settings, settings.ollama_base_url, args.model, args.timeout,
                                    context_max_chars=args.context_max_chars, num_ctx=args.num_ctx)
    print('Verifying retrieval and model inputs for the complete reference benchmark...', flush=True)
    audit = verify_saved_inputs(run_dir, pipeline.retriever)
    audit.update(verified_at=datetime.now(timezone.utc).isoformat(),
                 embedding_observed_now=pipeline.collection_provenance,
                 generator_called=False,
                 note='Current cached encoder reproduces saved retrieval. Historical encoder revision and server runtime remain unknown.')
    write_json(Path(run_dir) / 'local_retrieval_verification.json', audit)
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--annotate-run')
    mode.add_argument('--verify-run', help='Verify all retrieval/prompt inputs with the cached encoder; no LLM calls/downloads')
    arguments = parser.parse_args()
    print(json.dumps(annotate_run(arguments.annotate_run) if arguments.annotate_run
                     else verify_run_locally(arguments.verify_run), indent=2))
