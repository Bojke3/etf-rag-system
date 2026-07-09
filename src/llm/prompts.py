"""Prompt templates for RAG answer generation."""


class PromptTemplate:
    """Prompt template builder"""

    SYSTEM = """Ti si asistent za studente Elektrotehnickog fakulteta.
Odgovaraj iskljucivo na osnovu datog konteksta.
Odgovaraj na srpskom jeziku, latinicom.
Ako odgovor ne postoji u kontekstu, reci: "Nisam pronasao odgovor u dostupnim dokumentima."
Ne izmisljaj informacije i ne koristi znanje van konteksta."""

    ZERO_SHOT = """Kontekst:
{context}

Pitanje: {question}
Odgovor:"""

    FEW_SHOT = """Kontekst:
{context}

Primeri:
{examples}

Pitanje: {question}
Odgovor:"""

    CHAIN_OF_THOUGHT = """Prvo pazljivo pronadji relevantne delove konteksta, ali u odgovoru prikazi samo konacan odgovor.

Kontekst:
{context}

Pitanje:
{question}

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
