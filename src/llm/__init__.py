"""LLM integration layer - Local and cloud LLM models"""

from .base import LLMClient
from .ollama import OllamaClient
from .prompts import PromptTemplate

__all__ = [
    "LLMClient",
    "OllamaClient",
    "PromptTemplate",
]
