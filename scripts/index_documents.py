"""Script to embed chunked documents and build the FAISS vector index.

Run after process_documents.py:
    python scripts/index_documents.py
    python scripts/index_documents.py --input data/processed --output models/vectorstore
"""

import argparse
import logging
import re
import sys
from pathlib import Path

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.embedding import FAISSVectorStore, SentenceTransformerEmbedding
from src.utils import ensure_directories, get_file_paths, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

# Matches filenames like "syllabus_chunk0001.txt" produced by process_documents.py
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
    chunk_files = get_file_paths(input_dir, extensions=["*.txt"])

    if not chunk_files:
        logger.warning(f"No .txt chunk files found in {input_dir}. Run process_documents.py first.")
        return

    logger.info(f"Found {len(chunk_files)} chunks to index")

    # Load embedding model
    logger.info(f"Loading embedding model: {model_name} (device={device})")
    embedding_model = SentenceTransformerEmbedding(model_name=model_name, device=device)
    vector_store = FAISSVectorStore(embedding_dim=embedding_model.embedding_dim)

    ensure_directories([output_dir])

    total_indexed = 0
    for batch_start in range(0, len(chunk_files), batch_size):
        batch_paths = chunk_files[batch_start : batch_start + batch_size]

        texts = []
        metadatas = []
        for file_path in batch_paths:
            try:
                text = Path(file_path).read_text(encoding="utf-8").strip()
                if not text:
                    logger.warning(f"Skipping empty chunk: {file_path}")
                    continue
                document, chunk_id = parse_chunk_filename(Path(file_path).stem)
                texts.append(text)
                metadatas.append({"document": document, "chunk_id": chunk_id, "text": text})
            except Exception as e:
                logger.error(f"Error reading {file_path}: {e}")

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
        logger.error("No chunks were indexed — index not saved.")
        return

    vector_store.save(output_dir)
    logger.info(f"Index saved to {output_dir} ({total_indexed} chunks)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed document chunks and build FAISS index")
    parser.add_argument("--input", default=config.processed_data_dir, help="Directory of chunked .txt files")
    parser.add_argument("--output", default=config.vector_store_path, help="Output directory for FAISS index")
    parser.add_argument("--model", default=config.embedding_model, help="Sentence-transformers model name")
    parser.add_argument("--device", default=config.embedding_device, help="Device: cpu or cuda")
    parser.add_argument("--batch-size", type=int, default=32, help="Chunks per embedding batch")

    args = parser.parse_args()

    index_documents(
        input_dir=args.input,
        output_dir=args.output,
        model_name=args.model,
        device=args.device,
        batch_size=args.batch_size,
    )
