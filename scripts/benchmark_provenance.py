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


def match_kind(path, expected):
    """How a file matches a recorded hash: exact, only after line-ending repair, or not.

    Provenance hashes raw bytes, but some were recorded on Windows from CRLF
    working copies while the committed blobs are LF. Those records can never
    match byte-for-byte on a Linux/macOS checkout, which would block every
    repetition of an otherwise intact run. Reporting the weaker match keeps the
    original record untouched and states plainly what was compared. Binary
    artifacts are unaffected: a .faiss file is not line-ending sensitive, and a
    coincidental match after substitution is not credible at SHA-256.
    """
    if sha256(path) == expected:
        return 'exact'
    data = Path(path).read_bytes()
    unix = data.replace(b'\r\n', b'\n')
    for variant in (unix, unix.replace(b'\n', b'\r\n')):
        if variant != data and hashlib.sha256(variant).hexdigest() == expected:
            return 'line_endings'
    return None


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


def retrieval_record(config, embedding, store, strategy_id=None, artifact_name=None, parent_count=0):
    """Describe the index the direct collector actually loaded.

    ``artifact_name`` is the suffix a strategy build uses for its files; ``None``
    means the unsuffixed legacy pair, whose original chunking cannot be recovered
    from the artifacts and so is recorded as ``flat_legacy_or_staged``.
    """
    from src.embedding import FAISSVectorStore

    directory = Path(config.vector_store_path)
    index_name, metadata_name = FAISSVectorStore.artifact_names(artifact_name)
    names = [index_name, metadata_name]
    if parent_count:
        names.append(f'parents_{strategy_id}.json')
    model = embedding.model
    encoder_config = getattr(getattr(model[0], 'auto_model', None), 'config', None)
    return {
        'retriever': 'ParentAwareRetriever(SimpleRetriever)' if parent_count else 'SimpleRetriever',
        'effective_strategy': strategy_id if artifact_name else 'flat_legacy_or_staged',
        'parent_chunks_held_out': int(parent_count),
        'embedding_model': config.embedding_model, 'embedding_device': config.embedding_device,
        'embedding_revision': getattr(encoder_config, '_commit_hash', None),
        'embedding_dimension': int(store.index.d),
        'embedding_max_seq_length': int(model.max_seq_length),
        'embedding_revision_note': 'Resolved from loaded encoder config when available; null means unknown.',
        'index_type': type(store.index).__name__, 'vector_count': int(store.index.ntotal),
        'normalization': 'L2-normalized document/query vectors; inner product search',
        'files': {name: sha256(directory / name) for name in names},
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
        # The loader reports which artifacts it actually read, so a strategy
        # build records index_<strategy>.faiss and its parent store rather than
        # the legacy unsuffixed pair.
        required = list(expected_files) if expected_files else ['index.faiss', 'metadatas.json']
        for name in required + [n for n in ('manifest.json',) if n not in required]:
            path = Path(index_dir) / name
            if path.is_file():
                candidates['vectorstore/' + name] = path
        if not all('vectorstore/' + n in candidates for n in required):
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


def relocated_index_file(name, artifact):
    """An index artifact whose recorded directory is gone but whose bytes survive.

    The c001 runs recorded ``models/vectorstore``, the legacy default path on the
    machine that produced them; that directory was renamed to a per-configuration
    one. The remap is accepted only when the file's hash still equals what the run
    recorded, so this identifies the same artifact rather than guessing at a
    substitute. Raw run records are never rewritten.
    """
    from src.embedding import load_registry

    wanted = Path(artifact['path']).name
    for entry in load_registry().values():
        candidate = ROOT / entry['index_dir'] / wanted
        if candidate.is_file() and sha256(candidate) == artifact['sha256']:
            return candidate.resolve()
    return None


def validate_inputs(run_dir, notes=None):
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
        if not path.is_file() and name.startswith('vectorstore/'):
            moved = relocated_index_file(name, artifact)
            if moved is not None:
                if notes is not None:
                    notes.append({'input': name, 'match': 'relocated', 'recorded_path': artifact['path'],
                                  'resolved_path': moved.relative_to(ROOT).as_posix()})
                paths[name] = moved
                continue
        kind = match_kind(path, artifact['sha256']) if path.is_file() else None
        if kind is None:
            raise ValueError(f'Referenced run input missing or changed: {name}')
        if kind != 'exact' and notes is not None:
            notes.append({'input': name, 'match': kind, 'recorded_path': artifact['path']})
        paths[name] = path
    cfg = read_json(run_dir / 'run_config.json')
    if match_kind(paths['benchmark.json'], cfg['benchmark_sha256']) is None:
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
    if (run_dir / 'provenance.json').exists():
        paths = validate_inputs(run_dir)
    else:
        # A run annotated for the first time has no provenance yet; derive the
        # artifact names from the strategy it recorded.
        from src.embedding import FAISSVectorStore
        strategy = recorded_strategy(cfg['backend'])
        suffix = None if strategy == 'flat_baseline' else strategy
        _, metadata_name = FAISSVectorStore.artifact_names(suffix)
        index_dir = Path(cfg['component_config']['vector_store_path'])
        paths = {'benchmark.json': Path(cfg['benchmark']),
                 'vectorstore/' + metadata_name: index_dir / metadata_name}
        parents = index_dir / f'parents_{strategy}.json'
        if parents.is_file():
            paths['vectorstore/' + parents.name] = parents
    if match_kind(paths['benchmark.json'], cfg['benchmark_sha256']) is None:
        raise ValueError('Benchmark differs from the historical run.')
    questions = questions_from(paths['benchmark.json'])
    answers = latest_answers(run_dir)
    if set(answers) != {q['id'] for q in questions}:
        raise ValueError('Reference run must contain exactly the full benchmark question set.')
    _, metadata_path, parents_path = recorded_index(paths)
    metadata = read_json(metadata_path)
    lookup = {(m['document'], str(m['chunk_id'])): m for m in metadata}
    # Hierarchical runs record the parent's text under the matched child's
    # identity, and parents are deliberately not in the embedded metadata.
    parents = read_json(parents_path) if parents_path is not None else {}

    def indexed_text(source):
        if source.get('expanded_to_parent'):
            return (parents.get(source.get('parent_chunk_id')) or {}).get('text')
        return lookup.get((source['document'], str(source['chunk_id'])), {}).get('text')

    for question in questions:
        answer = answers[question['id']]
        if answer.get('status') != 'success' or any(answer[k] != question[k] for k in ('question', 'expected_answer')):
            raise ValueError(f'Incomplete or mismatched reference answer: {question["id"]}')
        docs = answer.get('sources', [])
        if not docs or any(indexed_text(d) != d['text'] for d in docs):
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


def recorded_index(paths):
    """The index artifacts a run recorded, whatever strategy suffix they carry."""
    def find(predicate):
        return next((p for name, p in paths.items()
                     if name.startswith('vectorstore/') and predicate(Path(name).name)), None)

    return (find(lambda n: n.endswith('.faiss')),
            find(lambda n: n.startswith('metadatas')),
            find(lambda n: n.startswith('parents_')))


def recorded_strategy(backend):
    """The chunking strategy a run actually used.

    Runs collected before strategy support recorded ``flat_legacy_or_staged``,
    which is a statement about unrecoverable provenance, not a strategy id; they
    were flat. Anything else is a real strategy and must be restored as such, or
    a repetition of a hierarchical run would quietly collect flat.
    """
    strategy = (backend.get('retrieval_provenance') or {}).get('effective_strategy')
    if not strategy or strategy == 'flat_legacy_or_staged':
        return 'flat_baseline'
    return strategy


def apply_repeat_settings(args, config):
    """Restore recorded effective settings; SSH credentials still come from local config."""
    run_dir = Path(args.repeat_from)
    paths = validate_inputs(run_dir, notes=getattr(args, 'provenance_notes', None))
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
    index_path, _, _ = recorded_index(paths)
    if index_path is None:
        raise ValueError('The reference run recorded no FAISS index.')
    overrides.update(vector_store_path=str(index_path.parent),
                     chunk_strategy=recorded_strategy(backend), ollama_temperature=options['temperature'],
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
    # Weaker-than-exact input matches must appear in the report, not only pass.
    args.provenance_notes = []
    settings = apply_repeat_settings(args, config)
    print('Loading cached encoder and referenced index; no model downloads or LLM requests.', flush=True)
    pipeline = build_local_pipeline(settings, settings.ollama_base_url, args.model, args.timeout,
                                    context_max_chars=args.context_max_chars, num_ctx=args.num_ctx)
    print('Verifying retrieval and model inputs for the complete reference benchmark...', flush=True)
    audit = verify_saved_inputs(run_dir, pipeline.retriever)
    audit.update(verified_at=datetime.now(timezone.utc).isoformat(),
                 embedding_observed_now=pipeline.collection_provenance,
                 generator_called=False,
                 input_match_exceptions=args.provenance_notes,
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
