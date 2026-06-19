"""Ollama LLM client."""

from typing import List
import logging

from .base import LLMClient

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """Client for local Ollama models"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral", timeout: int = 300):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.session = None

    def generate(self, prompt: str, temperature: float = 0.1, max_tokens: int = 2048, system: str = "", **kwargs) -> str:
        """Generate response using Ollama"""
        try:
            import requests
            logger.info("Calling Ollama model=%s", self.model)
            logger.info("Prompt length=%s chars", len(prompt))
            logger.info("Max tokens=%s, timeout=%s", max_tokens, self.timeout)

            payload = {
                "model": self.model,
                "prompt": prompt,
                "temperature": temperature,
                "num_predict": max_tokens,
                "stream": False,
            }
            if system:
                payload["system"] = system

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                answer = response.json().get("response", "")
                logger.info("Ollama response length=%s chars", len(answer))
                return answer
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
