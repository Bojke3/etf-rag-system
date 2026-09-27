"""Anthropic Messages API client."""

import logging
import os
import sys
from typing import List, Optional

from .base import LLMClient

logger = logging.getLogger(__name__)


class AnthropicClient(LLMClient):
    """Small adapter exposing the same interface as the project's LLM clients."""

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        timeout: int = 300,
        max_tokens: int = 500,
        api_key: Optional[str] = None,
        disable_thinking: bool = True,
        raise_errors: bool = False,
    ):
        if max_tokens < 1:
            raise ValueError("Anthropic max_tokens must be positive.")
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.disable_thinking = disable_thinking
        self.raise_errors = raise_errors
        self.last_response_metadata = {}
        self._client = None

    def _get_client(self):
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for --judge-execution api")
        if self._client is None:
            try:
                from anthropic import Anthropic
            except ImportError as exc:
                raise RuntimeError(
                    "The 'anthropic' package is required for --judge-execution api; "
                    f"current interpreter: {sys.executable}. Install it with: "
                    f'"{sys.executable}" -m pip install "anthropic>=1.8.0"'
                ) from exc
            self._client = Anthropic(api_key=self.api_key, timeout=float(self.timeout))
        return self._client

    def validate_configuration(self):
        """Validate credentials and load the SDK without making an API request."""
        self._get_client()

    def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: str = "",
        **kwargs,
    ) -> str:
        """Generate text with Anthropic's Messages API.

        Sampling parameters are intentionally not sent. Claude Sonnet 5 rejects
        non-default temperature/top-p values, and the judge rubric supplies the
        determinism constraints in its instructions instead.
        """
        del temperature, kwargs
        self.last_response_metadata = {}
        try:
            request = {
                "model": self.model,
                "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                request["system"] = system
            if self.disable_thinking:
                request["thinking"] = {"type": "disabled"}

            response = self._get_client().messages.create(**request)
            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", None) == "text"
            )
            usage = getattr(response, "usage", None)
            self.last_response_metadata = {
                "id": getattr(response, "id", None),
                "request_id": getattr(response, "_request_id", None),
                "model": getattr(response, "model", self.model),
                "stop_reason": getattr(response, "stop_reason", None),
                "input_tokens": getattr(usage, "input_tokens", None),
                "output_tokens": getattr(usage, "output_tokens", None),
                # Keep the common judge truncation check backend-independent.
                "done_reason": (
                    "length" if getattr(response, "stop_reason", None) == "max_tokens" else "stop"
                ),
            }
            return text
        except Exception as exc:
            logger.error("Error calling Anthropic: %s", exc)
            if self.raise_errors:
                raise
            return ""

    def list_available_models(self) -> List[str]:
        """Return model IDs visible to the configured Anthropic account."""
        try:
            page = self._get_client().models.list(limit=100)
            return [model.id for model in page.data]
        except Exception as exc:
            logger.error("Error listing Anthropic models: %s", exc)
            if self.raise_errors:
                raise
            return []

    def close(self):
        """Close the SDK's underlying HTTP client, if it was created."""
        if self._client is not None:
            self._client.close()
            self._client = None
