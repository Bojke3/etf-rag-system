"""Context construction utilities for retrieved documents."""

from typing import Dict, List


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
