"""Hierarchical (parent-child) chunking.

Parents are large, semantically coherent blocks that are *not* embedded -- they
are looked up by id at retrieval time to give the LLM more context around a hit.
Children are small, embedded, and each carries its parent's id.

Sizes are in characters (nothing here is token-aware).  The task specified
1024-1536 tokens for parents and 256-384 for children; at ~3.5 chars/token for
Serbian that is ~3600-5400 and ~900-1350 characters respectively.
"""

from typing import List, Optional, Tuple

from ..document import Document
from .base import (
    LEVEL_CHILD,
    LEVEL_PARENT,
    Chunk,
    ChunkingStrategy,
    document_slug,
    make_chunk_id,
)
from .splitters import (
    PAGE_SEPARATOR,
    HEADING_RE,
    find_atomic_spans,
    page_for_offset,
    recursive_split,
    section_for_offset,
)


class HierarchicalChunker(ChunkingStrategy):
    """Two-level chunker: section-aware parents, overlapping children."""

    strategy_id = "hierarchical"

    def __init__(
        self,
        parent_size: int = 4500,
        parent_min: int = 3600,
        child_size: int = 1200,
        child_min: int = 900,
        child_overlap_ratio: float = 0.12,
    ):
        if child_size >= parent_size:
            raise ValueError("child_size must be smaller than parent_size")
        if not 0.0 <= child_overlap_ratio < 0.5:
            raise ValueError("child_overlap_ratio must be in [0.0, 0.5)")

        self.parent_size = parent_size
        self.parent_min = min(parent_min, parent_size)
        self.child_size = child_size
        self.child_min = min(child_min, child_size)
        self.child_overlap = int(child_size * child_overlap_ratio)

    # -- parents ---------------------------------------------------------

    def _section_spans(self, text: str) -> List[Tuple[int, int]]:
        """Split the document at heading cues; falls back to the whole text."""
        starts = [m.start() for m in HEADING_RE.finditer(text)]
        if not starts or starts[0] != 0:
            starts = [0] + starts

        spans = []
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < len(starts) else len(text)
            if end > start:
                spans.append((start, end))
        return spans

    def _parent_spans(self, text: str, atomic_spans) -> List[Tuple[int, int]]:
        """Pack consecutive sections up to the parent target size."""
        parents: List[Tuple[int, int]] = []
        current_start: Optional[int] = None
        current_end = 0

        for start, end in self._section_spans(text):
            length = end - start

            if length > self.parent_size:
                # Oversized section: flush what we have, then split it.
                if current_start is not None:
                    parents.append((current_start, current_end))
                    current_start = None
                parents.extend(
                    recursive_split(
                        text[start:end],
                        self.parent_size,
                        self.parent_min,
                        atomic_spans,
                        offset=start,
                    )
                )
                continue

            if current_start is None:
                current_start, current_end = start, end
            elif current_end - current_start + length <= self.parent_size:
                current_end = end
            else:
                parents.append((current_start, current_end))
                current_start, current_end = start, end

        if current_start is not None:
            parents.append((current_start, current_end))

        return [(s, e) for s, e in parents if text[s:e].strip()]

    # -- children --------------------------------------------------------

    def _child_spans(self, text: str, parent_start: int, parent_end: int, atomic_spans):
        """Split one parent into overlapping children, never crossing its bounds."""
        body = text[parent_start:parent_end]
        base = recursive_split(
            body, self.child_size, self.child_min, atomic_spans, offset=parent_start
        )

        if self.child_overlap <= 0:
            return base

        overlapped = []
        for i, (start, end) in enumerate(base):
            # Extend backwards into the previous child, but stay inside the parent.
            start = parent_start if i == 0 else max(parent_start, start - self.child_overlap)
            overlapped.append((start, end))
        return overlapped

    # -- entry point -----------------------------------------------------

    def chunk(self, document: Document) -> List[Chunk]:
        text = document.text
        if not text.strip():
            return []

        slug = document_slug(document)
        atomic_spans = find_atomic_spans(text)
        chunks: List[Chunk] = []
        child_index = 0

        for parent_index, (p_start, p_end) in enumerate(self._parent_spans(text, atomic_spans)):
            parent_text = text[p_start:p_end].strip()
            if not parent_text:
                continue

            parent_id = make_chunk_id(slug, self.strategy_id, LEVEL_PARENT, parent_index)
            section = section_for_offset(text, p_start + 1)
            page = page_for_offset(text, p_start)

            chunks.append(
                Chunk(
                    text=parent_text.replace(PAGE_SEPARATOR, "\n"),
                    metadata=self.build_metadata(
                        document,
                        chunk_index=parent_index,
                        char_start=p_start,
                        char_end=p_end,
                        page=page,
                        section=section,
                    ),
                    chunk_id=parent_id,
                    parent_chunk_id=None,
                    strategy_id=self.strategy_id,
                    level=LEVEL_PARENT,
                )
            )

            for c_start, c_end in self._child_spans(text, p_start, p_end, atomic_spans):
                child_text = text[c_start:c_end].strip()
                if not child_text:
                    continue

                metadata = self.build_metadata(
                    document,
                    chunk_index=child_index,
                    char_start=c_start,
                    char_end=c_end,
                    page=page_for_offset(text, c_start),
                    section=section_for_offset(text, c_start + 1) or section,
                )
                metadata["parent_chunk_id"] = parent_id

                chunks.append(
                    Chunk(
                        text=child_text.replace(PAGE_SEPARATOR, "\n"),
                        metadata=metadata,
                        chunk_id=make_chunk_id(
                            slug, self.strategy_id, LEVEL_CHILD, child_index
                        ),
                        parent_chunk_id=parent_id,
                        strategy_id=self.strategy_id,
                        level=LEVEL_CHILD,
                    )
                )
                child_index += 1

        return chunks
