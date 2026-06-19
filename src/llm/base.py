"""Base interfaces for LLM clients."""

from abc import ABC, abstractmethod
from typing import List


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from prompt"""
        pass

    @abstractmethod
    def list_available_models(self) -> List[str]:
        """List available models"""
        pass
