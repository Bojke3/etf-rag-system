"""Embedding layer - Vector representations and storage"""

from .base import EmbeddingModel, VectorStore
from .faiss_store import FAISSVectorStore
from .sentence_transformer import SentenceTransformerEmbedding
from .registry import find_by_index_dir, load_registry, resolve, verify_pairing

__all__ = [
    "EmbeddingModel",
    "VectorStore",
    "FAISSVectorStore",
    "SentenceTransformerEmbedding",
    "load_registry",
    "resolve",
    "find_by_index_dir",
    "verify_pairing",
]
