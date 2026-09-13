"""Stage 1: extract document text once, with the existing OCR fallback."""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.stages import extract_documents
from src.utils import setup_logging


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="DataAkti", help="Directory containing original documents")
    parser.add_argument("--output", default="data/extracted", help="New or empty snapshot directory")
    parser.add_argument("--no-ocr", action="store_true", help="Disable OCR fallback")
    parser.add_argument("--ocr-max-pages", type=int, help="Limit OCR to the first N pages")
    parser.add_argument("--ocr-languages", help="Comma-separated EasyOCR languages, e.g. rs_cyrillic,en")
    args = parser.parse_args()
    setup_logging()
    try:
        extract_documents(args.input, args.output, not args.no_ocr,
                          args.ocr_max_pages, args.ocr_languages)
    except Exception as exc:
        logging.getLogger(__name__).error("Extraction failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
