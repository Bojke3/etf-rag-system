"""Script to embed chunked documents and build the FAISS vector index.

Stage 3, run after chunk_documents.py:
    python scripts/index_documents.py --input data/chunks --output models/vectorstore_new
"""

import argparse
import logging
from datetime import datetime, timezone
import re
import sys
from pathlib import Path

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.stages import file_hash, prepare_output, read_manifest, verified_file, write_manifest
from src.utils import ensure_directories, get_file_paths, setup_logging

try:
    from src.config import config
except ImportError:
    config = None

setup_logging()
logger = logging.getLogger(__name__)

# Matches filenames like "syllabus_chunk0001.txt" produced by chunk_documents.py
_CHUNK_RE = re.compile(r"^(.+)_chunk(\d+)$")


def parse_chunk_filename(stem: str) -> tuple[str, int]:
    """Return (document_name, chunk_id) from a chunk file stem.

    Falls back to (stem, 0) for files not produced by the chunking script.
    """
    m = _CHUNK_RE.match(stem)
    if m:
        return m.group(1), int(m.group(2))
    return stem, 0


def index_documents(
    input_dir: str,
    output_dir: str,
    model_name: str,
    device: str,
    batch_size: int,
) -> None:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    source, target = prepare_output(input_dir, output_dir)
    chunk_files = get_file_paths(str(source), extensions=["*.txt"])
    chunk_manifest = None
    if (source / "manifest.json").exists():
        chunk_manifest = read_manifest(source, "chunking")
        expected = [verified_file(source, item["file"], item["sha256"])
                    for item in chunk_manifest["chunks"]]
        if len(set(expected)) != len(expected) or set(expected) != {Path(p).resolve() for p in chunk_files}:
            raise ValueError("Chunk files do not match the manifest; use an unmixed chunk directory.")
    elif any(_CHUNK_RE.match(Path(p).stem) is None for p in chunk_files):
        raise ValueError("Input must contain chunk files, not raw or cleaned document text.")

    if not chunk_files:
        raise ValueError(f"No chunks found in {input_dir}. Run chunk_documents.py first.")

    logger.info(f"Found {len(chunk_files)} chunks to index")

    # Load embedding model
    from src.embedding import FAISSVectorStore, SentenceTransformerEmbedding
    logger.info(f"Loading embedding model: {model_name} (device={device})")
    embedding_model = SentenceTransformerEmbedding(model_name=model_name, device=device)
    vector_store = FAISSVectorStore(embedding_dim=embedding_model.embedding_dim)

    ensure_directories([str(target)])
    chunk_hashes = {str(Path(p).relative_to(source)): file_hash(p) for p in chunk_files}

    total_indexed = 0
    for batch_start in range(0, len(chunk_files), batch_size):
        batch_paths = chunk_files[batch_start : batch_start + batch_size]

        texts = []
        metadatas = []
        for file_path in batch_paths:
            try:
                text = Path(file_path).read_text(encoding="utf-8").strip()
                if not text:
                    raise ValueError(f"Empty chunk: {file_path}")
                document, chunk_id = parse_chunk_filename(Path(file_path).stem)
                texts.append(text)
                metadatas.append({"document": document, "chunk_id": chunk_id, "text": text})
            except Exception as e:
                raise ValueError(f"Error reading {file_path}: {e}") from e

        if not texts:
            continue

        logger.info(
            f"Embedding batch {batch_start // batch_size + 1}/"
            f"{(len(chunk_files) - 1) // batch_size + 1} ({len(texts)} chunks)"
        )
        embeddings = embedding_model.embed_texts(texts)
        vector_store.add(embeddings, metadatas)
        total_indexed += len(texts)

    if total_indexed == 0:
        raise ValueError("No chunks were indexed; index not saved.")

    if any(file_hash(source / name) != digest for name, digest in chunk_hashes.items()):
        raise ValueError("Chunk content changed during indexing; index not saved.")
    vector_store.save(str(target))
    write_manifest(target, {
        "schema_version": 1, "stage": "indexing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chunk_directory": str(source),
        "chunk_manifest_sha256": file_hash(source / "manifest.json") if chunk_manifest else None,
        "settings": {"embedding_model": model_name, "device": device, "batch_size": batch_size},
        "embedding_dimension": embedding_model.embedding_dim,
        "chunk_count": total_indexed, "chunk_sha256": chunk_hashes,
    })
    logger.info(f"Index saved to {output_dir} ({total_indexed} chunks)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed document chunks and build FAISS index")
    parser.add_argument("--input", default="./data/chunks", help="Directory of chunked .txt files")
    parser.add_argument("--output", default="./models/vectorstore_new", help="New or empty output directory for FAISS index")
    parser.add_argument("--model", default=getattr(config, "embedding_model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"), help="Sentence-transformers model name")
    parser.add_argument("--device", default=getattr(config, "embedding_device", "cpu"), help="Device: cpu or cuda")
    parser.add_argument("--batch-size", type=int, default=32, help="Chunks per embedding batch")

    args = parser.parse_args()

    try:
        if args.batch_size <= 0:
            raise ValueError("batch-size must be positive")
        index_documents(args.input, args.output, args.model, args.device, args.batch_size)
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        sys.exit(1)
