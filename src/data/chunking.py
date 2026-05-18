from dataclasses import dataclass
from typing import List, Dict, Any

from .document import Document


@dataclass
class Chunk:
    text: str
    metadata: Dict[str, Any]


class SimpleChunker:
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, document: Document) -> List[Chunk]:
        text = document.text
        chunks = []

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end].strip()

            if chunk_text:
                metadata = {
                    **document.metadata,
                    "chunk_index": chunk_index,
                }

                chunks.append(
                    Chunk(
                        text=chunk_text,
                        metadata=metadata,
                    )
                )

                chunk_index += 1

            start += self.chunk_size - self.overlap

        return chunks