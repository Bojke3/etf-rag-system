"""Sentence Transformers embedding implementation."""

from typing import List
import logging

import numpy as np

from .base import EmbeddingModel

logger = logging.getLogger(__name__)


class SentenceTransformerEmbedding(EmbeddingModel):
    """Embedding using Sentence Transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name, device=device)
            self.model_name = model_name
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise

    def embed_text(self, text: str) -> np.ndarray:
        """Embed single text"""
        return self.model.encode(text, convert_to_numpy=True)

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts"""
        return self.model.encode(texts, convert_to_numpy=True)

    @property
    def embedding_dim(self) -> int:
        """Return embedding dimension"""
        return self.model.get_sentence_embedding_dimension()
