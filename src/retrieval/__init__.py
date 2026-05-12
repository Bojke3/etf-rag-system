"""Retrieval layer - Document retrieval and ranking"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Retriever(ABC):
    """Abstract base class for retrievers"""
    
    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant documents"""
        pass

class SimpleRetriever(Retriever):
    """Simple retriever using embedding similarity"""
    
    def __init__(self, embedding_model, vector_store):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve documents similar to query"""
        try:
            query_embedding = self.embedding_model.embed_text(query)
            results = self.vector_store.search(query_embedding, top_k)
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

class ContextBuilder:
    """Build context from retrieved documents"""
    
    @staticmethod
    def build_context(retrieved_docs: List[Dict], max_length: int = 2000) -> str:
        """Build context string from retrieved documents"""
        context_parts = []
        total_length = 0
        
        for doc in retrieved_docs:
            if 'text' in doc:
                text = doc['text']
                if total_length + len(text) <= max_length:
                    context_parts.append(text)
                    total_length += len(text)
                else:
                    # Truncate to fit
                    remaining = max_length - total_length
                    if remaining > 100:
                        context_parts.append(text[:remaining])
                    break
        
        return "\n\n".join(context_parts)
