"""Script to embed chunked documents and build the FAISS vector index.

Run after process_documents.py:
    python scripts/index_documents.py
    python scripts/index_documents.py --strategy hierarchical

Each chunking strategy gets its own index artifacts, so they never mix:

    models/vectorstore/index_<strategy>.faiss
    models/vectorstore/metadatas_<strategy>.json
    models/vectorstore/parents_<strategy>.json   (hierarchical only, NOT embedded)

For hierarchical chunking only child chunks are embedded; parents are written to
the sidecar above and looked up by id at retrieval time to supply extra context.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.chunking import LEVEL_CHILD, LEVEL_FLAT, LEVEL_PARENT, Chunk, resolve_strategy_id
from src.embedding import FAISSVectorStore, SentenceTransformerEmbedding
from src.utils import ensure_directories, get_file_paths, setup_logging

try:
    from src.config import config
except ImportError:
    config = None

setup_logging()
logger = logging.getLogger(__name__)

# Matches filenames like "syllabus_chunk0001.txt" produced by process_documents.py
_CHUNK_RE = re.compile(r"^(.+)_chunk(\d+)$")

CHUNKS_FILE = "chunks.jsonl"
#: Levels that get embedded into the vector index.
EMBEDDED_LEVELS = (LEVEL_FLAT, LEVEL_CHILD)


def parse_chunk_filename(stem: str) -> Tuple[str, int]:
    """Return (document_name, chunk_id) from a chunk file stem.

    Falls back to (stem, 0) for files not produced by the chunking script.
    """
    m = _CHUNK_RE.match(stem)
    if m:
        return m.group(1), int(m.group(2))
    return stem, 0


def parents_file_name(strategy_id: str) -> str:
    return f"parents_{strategy_id}.json"


def resolve_input_dir(input_dir: str, strategy_id: str) -> Path:
    """Prefer the per-strategy subdirectory, fall back to a flat legacy layout."""
    candidate = Path(input_dir) / strategy_id
    if candidate.exists():
        return candidate
    logger.warning(
        "No %s directory under %s — falling back to the legacy flat layout",
        strategy_id,
        input_dir,
    )
    return Path(input_dir)


def load_chunks(source_dir: Path) -> List[Chunk]:
    """Load chunks from chunks.jsonl, or from legacy per-chunk .txt files."""
    chunks_path = source_dir / CHUNKS_FILE

    if chunks_path.exists():
        chunks = []
        with open(chunks_path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    chunks.append(Chunk.from_dict(json.loads(line)))
                except Exception as e:
                    logger.error("Bad chunk record at %s:%s: %s", chunks_path, line_no, e)
        logger.info("Loaded %s chunks from %s", len(chunks), chunks_path)
        return chunks

    # Legacy layout: one .txt per chunk, metadata re-derived from the file name.
    chunk_files = get_file_paths(str(source_dir), extensions=["*.txt"])
    chunks = []
    for file_path in chunk_files:
        try:
            text = Path(file_path).read_text(encoding="utf-8").strip()
            if not text:
                logger.warning(f"Skipping empty chunk: {file_path}")
                continue
            document, chunk_id = parse_chunk_filename(Path(file_path).stem)
            chunks.append(
                Chunk(
                    text=text,
                    metadata={"document": document, "chunk_id": chunk_id},
                    chunk_id=str(chunk_id),
                    level=LEVEL_FLAT,
                )
            )
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")

    logger.info("Loaded %s chunks from legacy .txt files in %s", len(chunks), source_dir)
    return chunks


def build_metadata(chunk: Chunk, fallback_chunk_id: int) -> Dict:
    """The metadata record stored alongside each vector.

    ``document``/``chunk_id``/``text`` are kept for backwards compatibility with
    everything that already reads metadatas.json; the rest is additive.
    """
    meta = chunk.metadata or {}
    return {
        "document": meta.get("document", "Unknown"),
        "chunk_id": meta.get("chunk_index", fallback_chunk_id),
        "text": chunk.text,
        "id": chunk.chunk_id,
        "parent_chunk_id": chunk.parent_chunk_id,
        "strategy_id": chunk.strategy_id,
        "level": chunk.level,
        "section": meta.get("section"),
        "subject": meta.get("subject"),
        "page": meta.get("page"),
        "source": meta.get("source"),
    }


def index_documents(
    input_dir: str,
    output_dir: str,
    model_name: str,
    device: str,
    batch_size: int,
    strategy: Optional[str] = None,
) -> None:
    strategy_id = resolve_strategy_id(strategy)
    source_dir = resolve_input_dir(input_dir, strategy_id)

    all_chunks = load_chunks(source_dir)
    if not all_chunks:
        logger.warning(
            f"No chunks found in {source_dir}. Run process_documents.py --strategy {strategy_id} first."
        )
        return

    to_embed = [c for c in all_chunks if c.level in EMBEDDED_LEVELS]
    parents = [c for c in all_chunks if c.level == LEVEL_PARENT]

    if not to_embed:
        logger.error("No embeddable chunks (levels %s) found.", ", ".join(EMBEDDED_LEVELS))
        return

    logger.info(
        "Strategy=%s: %s chunks to embed, %s parent chunks held out",
        strategy_id,
        len(to_embed),
        len(parents),
    )

    # Load embedding model
    logger.info(f"Loading embedding model: {model_name} (device={device})")
    embedding_model = SentenceTransformerEmbedding(model_name=model_name, device=device)
    vector_store = FAISSVectorStore(embedding_dim=embedding_model.embedding_dim)

    ensure_directories([output_dir])

    total_indexed = 0
    for batch_start in range(0, len(to_embed), batch_size):
        batch = to_embed[batch_start : batch_start + batch_size]

        texts = [c.text for c in batch]
        metadatas = [
            build_metadata(c, batch_start + i) for i, c in enumerate(batch)
        ]

        logger.info(
            f"Embedding batch {batch_start // batch_size + 1}/"
            f"{(len(to_embed) - 1) // batch_size + 1} ({len(texts)} chunks)"
        )
        embeddings = embedding_model.embed_texts(texts)
        vector_store.add(embeddings, metadatas)
        total_indexed += len(texts)

    if total_indexed == 0:
        logger.error("No chunks were indexed — index not saved.")
        return

    vector_store.save(output_dir, name=strategy_id)

    # Parent chunks are not embedded; they are looked up by id at retrieval time.
    parents_path = Path(output_dir) / parents_file_name(strategy_id)
    parent_map = {
        c.chunk_id: {
            "text": c.text,
            "document": (c.metadata or {}).get("document"),
            "section": (c.metadata or {}).get("section"),
            "page": (c.metadata or {}).get("page"),
        }
        for c in parents
    }
    if parent_map:
        with open(parents_path, "w", encoding="utf-8") as f:
            json.dump(parent_map, f, ensure_ascii=False)

    index_file, metadata_file = FAISSVectorStore.artifact_names(strategy_id)
    logger.info(
        "Index saved to %s/%s (+ %s, %s parents in %s) — %s chunks",
        output_dir,
        index_file,
        metadata_file,
        len(parent_map),
        parents_path.name,
        total_indexed,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed document chunks and build FAISS index")
    parser.add_argument("--input", default=getattr(config, "processed_data_dir", "./data/processed"), help="Directory of processed chunks (a per-strategy subdirectory is used inside it)")
    parser.add_argument("--output", default=getattr(config, "vector_store_path", "./models/vectorstore"), help="Output directory for FAISS index")
    parser.add_argument("--strategy", default=getattr(config, "chunk_strategy", "flat_baseline"), help="Chunking strategy: flat_baseline (alias flat_512) or hierarchical")
    parser.add_argument("--model", default=getattr(config, "embedding_model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"), help="Sentence-transformers model name")
    parser.add_argument("--device", default=getattr(config, "embedding_device", "cpu"), help="Device: cpu or cuda")
    parser.add_argument("--batch-size", type=int, default=32, help="Chunks per embedding batch")

    args = parser.parse_args()

    index_documents(
        input_dir=args.input,
        output_dir=args.output,
        model_name=args.model,
        device=args.device,
        batch_size=args.batch_size,
        strategy=args.strategy,
    )
