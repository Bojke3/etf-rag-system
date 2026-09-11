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
            raise ValueError('Bez interaktivne konzole zadaj --execution local ili --execution ssh (ili BENCHMARK_EXECUTION).')
        while True:
            answer = input('Gde pokrenuti LLM? [1] Lokalno [2] Preko SSH-a (Enter=1): ').strip().lower()
            if answer in ('', '1', 'local', 'lokalno'):
                return 'local'
            if answer in ('2', 'ssh'):
                return 'ssh'
            print('Unesi 1 ili 2.')
    if mode not in ('local', 'ssh', 'api'):
        raise ValueError('BENCHMARK_EXECUTION mora biti ask, local, ssh ili api.')
    if endpoint and mode != 'api':
        raise ValueError('--endpoint se koristi samo uz --execution api.')
    return mode


def choose_model(models, requested, default):
    names = [m.get('name') or m.get('model') for m in models]
    names = [name for name in names if name]
    if not names:
        raise ValueError('Izabrana Ollama nema instaliranih modela.')

    def resolve(name):
        if name in names:
            return name
        if name and ':' not in name and name + ':latest' in names:
            return name + ':latest'
        return None

    if requested:
        chosen = resolve(requested)
        if not chosen:
            raise ValueError(f'Model {requested!r} nije instaliran. Dostupni: {", ".join(names)}')
    elif sys.stdin.isatty():
        chosen = resolve(default)
        for i, name in enumerate(names, 1):
            print(f'  {i}. {name}' + (' (podrazumevani)' if name == chosen else ''))
        while True:
            answer = input(f'Model (broj ili naziv{", Enter=" + chosen if chosen else ""}): ').strip()
            candidate = chosen if not answer else resolve(answer)
            if answer.isdigit() and 1 <= int(answer) <= len(names):
                candidate = names[int(answer)-1]
            if candidate:
                chosen = candidate
                break
            print('Izaberi jedan od navedenih modela.')
    else:
        chosen = resolve(default)
        if not chosen:
            raise ValueError(f'Podrazumevani model {default!r} nije dostupan. Zadaj --model. Dostupni: {", ".join(names)}')
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
        raise ValueError('Lokalni vektorski indeks nije pronadjen. Prvo obradi/indeksiraj dokumente.')
    embedding = SentenceTransformerEmbedding(model_name=config.embedding_model, device=config.embedding_device)
    store = FAISSVectorStore(embedding_dim=embedding.embedding_dim)
    store.load(str(index_dir))
    if store.index.ntotal == 0:
        raise ValueError('Lokalni vektorski indeks je prazan.')
    if store.index.d != embedding.embedding_dim:
        raise ValueError('Dimenzija embedding modela ne odgovara sacuvanom indeksu.')
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
            raise ValueError('API endpoint treba da se zavrsava sa /query.')
        with urlopen(endpoint.rstrip('/')[:-len('/query')] + '/', timeout=5) as response:
            info = json.load(response)
        actual_model = info.get('ollama_model')
        if not actual_model:
            raise ValueError('RAG API ne prijavljuje aktivni model na health endpointu.')
        if args.model and args.model != actual_model:
            raise ValueError(f'API koristi {actual_model}, a trazen je {args.model}. Promeni model u aplikaciji ili koristi local/ssh rezim.')
        args.endpoint, args.model = endpoint, actual_model
        yield None, {'execution': 'api', 'model': actual_model}
        return

    if config is None:
        raise ValueError('Konfiguracija nije ucitana. Proveri .env i projektne Python zavisnosti.')
    manager = nullcontext()
    base_url = config.ollama_base_url.rstrip('/')
    default_model = config.ollama_model
    if mode == 'ssh':
        host = config.ssh_host
        user = config.ssh_user
        if not host:
            if not sys.stdin.isatty():
                raise ValueError('Podesi SSH_HOST u .env za neinteraktivni SSH rad.')
            host = input('SSH adresa ili naziv iz ~/.ssh/config: ').strip()
            if not user:
                user = input('SSH korisnik (Enter za podesavanje iz SSH config-a): ').strip()
        manager = SSHTunnel(host, user, config.ssh_port, config.ssh_identity_file,
                            config.ssh_local_port, config.ssh_ollama_host, config.ssh_ollama_port,
                            config.ssh_startup_timeout)
        base_url, default_model = manager.base_url, config.ssh_ollama_model
    with manager as tunnel:
        models = list_models(base_url)
        model, model_record = choose_model(models, args.model, default_model)
        args.model, args.endpoint = model, base_url
        print(f'LLM: {model} | ID: {model_record.get("digest", "unknown")} | rezim: {mode}', flush=True)
        print('Ucitavanje lokalnog embedding modela i indeksa...', flush=True)
        pipeline = build_local_pipeline(config, base_url, model, args.timeout)

        def query_fn(**request):
            if tunnel is not None and tunnel.process.poll() is not None:
                raise ConnectionError('SSH tunel je prekinut. Ponovo pokreni isti run nakon povezivanja.')
            result = pipeline.process_query(question=request['question'], top_k=request['top_k'],
                                            prompt_strategy=request['prompt_strategy'], include_sources=True)
            if result.get('status') == 'success' and not result.get('answer', '').strip():
                result['status'] = 'error'
                result['error'] = 'Ollama nije vratila odgovor. Proveri model, vezu, timeout i izlazni budzet.'
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
