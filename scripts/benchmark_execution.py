"""Select local generation, SSH generation, or an existing RAG HTTP API."""

import hashlib
import json
import sys
from contextlib import contextmanager, nullcontext
from pathlib import Path
from urllib.request import urlopen

from src.llm.ssh_tunnel import SSHTunnel, list_models


def choose_execution(requested, configured='ask', endpoint=None):
    mode = requested or ('api' if endpoint else configured)
    if mode == 'ask':
        if not sys.stdin.isatty():
            raise ValueError('In non-interactive mode, specify --execution local or --execution ssh (or set BENCHMARK_EXECUTION).')
        while True:
            answer = input('Where should the LLM run? [1] Local [2] SSH (Enter=1): ').strip().lower()
            if answer in ('', '1', 'local', 'lokalno'):
                return 'local'
            if answer in ('2', 'ssh'):
                return 'ssh'
            print('Enter 1 or 2.')
    if mode not in ('local', 'ssh', 'api'):
        raise ValueError('BENCHMARK_EXECUTION must be ask, local, ssh, or api.')
    if endpoint and mode != 'api':
        raise ValueError('--endpoint is only supported with --execution api.')
    return mode


def choose_model(models, requested, default):
    names = [m.get('name') or m.get('model') for m in models]
    names = [name for name in names if name]
    if not names:
        raise ValueError('The selected Ollama instance has no installed models.')

    def resolve(name):
        if name in names:
            return name
        if name and ':' not in name and name + ':latest' in names:
            return name + ':latest'
        return None

    if requested:
        chosen = resolve(requested)
        if not chosen:
            raise ValueError(f'Model {requested!r} is not installed. Available models: {", ".join(names)}')
    elif sys.stdin.isatty():
        chosen = resolve(default)
        for i, name in enumerate(names, 1):
            print(f'  {i}. {name}' + (' (default)' if name == chosen else ''))
        while True:
            answer = input(f'Model (number or name{", Enter=" + chosen if chosen else ""}): ').strip()
            candidate = chosen if not answer else resolve(answer)
            if answer.isdigit() and 1 <= int(answer) <= len(names):
                candidate = names[int(answer)-1]
            if candidate:
                chosen = candidate
                break
            print('Select one of the listed models.')
    else:
        chosen = resolve(default)
        if not chosen:
            raise ValueError(f'Default model {default!r} is not available. Specify --model. Available models: {", ".join(names)}')
    record = next(m for m in models if (m.get('name') or m.get('model')) == chosen)
    return chosen, record


def build_local_pipeline(config, base_url, model, timeout):
    """Keep the same retriever/prompt pipeline on the laptop in both modes."""
    from src.embedding import SentenceTransformerEmbedding, FAISSVectorStore
    from src.retrieval import SimpleRetriever
    from src.llm import OllamaClient
    from src.rag import RAGPipeline

    index_dir = Path(config.vector_store_path)
    if not all((index_dir / name).is_file() for name in ('index.faiss', 'metadatas.json')):
        raise ValueError('Local vector index not found. Process and index the documents first.')
    embedding = SentenceTransformerEmbedding(model_name=config.embedding_model, device=config.embedding_device)
    store = FAISSVectorStore(embedding_dim=embedding.embedding_dim)
    store.load(str(index_dir))
    if store.index.ntotal == 0:
        raise ValueError('The local vector index is empty.')
    if store.index.d != embedding.embedding_dim:
        raise ValueError('The embedding model dimension does not match the saved index.')
    retriever = SimpleRetriever(embedding, store, threshold=config.retrieval_threshold)
    client = OllamaClient(base_url=base_url, model=model, timeout=timeout,
                          temperature=config.ollama_temperature, max_tokens=config.ollama_max_tokens,
                          top_p=config.ollama_top_p, think=config.ollama_think, raise_errors=True)
    return RAGPipeline(retriever, client, embedding)


@contextmanager
def prepare_execution(args, config):
    mode = choose_execution(args.execution, getattr(config, 'benchmark_execution', 'ask'), args.endpoint)
    args.execution = mode
    if mode == 'api':
        endpoint = args.endpoint or 'http://localhost:8000/query'
        if not endpoint.rstrip('/').endswith('/query'):
            raise ValueError('The API endpoint must end with /query.')
        with urlopen(endpoint.rstrip('/')[:-len('/query')] + '/', timeout=5) as response:
            info = json.load(response)
        actual_model = info.get('ollama_model')
        if not actual_model:
            raise ValueError('The RAG API health endpoint does not report the active model.')
        if args.model and args.model != actual_model:
            raise ValueError(f'The API uses {actual_model}, but {args.model} was requested. Change the model in the app or use local/ssh mode.')
        args.endpoint, args.model = endpoint, actual_model
        yield None, {'execution': 'api', 'model': actual_model}
        return

    if config is None:
        raise ValueError('Configuration could not be loaded. Check .env and the project Python dependencies.')
    manager = nullcontext()
    base_url = config.ollama_base_url.rstrip('/')
    default_model = config.ollama_model
    if mode == 'ssh':
        host = config.ssh_host
        user = config.ssh_user
        if not host:
            if not sys.stdin.isatty():
                raise ValueError('Set SSH_HOST in .env for non-interactive SSH execution.')
            host = input('SSH host or alias from ~/.ssh/config: ').strip()
            if not user:
                user = input('SSH username (Enter to use your SSH configuration): ').strip()
        manager = SSHTunnel(host, user, config.ssh_port, config.ssh_identity_file,
                            config.ssh_local_port, config.ssh_ollama_host, config.ssh_ollama_port,
                            config.ssh_startup_timeout)
        base_url, default_model = manager.base_url, config.ssh_ollama_model
    with manager as tunnel:
        models = list_models(base_url)
        model, model_record = choose_model(models, args.model, default_model)
        args.model, args.endpoint = model, base_url
        print(f'LLM: {model} | ID: {model_record.get("digest", "unknown")} | mode: {mode}', flush=True)
        print('Loading the local embedding model and vector index...', flush=True)
        pipeline = build_local_pipeline(config, base_url, model, args.timeout)

        def query_fn(**request):
            if tunnel is not None and tunnel.process.poll() is not None:
                raise ConnectionError('The SSH tunnel disconnected. Reconnect and resume with the same --run-id.')
            result = pipeline.process_query(question=request['question'], top_k=request['top_k'],
                                            prompt_strategy=request['prompt_strategy'], include_sources=True)
            if result.get('status') == 'success' and not result.get('answer', '').strip():
                result['status'] = 'error'
                result['error'] = 'Ollama returned no answer. Check the model, connection, timeout, and output token budget.'
            return result

        metadata = {
            'execution': mode, 'model': model, 'model_digest': model_record.get('digest'),
            'model_details': model_record.get('details', {}),
            'generation_options': {'temperature': config.ollama_temperature,
                                   'num_predict': config.ollama_max_tokens,
                                   'top_p': config.ollama_top_p, 'think': config.ollama_think},
            'prompts_sha256': hashlib.sha256((Path(__file__).resolve().parents[1] / 'src/llm/prompts.py').read_bytes()).hexdigest(),
        }
        yield query_fn, metadata
