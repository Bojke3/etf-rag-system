"""Embedding layer - Vector representations and storage"""

from .base import EmbeddingModel, VectorStore
from .faiss_store import FAISSVectorStore
from .sentence_transformer import SentenceTransformerEmbedding

__all__ = [
    "EmbeddingModel",
    "VectorStore",
    "FAISSVectorStore",
    "SentenceTransformerEmbedding",
]
