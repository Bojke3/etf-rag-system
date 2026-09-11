"""Flat fixed-width chunking -- the original baseline strategy.

This is the sliding window the project has always used: 1024 *characters* with
150 characters of overlap (see DECISIONS.md D4/D5 -- 512 was rejected because it
cut Serbian legal sentences mid-predicate).  The strategy id is
``flat_baseline``; ``flat_512`` is accepted as an alias for it in the registry.

The loop below is deliberately identical to the pre-refactor ``SimpleChunker``
so that, with OCR cleanup disabled, output is byte-for-byte what it was before.
"""

from typing import List

from ..document import Document
from .base import LEVEL_FLAT, Chunk, ChunkingStrategy, document_slug, make_chunk_id
from .splitters import PAGE_SEPARATOR, page_for_offset, section_for_offset


class FlatChunker(ChunkingStrategy):
    """Fixed-width character sliding window."""

    strategy_id = "flat_baseline"

    def __init__(self, chunk_size: int = 1024, overlap: int = 200):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: Document) -> List[Chunk]:
        text = document.text
        slug = document_slug(document)
        chunks: List[Chunk] = []

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size
            raw = text[start:end]
            chunk_text = raw.strip()

            if chunk_text:
                metadata = self.build_metadata(
                    document,
                    chunk_index=chunk_index,
                    char_start=start,
                    char_end=min(end, len(text)),
                    page=page_for_offset(text, start),
                    section=section_for_offset(text, start),
                )

                chunks.append(
                    Chunk(
                        text=chunk_text.replace(PAGE_SEPARATOR, "\n"),
                        metadata=metadata,
                        chunk_id=make_chunk_id(slug, self.strategy_id, LEVEL_FLAT, chunk_index),
                        parent_chunk_id=None,
                        strategy_id=self.strategy_id,
                        level=LEVEL_FLAT,
                    )
                )

                chunk_index += 1

            start += self.chunk_size - self.overlap

        return chunks


class SimpleChunker(FlatChunker):
    """Deprecated alias kept so existing imports and ``.split()`` calls work."""
