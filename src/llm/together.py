"""Together chat completions for benchmark generation (no SDK required)."""

from datetime import datetime, timezone

from .base import LLMClient


class TogetherClient(LLMClient):
    base_url = 'https://api.together.ai/v1'

    def __init__(self, api_key, model, timeout=900, temperature=0.7,
                 max_tokens=2048, top_p=0.9, think=False):
        if not api_key or not api_key.strip():
            raise ValueError('Set TOGETHER_API_KEY in .env before using --execution together.')
        if think is not None and not isinstance(think, bool):
            raise ValueError('TOGETHER_THINK must be true or false.')
        self._api_key = api_key.strip()
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.think = think
        self.last_response_metadata = {}

    def generation_options(self):
        return {'temperature': self.temperature, 'max_tokens': self.max_tokens,
                'top_p': self.top_p, 'stream': False,
                **({'reasoning': {'enabled': self.think}} if self.think is not None else {})}

    def generate(self, prompt, temperature=None, max_tokens=None, system='', **kwargs):
        import requests

        self.last_response_metadata = {
            'provider': 'together', 'requested_model': self.model,
            'requested_at_utc': datetime.now(timezone.utc).isoformat(),
        }
        messages = ([{'role': 'system', 'content': system}] if system else [])
        messages.append({'role': 'user', 'content': prompt})
        options = self.generation_options()
        if temperature is not None:
            options['temperature'] = temperature
        if max_tokens is not None:
            options['max_tokens'] = max_tokens
        self.last_response_metadata['request_options'] = options
        try:
            response = requests.post(
                self.base_url + '/chat/completions',
                headers={'Authorization': 'Bearer ' + self._api_key},
                json={'model': self.model, 'messages': messages, **options},
                timeout=self.timeout,
            )
            self.last_response_metadata.update(
                http_status=response.status_code,
                request_id=response.headers.get('x-request-id'),
                received_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            # Redact the credential even if a provider error happens to echo it.
            safe_body = response.text.replace(self._api_key, '[REDACTED]')
            if response.status_code != 200:
                self.last_response_metadata['error_body'] = safe_body[:2000]
                raise RuntimeError(f'Together HTTP {response.status_code}: {safe_body[:500]}')
            import json
            result = json.loads(safe_body)
            self.last_response_metadata['raw_response'] = result
            choices = result.get('choices') or []
            if not choices:
                raise RuntimeError('Together returned no choices.')
            choice = choices[0]
            usage = result.get('usage') or {}
            self.last_response_metadata.update(
                response_id=result.get('id'), model=result.get('model'),
                system_fingerprint=result.get('system_fingerprint'), usage=usage,
                finish_reason=choice.get('finish_reason'),
                prompt_eval_count=usage.get('prompt_tokens'),
                eval_count=usage.get('completion_tokens'),
                done_reason=choice.get('finish_reason'),
            )
            if result.get('model') and result['model'] != self.model:
                raise RuntimeError('Together returned a different model; inspect diagnostics.generation.raw_response.')
            content = (choice.get('message') or {}).get('content')
            if not isinstance(content, str) or not content.strip():
                raise RuntimeError('Together returned no final answer text; inspect finish_reason and reasoning.')
            return content
        except Exception as exc:
            message = str(exc).replace(self._api_key, '[REDACTED]')
            self.last_response_metadata['error'] = message
            raise RuntimeError(message) from None

    def list_available_models(self):
        import requests

        response = requests.get(self.base_url + '/models',
                                headers={'Authorization': 'Bearer ' + self._api_key},
                                timeout=self.timeout)
        if response.status_code != 200:
            raise RuntimeError(f'Together model listing failed: HTTP {response.status_code}')
        models = response.json()
        if isinstance(models, dict):
            models = models.get('data', [])
        return [model['id'] for model in models]
