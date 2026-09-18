"""Script to embed chunked documents and build the FAISS vector index.

Two chunk layouts are supported and auto-detected (override with ``--mode``):

**strategy** — chunks written by ``process_documents.py`` as ``chunks.jsonl``
inside a per-strategy subdirectory. Each chunking strategy gets its own index
artifacts, so they never mix::

    python scripts/index_documents.py
    python scripts/index_documents.py --strategy hierarchical

    models/vectorstore/index_<strategy>.faiss
    models/vectorstore/metadatas_<strategy>.json
    models/vectorstore/parents_<strategy>.json   (hierarchical only, NOT embedded)

For hierarchical chunking only child chunks are embedded; parents are written to
the sidecar above and looked up by id at retrieval time to supply extra context.

**staged** — stage 3 of the three-stage pipeline, reading the hash-verified
``<document>_chunk<NNNN>.txt`` set produced by ``chunk_documents.py``. Writes the
historical ``index.faiss`` / ``metadatas.json`` pair plus an indexing manifest
recording the embedding settings and input hashes (see docs/DATA_PIPELINE.md)::

    python scripts/index_documents.py --input data/chunks --output models/vectorstore_new
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.chunking import LEVEL_CHILD, LEVEL_FLAT, LEVEL_PARENT, Chunk, resolve_strategy_id
from src.data.stages import file_hash, prepare_output, read_manifest, verified_file, write_manifest
from src.utils import ensure_directories, get_file_paths, setup_logging

try:
    from src.config import config
except ImportError:
    config = None

setup_logging()
logger = logging.getLogger(__name__)

# Matches filenames like "syllabus_chunk0001.txt" produced by either chunker
_CHUNK_RE = re.compile(r"^(.+)_chunk(\d+)$")

CHUNKS_FILE = "chunks.jsonl"
#: Levels that get embedded into the vector index.
EMBEDDED_LEVELS = (LEVEL_FLAT, LEVEL_CHILD)

MODE_STRATEGY = "strategy"
MODE_STAGED = "staged"


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


def detect_mode(input_dir: str, strategy_id: str) -> str:
    """Pick the chunk layout for ``input_dir``.

    A chunking manifest is conclusive, but it no longer implies one layout:
    ``chunk_documents.py`` records a ``chunks`` list of per-chunk ``.txt``
    files, while a strategy build records ``chunks_file`` pointing at a
    ``chunks.jsonl``. Route on which of the two the manifest carries. Otherwise
    a chunks.jsonl or a per-strategy subdirectory means strategy layout, as does
    a legacy flat directory of ``<stem>_chunk<NNNN>.txt`` files. Anything else
    falls to the staged path, which validates chunk filenames and so refuses a
    directory of raw or cleaned document text. Use ``--mode`` to override.
    """
    source = Path(input_dir)
    manifest_path = source / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return MODE_STAGED
        return MODE_STRATEGY if manifest.get("chunks_file") else MODE_STAGED
    if (source / strategy_id / CHUNKS_FILE).exists() or (source / CHUNKS_FILE).exists():
        return MODE_STRATEGY
    if (source / strategy_id).is_dir():
        return MODE_STRATEGY
    # A legacy flat directory of <stem>_chunk<NNNN>.txt keeps the historical
    # per-strategy behaviour. Anything else falls to the staged path, whose
    # filename validation rejects raw or cleaned document text.
    texts = get_file_paths(str(source), extensions=["*.txt"]) if source.is_dir() else []
    if texts and all(_CHUNK_RE.match(Path(p).stem) for p in texts):
        return MODE_STRATEGY
    return MODE_STAGED


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


def _load_embedding(model_name: str, device: str):
    # Imported here, not at module scope, so the heavy embedding stack loads
    # only when indexing actually runs.
    from src.embedding import FAISSVectorStore, SentenceTransformerEmbedding

    logger.info(f"Loading embedding model: {model_name} (device={device})")
    embedding_model = SentenceTransformerEmbedding(model_name=model_name, device=device)
    return embedding_model, FAISSVectorStore(embedding_dim=embedding_model.embedding_dim)


def index_strategy_chunks(
    input_dir: str,
    output_dir: str,
    model_name: str,
    device: str,
    batch_size: int,
    strategy_id: str,
) -> None:
    """Index chunks.jsonl (or legacy .txt) into per-strategy index artifacts."""
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

    embedding_model, vector_store = _load_embedding(model_name, device)
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

    # Strategy builds used to leave no index manifest, so provenance recorded a
    # null index_manifest_sha256 for them while staged builds recorded one.
    chunk_manifest_path = Path(input_dir) / "manifest.json"
    write_manifest(output_dir, {
        "schema_version": 1,
        "stage": "indexing",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "chunk_directory": str(source_dir),
        "chunk_manifest_sha256": (file_hash(chunk_manifest_path)
                                  if chunk_manifest_path.is_file() else None),
        "settings": {"embedding_model": model_name, "device": device,
                     "batch_size": batch_size, "strategy": strategy_id},
        "embedding_dimension": int(embedding_model.embedding_dim),
        "chunk_count": total_indexed,
        "parent_count": len(parent_map),
        "artifacts": {name: file_hash(Path(output_dir) / name)
                      for name in sorted(p.name for p in Path(output_dir).glob("*")
                                         if p.is_file() and p.name != "manifest.json")},
    })

    from src.embedding import FAISSVectorStore

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


def index_staged_chunks(
    input_dir: str,
    output_dir: str,
    model_name: str,
    device: str,
    batch_size: int,
) -> None:
    """Stage 3: index a hash-verified chunk directory and record a manifest."""
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

    embedding_model, vector_store = _load_embedding(model_name, device)

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


def index_documents(
    input_dir: str,
    output_dir: str,
    model_name: str,
    device: str,
    batch_size: int,
    strategy: Optional[str] = None,
    mode: str = "auto",
) -> None:
    """Embed chunks into a FAISS index, dispatching on the chunk layout."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    strategy_id = resolve_strategy_id(strategy)
    resolved = detect_mode(input_dir, strategy_id) if mode == "auto" else mode
    logger.info("Chunk layout: %s (mode=%s)", resolved, mode)

    if resolved == MODE_STAGED:
        index_staged_chunks(input_dir, output_dir, model_name, device, batch_size)
    else:
        index_strategy_chunks(input_dir, output_dir, model_name, device, batch_size, strategy_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed document chunks and build FAISS index")
    parser.add_argument("--input", default=getattr(config, "processed_data_dir", "./data/processed"), help="Directory of chunks: a per-strategy subdirectory (strategy mode) or a chunk_documents.py output (staged mode)")
    parser.add_argument("--output", default=getattr(config, "vector_store_path", "./models/vectorstore"), help="Output directory for FAISS index")
    parser.add_argument("--strategy", default=getattr(config, "chunk_strategy", "flat_baseline"), help="Chunking strategy: flat_baseline (alias flat_512) or hierarchical")
    parser.add_argument("--mode", choices=["auto", MODE_STRATEGY, MODE_STAGED], default="auto", help="Chunk layout; auto detects a chunking manifest or chunks.jsonl")
    parser.add_argument("--model", default=getattr(config, "embedding_model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"), help="Sentence-transformers model name")
    parser.add_argument("--device", default=getattr(config, "embedding_device", "cpu"), help="Device: cpu or cuda")
    parser.add_argument("--batch-size", type=int, default=32, help="Chunks per embedding batch")

    args = parser.parse_args()

    try:
        index_documents(
            input_dir=args.input,
            output_dir=args.output,
            model_name=args.model,
            device=args.device,
            batch_size=args.batch_size,
            strategy=args.strategy,
            mode=args.mode,
        )
    except Exception as exc:
        logger.error("Indexing failed: %s", exc)
        sys.exit(1)
