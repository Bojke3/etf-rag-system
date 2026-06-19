"""Base interfaces for document retrieval."""

from abc import ABC, abstractmethod
from typing import Dict, List


class Retriever(ABC):
    """Abstract base class for retrievers"""

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve relevant documents"""
        pass
