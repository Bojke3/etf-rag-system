"""Base interfaces for embedding models and vector stores."""

from abc import ABC, abstractmethod
from typing import Dict, List

import numpy as np


class EmbeddingModel(ABC):
    """Abstract base class for embedding models"""

    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Embed single text"""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts"""
        pass

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return embedding dimension"""
        pass


class VectorStore(ABC):
    """Abstract base class for vector stores"""

    @abstractmethod
    def add(self, embeddings: np.ndarray, metadatas: List[Dict]) -> None:
        """Add embeddings to store"""
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Search similar embeddings"""
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """Save vector store"""
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """Load vector store"""
        pass
