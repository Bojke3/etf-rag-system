"""LLM integration layer - Local and cloud LLM models"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

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

class OllamaClient(LLMClient):
    """Client for local Ollama models"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral"):
        self.base_url = base_url
        self.model = model
        self.session = None
    
    def generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048, **kwargs) -> str:
        """Generate response using Ollama"""
        try:
            import requests
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""
    
    def list_available_models(self) -> List[str]:
        """List available Ollama models"""
        try:
            import requests
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m.get('name', '') for m in models]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
        return []

class PromptTemplate:
    """Prompt template builder"""
    
    ZERO_SHOT = """Ti si asistent koji odgovara na pitanja o ETF fakultetu. Odgovori ISKLJUČIVO na osnovu datog konteksta. Ako odgovor nije u kontekstu, reci "Nisam pronašao odgovor u dostupnim dokumentima." Koristi latinično pismo. Ne izmišljaj informacije.

Pitanje: {question}
Kontekst: {context}
Odgovor:"""

    FEW_SHOT = """Ti si asistent koji odgovara na pitanja o ETF fakultetu. Odgovori ISKLJUČIVO na osnovu datog konteksta. Ako odgovor nije u kontekstu, reci "Nisam pronašao odgovor u dostupnim dokumentima." Koristi latinično pismo. Ne izmišljaj informacije.

Primeri:
{examples}

Pitanje: {question}
Kontekst: {context}
Odgovor:"""

    CHAIN_OF_THOUGHT = """Ti si asistent koji odgovara na pitanja o ETF fakultetu. Odgovori ISKLJUČIVO na osnovu datog konteksta. Ako odgovor nije u kontekstu, reci "Nisam pronašao odgovor u dostupnim dokumentima." Koristi latinično pismo. Ne izmišljaj informacije.

Pitanje: {question}
Kontekst: {context}

Korak 1: Identifikuj relevantne informacije iz konteksta
Korak 2: Formuliši odgovor samo na osnovu tih informacija
Odgovor:"""
    
    @staticmethod
    def format_zero_shot(question: str, context: str) -> str:
        """Format zero-shot prompt"""
        return PromptTemplate.ZERO_SHOT.format(question=question, context=context)
    
    @staticmethod
    def format_few_shot(question: str, context: str, examples: str) -> str:
        """Format few-shot prompt"""
        return PromptTemplate.FEW_SHOT.format(
            question=question,
            context=context,
            examples=examples
        )
    
    @staticmethod
    def format_chain_of_thought(question: str, context: str) -> str:
        """Format chain-of-thought prompt"""
        return PromptTemplate.CHAIN_OF_THOUGHT.format(
            question=question,
            context=context
        )
