"""Context construction utilities for retrieved documents."""

from typing import Dict, List


class ContextBuilder:
    """Build context from retrieved documents"""

    @staticmethod
    def build_context(retrieved_docs: List[Dict], max_length: int = 2000) -> str:
        """Build context with a character budget including separators."""
        return ContextBuilder.build_context_details(retrieved_docs, max_length)['context']

    @staticmethod
    def build_context_details(retrieved_docs: List[Dict], max_length: int = 2000) -> Dict:
        """Return exact context and per-chunk usage for reproducible evaluation."""
        if max_length < 1:
            raise ValueError('Context character budget must be positive.')
        context_parts = []
        total_length = 0
        usage = []
        stopped = False
        for rank, doc in enumerate(retrieved_docs, start=1):
            text = doc.get('text', '')
            used = 0
            separator_length = 2 if context_parts else 0
            if text and not stopped:
                remaining = max_length - total_length - separator_length
                if len(text) <= remaining:
                    used = len(text)
                else:
                    # Retain the existing policy of omitting tiny trailing fragments.
                    used = max(0, remaining) if remaining > 100 else 0
                    stopped = True
                if used:
                    context_parts.append(text[:used])
                    total_length += separator_length + used
            usage.append({'rank': rank, 'document': doc.get('document', 'Unknown'),
                          'chunk_id': doc.get('chunk_id'), 'text_chars': len(text),
                          'context_chars_used': used})
        context = '\n\n'.join(context_parts)
        full_context = '\n\n'.join(doc['text'] for doc in retrieved_docs if doc.get('text'))
        return {'context': context, 'context_max_chars': max_length,
                'context_chars': len(context), 'full_context_chars': len(full_context),
                'context_truncated': context != full_context,
                'chunks_fully_included': sum(u['text_chars'] > 0 and u['context_chars_used'] == u['text_chars'] for u in usage),
                'chunks_partially_included': sum(0 < u['context_chars_used'] < u['text_chars'] for u in usage),
                'chunks_omitted': sum(u['text_chars'] > 0 and u['context_chars_used'] == 0 for u in usage),
                'chunk_usage': usage}
