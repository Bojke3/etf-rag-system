"""Ollama LLM client."""

from typing import List, Optional, Union
import logging

from .base import LLMClient

logger = logging.getLogger(__name__)


class OllamaClient(LLMClient):
    """Client for local Ollama models"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "mistral", timeout: int = 300,
                 temperature: float = 0.1, max_tokens: int = 2048,
                 top_p: Optional[float] = None, think: Optional[Union[bool, str]] = None,
                 raise_errors: bool = False, num_ctx: Optional[int] = None):
        if num_ctx is not None and num_ctx < 1:
            raise ValueError('Ollama context window must be positive.')
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.session = None
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.think = think
        self.raise_errors = raise_errors
        self.num_ctx = num_ctx
        self.last_response_metadata = {}

    def generate(self, prompt: str, temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None, system: str = "", **kwargs) -> str:
        """Generate response using Ollama"""
        self.last_response_metadata = {}
        try:
            import requests
            temperature = self.temperature if temperature is None else temperature
            max_tokens = self.max_tokens if max_tokens is None else max_tokens
            logger.info("Calling Ollama model=%s", self.model)
            logger.info("Prompt length=%s chars", len(prompt))
            logger.info("Max tokens=%s, timeout=%s", max_tokens, self.timeout)

            payload = {
                "model": self.model,
                "prompt": prompt,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            }
            if self.top_p is not None:
                payload["options"]["top_p"] = self.top_p
            if self.num_ctx is not None:
                payload["options"]["num_ctx"] = self.num_ctx
            if self.think is not None:
                payload["think"] = self.think
            if system:
                payload["system"] = system

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                self.last_response_metadata = {key: result.get(key) for key in (
                    'prompt_eval_count', 'eval_count', 'done', 'done_reason',
                    'total_duration', 'load_duration', 'prompt_eval_duration', 'eval_duration')}
                answer = result.get("response", "")
                logger.info("Ollama response length=%s chars", len(answer))
                return answer
            else:
                raise RuntimeError(f'Ollama HTTP {response.status_code}: {response.text[:500]}')
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            if self.raise_errors:
                raise
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
