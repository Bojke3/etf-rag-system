# ETF RAG System

A retrieval-augmented generation (RAG) system for searching the internal documentation of the University of Belgrade School of Electrical Engineering (ETF). It retrieves relevant passages from faculty documents and uses a local large language model to answer questions with source references.

## Features

- PDF and Word document ingestion with OCR fallback
- Flat and hierarchical text chunking
- Multilingual sentence-transformer embeddings and FAISS retrieval
- Local answer generation through Ollama
- Source-aware answers through a web interface and JSON API
- Reproducible retrieval and generation benchmarks

## Architecture

```text
Documents -> extraction -> chunking -> embeddings -> FAISS index
                                                    |
User question -> retrieval -> context -> local LLM -> answer + sources
```

See [Architecture](docs/ARCHITECTURE.md) and [Data pipeline](docs/DATA_PIPELINE.md) for implementation details.

## Requirements

- Python 3.10 or newer
- Git
- [Ollama](https://ollama.com/) for local answer generation
- Enough disk space for the Python dependencies, embedding model, and LLM

## Quick start

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/Bojke3/etf-rag-system.git
cd etf-rag-system
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux or macOS
source .venv/bin/activate
```

Install the dependencies and create the local configuration:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```bash
# Linux or macOS
cp .env.example .env
```

Start Ollama, then download the default model from another terminal:

```bash
ollama pull mistral
```

The repository includes a ready-to-use FAISS index. The default settings in `.env.example` select its matching embedding model. Start the application with:

```bash
python web/app.py
```

Open `http://localhost:8000/chat` in a browser. The health endpoint is available at `http://localhost:8000/`, and questions can be submitted to `POST /query`.

## Try other models

To test another Ollama model, install it with `ollama pull MODEL_NAME`, then select it in the web interface or set `OLLAMA_MODEL=MODEL_NAME` in `.env` and restart the application.

For a repeatable local comparison, run the model against the [final benchmark questions](benchmarking/finalna_pitanja.json):

```bash
python scripts/collect_benchmark_answers.py --execution local --model MODEL_NAME --benchmark benchmarking/finalna_pitanja.json --run-id MODEL_RUN_ID
```

Use a unique run ID for every model or configuration. Results are saved under `benchmarking/runs/MODEL_RUN_ID/`. Keep the vector index, retrieval settings, prompt strategy, and context budget fixed when comparing generation models. To test a different embedding model, build a new index with `scripts/index_documents.py --model EMBEDDING_MODEL` and set the same `EMBEDDING_MODEL` and new `VECTOR_STORE_PATH` in `.env`; an index must not be queried with a different encoder from the one that created it.

## Build a new index

To rebuild the knowledge base from documents in `DataAkti/`, use the three-stage pipeline:

```bash
python scripts/extract_documents.py --input DataAkti --output data/extracted
python scripts/chunk_documents.py --input data/extracted --output data/chunks --chunk-size 1024 --overlap 150
python scripts/index_documents.py --input data/chunks --output models/vectorstore_new
```

Output directories must be new or empty. After indexing, set `VECTOR_STORE_PATH=./models/vectorstore_new` in `.env`. Keep `EMBEDDING_MODEL` identical to the model used to build the index.

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=src
```

## Project structure

| Path | Purpose |
| --- | --- |
| `src/data/` | Document loading, OCR, preprocessing, and chunking |
| `src/embedding/` | Embedding models, FAISS storage, and index validation |
| `src/retrieval/` | Similarity search and parent-aware retrieval |
| `src/llm/` | Local and hosted LLM clients |
| `src/rag/` | Context construction, prompting, and answer generation |
| `src/evaluation/` | Retrieval and generation evaluation |
| `scripts/` | Data processing and benchmarking commands |
| `web/` | Flask web interface and API |
| `benchmarking/` | Question sets, run records, and benchmark results |

## Documentation

- [Setup guide](docs/SETUP.md)
- [API reference](docs/API_DOCS.md)
- [Benchmarking guide](docs/BENCHMARKING.md)
- [Final benchmark questions](benchmarking/finalna_pitanja.json)
- [Retrieval evaluation](docs/retrieval_evaluation.md)
- [Research notes](docs/RESEARCH.md)
- [Vector index registry](models/README.md)

## Authors

Andrija Trnavcevic and Vuk Bojovic

## License

This project is distributed under the [MIT License](LICENSE).
