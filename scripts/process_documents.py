"""Script to process documents"""

import argparse
import logging
import os
import sys
from pathlib import Path

# Ensure repo root is on the path when running this script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data import DocumentLoaderFactory, SimpleChunker, TextPreprocessor
from src.utils import setup_logging, ensure_directories, get_file_paths

try:
    from src.config import config
except ImportError:
    config = None

setup_logging()
logger = logging.getLogger(__name__)


def process_documents(
    input_dir: str,
    output_dir: str,
    chunk_size: int = 512,
    overlap: int = 100,
    enable_ocr: bool = True,
    ocr_max_pages: int | None = None,
    ocr_languages: str | None = None,
):
    """Process documents from input directory, chunking each into numbered segments."""

    os.environ["ETF_RAG_ENABLE_OCR"] = "1" if enable_ocr else "0"
    if ocr_max_pages:
        os.environ["ETF_RAG_OCR_MAX_PAGES"] = str(ocr_max_pages)
    else:
        os.environ.pop("ETF_RAG_OCR_MAX_PAGES", None)

    if ocr_languages:
        os.environ["ETF_RAG_OCR_LANGUAGES"] = ocr_languages
    else:
        os.environ.pop("ETF_RAG_OCR_LANGUAGES", None)

    ensure_directories([output_dir])
    preprocessor = TextPreprocessor()
    chunker = SimpleChunker(chunk_size=chunk_size, overlap=overlap)

    doc_files = get_file_paths(
        input_dir,
        extensions=['*.pdf', '*.docx', '*.doc', '*.txt']
    )

    logger.info(f"Found {len(doc_files)} documents to process")

    processed_count = 0
    for file_path in doc_files:
        try:
            logger.info(f"Processing: {file_path}")

            document = DocumentLoaderFactory.load_document(file_path)
            document.text = preprocessor.clean(document.text)
            chunks = chunker.split(document)

            stem = Path(file_path).stem
            for i, chunk in enumerate(chunks):
                output_path = Path(output_dir) / f"{stem}_chunk{i:04d}.txt"
                output_path.write_text(chunk.text, encoding="utf-8")

            logger.info(f"Saved {len(chunks)} chunks for: {file_path}")
            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")

    logger.info(f"Processed {processed_count}/{len(doc_files)} documents")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process documents")
    parser.add_argument("--input", default=getattr(config, "data_dir", "./data/documents"), help="Input directory")
    parser.add_argument("--output", default=getattr(config, "processed_data_dir", "./data/processed"), help="Output directory")

    parser.add_argument("--chunk-size", type=int, default=getattr(config, "chunk_size", 512), help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=getattr(config, "chunk_overlap", 100), help="Overlap between chunks in characters")

    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback for scanned PDFs")
    parser.add_argument("--ocr-max-pages", type=int, help="OCR only the first N pages of each PDF")
    parser.add_argument(
        "--ocr-languages",
        help="Comma-separated EasyOCR languages, for example: rs_cyrillic,en",
    )

    args = parser.parse_args()

    process_documents(
        input_dir=args.input,
        output_dir=args.output,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        enable_ocr=not args.no_ocr,
        ocr_max_pages=args.ocr_max_pages,
        ocr_languages=args.ocr_languages,
    )
