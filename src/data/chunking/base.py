"""Chunk data model and the chunking strategy interface.

Every chunking strategy implements :class:`ChunkingStrategy` and returns a flat
list of :class:`Chunk` objects.  Strategies that build a hierarchy (see
``hierarchical.py``) return both parents and children in that single list and
distinguish them via the ``level`` field -- callers decide which levels get
embedded.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pathlib
import re

from ..document import Document

# Levels a chunk can occupy in its strategy's hierarchy.
LEVEL_FLAT = "flat"
LEVEL_PARENT = "parent"
LEVEL_CHILD = "child"

# Metadata keys every strategy is expected to populate (None when unavailable).
STANDARD_METADATA_KEYS = (
    "document",
    "source",
    "file_name",
    "file_type",
    "ocr_used",
    "subject",
    "section",
    "page",
    "chunk_index",
    "char_start",
    "char_end",
)

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def document_stem(document: Document) -> str:
    """The document's file name without extension, verbatim.

    This is what ``scripts/index_documents.py`` has always derived from chunk
    file names and what ``benchmarking/*.json`` records as ``source_document``,
    so it must keep its spaces and original casing.
    """
    name = document.metadata.get("file_name") or document.metadata.get("source") or "doc"
    return str(pathlib.PurePath(str(name)).stem) or "doc"


def document_slug(document: Document) -> str:
    """Filesystem/id-safe identifier for a document, used inside chunk ids."""
    return _SLUG_RE.sub("_", document_stem(document)).strip("_") or "doc"


def make_chunk_id(doc_slug: str, strategy_id: str, level: str, index: int) -> str:
    """Chunk ids are stable across rebuilds as long as the document text is unchanged."""
    return f"{doc_slug}::{strategy_id}::{level}::{index:04d}"


@dataclass
class Chunk:
    """A unit of text to be embedded or used as retrieval context.

    ``text`` and ``metadata`` stay first and required so that existing
    positional construction (``Chunk(text=..., metadata=...)``) keeps working.
    """

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    chunk_id: str = ""
    parent_chunk_id: Optional[str] = None
    strategy_id: str = ""
    level: str = LEVEL_FLAT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "parent_chunk_id": self.parent_chunk_id,
            "strategy_id": self.strategy_id,
            "level": self.level,
            "text": self.text,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chunk":
        return cls(
            text=data.get("text", ""),
            metadata=data.get("metadata", {}) or {},
            chunk_id=data.get("chunk_id", ""),
            parent_chunk_id=data.get("parent_chunk_id"),
            strategy_id=data.get("strategy_id", ""),
            level=data.get("level", LEVEL_FLAT),
        )


class ChunkingStrategy(ABC):
    """Interface every chunking strategy implements."""

    #: Identifier used for config selection and for naming build artifacts.
    strategy_id: str = ""

    @abstractmethod
    def chunk(self, document: Document) -> List[Chunk]:
        """Split ``document`` into chunks carrying the standard metadata."""

    # Backwards-compatible alias: the original chunker exposed ``split()``.
    def split(self, document: Document) -> List[Chunk]:
        return self.chunk(document)

    def build_metadata(
        self,
        document: Document,
        chunk_index: int,
        char_start: int,
        char_end: int,
        page: Optional[int] = None,
        section: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Merge document metadata with the per-chunk standard keys."""
        metadata = dict(document.metadata)
        metadata.setdefault("document", document_stem(document))
        metadata.update(
            {
                "chunk_index": chunk_index,
                "char_start": char_start,
                "char_end": char_end,
                "page": page,
                "section": section,
                "subject": subject if subject is not None else metadata.get("subject"),
                "strategy_id": self.strategy_id,
            }
        )
        return metadata
