"""Context construction utilities for retrieved documents."""

from typing import Dict, List, Optional


class ContextBuilder:
    """Build context from retrieved documents"""

    #: Fallback budget when no caller and no config supplies one.
    DEFAULT_MAX_LENGTH = 6000

    @staticmethod
    def build_context(retrieved_docs: List[Dict], max_length: Optional[int] = None) -> str:
        """Build context string from retrieved documents.

        ``max_length`` is a character budget over the whole context. It used to
        be hardcoded at 2000, which with 1024-char chunks meant only the first
        two retrieved chunks ever reached the LLM regardless of top_k. Keep this
        value identical across chunking strategies when comparing them, or the
        comparison measures context budget rather than chunking.
        """
        if max_length is None:
            max_length = ContextBuilder.DEFAULT_MAX_LENGTH
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
