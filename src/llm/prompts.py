"""Prompt templates for RAG answer generation."""


class PromptTemplate:
    """Prompt template builder"""

    SYSTEM = """You are a helpful assistant for ETF faculty students. 
    Answer only using the provided context. Always respond in Serbian using Latin script (not Cyrillic). 
    If the answer is not in the context, say: 'Nisam pronasao odgovor u dostupnim dokumentima.'"""

    ZERO_SHOT = """Context:
{context}

Question: {question}
Answer in Serbian (Latin script only):"""

    FEW_SHOT = """Context:
{context}

Examples:
{examples}

Question: {question}
Answer in Serbian (Latin script only):"""

    CHAIN_OF_THOUGHT = """Context:
{context}

Question: {question}
Answer in Serbian (Latin script only):"""

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
