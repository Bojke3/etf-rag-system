"""Simple embedding-similarity retriever."""

from typing import Dict, List
import logging

from .base import Retriever

logger = logging.getLogger(__name__)


class SimpleRetriever(Retriever):
    """Simple retriever using embedding similarity"""

    def __init__(self, embedding_model, vector_store, threshold: float = 0.0):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.threshold = threshold

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve documents similar to query, filtered by score threshold"""
        try:
            query_embedding = self.embedding_model.embed_text(query)
            results = self.vector_store.search(query_embedding, top_k)
            return [r for r in results if r.get('score', 0.0) >= self.threshold]
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
