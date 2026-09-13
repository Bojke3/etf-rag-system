"""Stage 2: chunk a saved extraction snapshot without running OCR."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.stages import chunk_documents
from src.utils import setup_logging


def main():
    try:
        from src.config import config
    except ImportError:
        config = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/extracted", help="Snapshot directory from extract_documents.py")
    parser.add_argument("--output", default="data/chunks", help="New or empty chunk directory")
    parser.add_argument("--chunk-size", type=int, default=getattr(config, "chunk_size", 1024), help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=getattr(config, "chunk_overlap", 150), help="Overlap in characters")
    args = parser.parse_args()
    setup_logging()
    try:
        chunk_documents(args.input, args.output, args.chunk_size, args.overlap)
    except Exception as exc:
        logging.getLogger(__name__).error("Chunking failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
