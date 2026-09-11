"""Retriever that expands hierarchical child hits to their parent chunks.

Children are what get embedded (they are small and specific, so they match a
question well); parents are what the LLM should actually read (they carry the
surrounding article so the answer is not cut off at a chunk boundary).

Two children of the same parent collapse into that parent once, so the context
is not padded with duplicate text.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from .base import Retriever

logger = logging.getLogger(__name__)


def load_parent_store(path: str, strategy_id: str) -> Dict[str, Dict]:
    """Load parents_<strategy>.json, or an empty map when there is none."""
    parents_path = Path(path) / f"parents_{strategy_id}.json"

    if not parents_path.exists():
        # Normal for flat strategies, which have no parent level at all.
        logger.debug("No parent store at %s — child chunks will be used as-is", parents_path)
        return {}

    try:
        with open(parents_path, encoding="utf-8") as f:
            store = json.load(f)
        logger.info("Loaded %s parent chunks from %s", len(store), parents_path)
        return store
    except Exception as e:
        logger.error("Failed to load parent store %s: %s", parents_path, e)
        return {}


class ParentAwareRetriever(Retriever):
    """Wraps another retriever and swaps child hits for their parents."""

    def __init__(self, retriever: Retriever, parent_store: Optional[Dict[str, Dict]] = None):
        self.retriever = retriever
        self.parent_store = parent_store or {}

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        results = self.retriever.retrieve(query, top_k)

        if not self.parent_store:
            return results

        expanded: List[Dict] = []
        seen_parents = set()

        for result in results:
            parent_id = result.get("parent_chunk_id")
            parent = self.parent_store.get(parent_id) if parent_id else None

            if parent is None:
                expanded.append(result)
                continue

            if parent_id in seen_parents:
                # Another child of this parent already contributed the text.
                continue
            seen_parents.add(parent_id)

            merged = dict(result)
            merged["text"] = parent.get("text", result.get("text", ""))
            # Keep the child's identity and score — that is what actually matched.
            merged["matched_chunk_id"] = result.get("id")
            merged["expanded_to_parent"] = True
            for key in ("section", "page"):
                if parent.get(key) is not None:
                    merged[key] = parent[key]
            expanded.append(merged)

        return expanded
