"""Script to process documents"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DocumentLoaderFactory
from src.config import config
from src.utils import setup_logging, ensure_directories, get_file_paths

setup_logging()
logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text into overlapping chunks by character count."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def process_documents(input_dir: str, output_dir: str, chunk_size: int = 512, overlap: int = 100):
    """Process documents from input directory, chunking each into numbered segments."""

    ensure_directories([output_dir])

    doc_files = get_file_paths(
        input_dir,
        extensions=['*.pdf', '*.docx', '*.doc', '*.txt']
    )

    logger.info(f"Found {len(doc_files)} documents to process")

    processed_count = 0
    for file_path in doc_files:
        try:
            logger.info(f"Processing: {file_path}")

            text = DocumentLoaderFactory.load_document(file_path)
            chunks = chunk_text(text, chunk_size, overlap)

            stem = Path(file_path).stem
            for i, chunk in enumerate(chunks):
                output_path = Path(output_dir) / f"{stem}_chunk{i:04d}.txt"
                output_path.write_text(chunk, encoding="utf-8")

            logger.info(f"Saved {len(chunks)} chunks for: {file_path}")
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    logger.info(f"Processed {processed_count}/{len(doc_files)} documents")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process documents")
    parser.add_argument("--input", default=config.data_dir, help="Input directory")
    parser.add_argument("--output", default=config.processed_data_dir, help="Output directory")
    parser.add_argument("--chunk-size", type=int, default=512, help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=100, help="Overlap between chunks in characters")

    args = parser.parse_args()

    process_documents(args.input, args.output, args.chunk_size, args.overlap)
