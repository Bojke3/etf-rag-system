"""Compatibility entry point for stage 2; extraction now uses extract_documents.py.

Input must be an extraction snapshot, not a directory of PDFs.
Prefer scripts/chunk_documents.py for new commands.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.chunk_documents import main
from src.data.stages import chunk_documents as process_documents


if __name__ == "__main__":
    sys.exit(main())
