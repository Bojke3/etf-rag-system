"""Script to process documents.

Two inputs are accepted and auto-detected:

**Documents** (PDF/DOCX/TXT) — extraction, OCR and strategy-aware chunking in
one pass::

    python scripts/process_documents.py --input DataAkti --output data/processed --strategy flat_baseline --ocr-languages rs_cyrillic,en

Chunks land in a per-strategy subdirectory (``<output>/<strategy_id>/``) so two
chunking strategies can coexist as separate build artifacts:

    chunks.jsonl                 canonical: full chunk records with metadata
    <stem>_chunk<NNNN>.txt       flat strategies only, for eyeballing / legacy

**An extraction snapshot** from ``extract_documents.py`` — this script then acts
as stage 2 of the three-stage pipeline and delegates to ``chunk_documents.py``,
which re-chunks the frozen text without re-running OCR and writes a chunk
manifest. OCR flags belong to ``extract_documents.py`` in that flow; prefer
``scripts/chunk_documents.py`` for new commands. See docs/DATA_PIPELINE.md.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DocumentLoaderFactory, TextPreprocessor
from src.data.chunking import DEFAULT_STRATEGY, LEVEL_FLAT, get_chunker, resolve_strategy_id
from src.utils import setup_logging, ensure_directories, get_file_paths

try:
    from src.config import config
except ImportError:
    config = None

setup_logging()
logger = logging.getLogger(__name__)

CHUNKS_FILE = "chunks.jsonl"


def is_extraction_snapshot(input_dir: str) -> bool:
    """True for an extract_documents.py snapshot rather than raw documents."""
    source = Path(input_dir)
    return (source / "manifest.json").exists() and (source / "cleaned").is_dir()


def process_documents(
    input_dir: str,
    output_dir: str,
    strategy: Optional[str] = None,
    chunk_size: int = 1000,
    overlap: int = 150,
    enable_ocr: bool = True,
    ocr_max_pages: Optional[int] = None,
    ocr_languages: Optional[str] = None,
    ocr_cleanup: bool = True,
):
    """Process documents from input directory, chunking each with one strategy."""

    if is_extraction_snapshot(input_dir):
        # Stage 2 of the three-stage pipeline: the text is already frozen and
        # hash-verified, so re-running extraction or OCR here would defeat it.
        # A strategy is honoured here rather than dropped -- silently returning
        # flat chunks for --strategy hierarchical is how a chunking comparison
        # ends up measuring nothing.
        strategy_id = resolve_strategy_id(strategy)

        if strategy_id == DEFAULT_STRATEGY:
            # Keeps stage 2 byte-identical to the chunk set the existing indexes
            # were built from; one .txt per chunk, as chunk_documents.py writes.
            from src.data.stages import chunk_documents as chunk_snapshot

            logger.info("Input is an extraction snapshot — flat chunking without re-running OCR")
            chunk_snapshot(input_dir, output_dir, chunk_size, overlap)
            return

        from src.data.stages import chunk_snapshot_with_strategy

        logger.info(
            "Input is an extraction snapshot — chunking with strategy=%s without re-running OCR",
            strategy_id,
        )
        chunk_snapshot_with_strategy(
            input_dir, output_dir, strategy_id, config,
            chunk_size=chunk_size, chunk_overlap=overlap,
        )
        return

    os.environ["ETF_RAG_ENABLE_OCR"] = "1" if enable_ocr else "0"
    if ocr_max_pages:
        os.environ["ETF_RAG_OCR_MAX_PAGES"] = str(ocr_max_pages)
    else:
        os.environ.pop("ETF_RAG_OCR_MAX_PAGES", None)

    if ocr_languages:
        os.environ["ETF_RAG_OCR_LANGUAGES"] = ocr_languages
    else:
        os.environ.pop("ETF_RAG_OCR_LANGUAGES", None)

    strategy_id = resolve_strategy_id(strategy)
    strategy_dir = Path(output_dir) / strategy_id
    ensure_directories([str(strategy_dir)])

    preprocessor = TextPreprocessor(ocr_cleanup=ocr_cleanup)
    chunker = get_chunker(
        strategy_id, config, chunk_size=chunk_size, chunk_overlap=overlap
    )

    logger.info(
        "Chunking strategy=%s ocr_cleanup=%s output=%s",
        strategy_id,
        ocr_cleanup,
        strategy_dir,
    )

    doc_files = get_file_paths(
        input_dir,
        extensions=['*.pdf', '*.docx', '*.doc', '*.txt']
    )

    logger.info(f"Found {len(doc_files)} documents to process")

    processed_count = 0
    total_chunks = 0
    chunks_path = strategy_dir / CHUNKS_FILE

    with open(chunks_path, "w", encoding="utf-8") as chunks_file:
        for file_path in doc_files:
            try:
                logger.info(f"Processing: {file_path}")

                document = DocumentLoaderFactory.load_document(file_path)
                document.text = preprocessor.clean(document.text)
                chunks = chunker.chunk(document)

                stem = Path(file_path).stem
                flat_index = 0

                for chunk in chunks:
                    chunks_file.write(
                        json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n"
                    )

                    # Keep the historical one-file-per-chunk layout for flat
                    # strategies; a hierarchy does not map onto it.
                    if chunk.level == LEVEL_FLAT:
                        output_path = strategy_dir / f"{stem}_chunk{flat_index:04d}.txt"
                        output_path.write_text(chunk.text, encoding="utf-8")
                        flat_index += 1

                logger.info(f"Saved {len(chunks)} chunks for: {file_path}")
                total_chunks += len(chunks)
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")

    logger.info(
        "Processed %s/%s documents, %s chunks -> %s",
        processed_count,
        len(doc_files),
        total_chunks,
        chunks_path,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process documents")
    parser.add_argument("--input", default=getattr(config, "data_dir", "./data/documents"), help="Input directory")
    parser.add_argument("--output", default=getattr(config, "processed_data_dir", "./data/processed"), help="Output directory (a per-strategy subdirectory is created inside it)")

    parser.add_argument("--strategy", default=getattr(config, "chunk_strategy", "flat_baseline"), help="Chunking strategy: flat_baseline (alias flat_512) or hierarchical")
    parser.add_argument("--chunk-size", type=int, default=getattr(config, "chunk_size", 1000), help="Chunk size in characters (flat strategies)")
    parser.add_argument("--overlap", type=int, default=getattr(config, "chunk_overlap", 150), help="Overlap between chunks in characters (flat strategies)")

    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback for scanned PDFs")
    parser.add_argument("--no-ocr-cleanup", action="store_true", help="Disable OCR text repair (reproduces pre-cleanup chunk output)")
    parser.add_argument("--ocr-max-pages", type=int, help="OCR only the first N pages of each PDF")
    parser.add_argument(
        "--ocr-languages",
        help="Comma-separated EasyOCR languages, for example: rs_cyrillic,en",
    )

    args = parser.parse_args()

    cleanup_default = bool(getattr(config, "ocr_cleanup", True))

    process_documents(
        input_dir=args.input,
        output_dir=args.output,
        strategy=args.strategy,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        enable_ocr=not args.no_ocr,
        ocr_max_pages=args.ocr_max_pages,
        ocr_languages=args.ocr_languages,
        ocr_cleanup=False if args.no_ocr_cleanup else cleanup_default,
    )
