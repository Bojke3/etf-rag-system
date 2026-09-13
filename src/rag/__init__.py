"""RAG Pipeline - Main orchestration"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import time
from src.data import TextPreprocessor

logger = logging.getLogger(__name__)

class RAGPipeline:
    """Main RAG pipeline orchestration"""
    
    def __init__(self, retriever, llm_client, embedding_model, context_max_chars=2000):
        if context_max_chars < 1:
            raise ValueError('Context character budget must be positive.')
        self.retriever = retriever
        self.llm_client = llm_client
        self.embedding_model = embedding_model
        self.preprocessor = TextPreprocessor()
        self.context_max_chars = context_max_chars
    
    def process_query(self,
                     question: str,
                     top_k: int = 5,
                     prompt_strategy: str = "zero_shot",
                     include_sources: bool = True,
                     examples: str = "",
                     include_diagnostics: bool = False,
                     context_documents: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Process user query end-to-end"""
        
        start_time = time.time()
        
        try:
            # Corpus is transliterated to Latin script at ingestion time (see
            # process_documents.py), so the query must match or retrieval
            # silently degrades for Cyrillic input.
            normalized_question = self.preprocessor.clean(question)

            # 1. Retrieve relevant documents
            retrieval_start = time.time()
            curated = context_documents is not None
            retrieved_docs = context_documents if curated else self.retriever.retrieve(normalized_question, top_k)
            retrieval_time = 0.0 if curated else time.time() - retrieval_start
            
            if not retrieved_docs and not curated:
                return {
                    "status": "error",
                    "error": "No relevant documents found",
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            
            # 2. Build context
            from src.retrieval import ContextBuilder
            context_details = ContextBuilder.build_context_details(retrieved_docs, self.context_max_chars)
            if curated and context_details['context_truncated']:
                raise ValueError('Curated evidence exceeds the context budget; increase --context-max-chars.')
            context = context_details['context']
            
            # 3. Build prompt
            from src.llm import PromptTemplate
            if prompt_strategy == "zero_shot":
                prompt = PromptTemplate.format_zero_shot(normalized_question, context)
            elif prompt_strategy == "few_shot":
                prompt = PromptTemplate.format_few_shot(normalized_question, context, examples)
            elif prompt_strategy == "chain_of_thought":
                prompt = PromptTemplate.format_chain_of_thought(normalized_question, context)
            else:
                prompt = PromptTemplate.format_zero_shot(normalized_question, context)
            
            logger.info("Retrieved chunks: %s", len(retrieved_docs))

            for i, doc in enumerate(retrieved_docs, start=1):
                logger.info(
                    "Chunk #%s |\n|\n| document = %s |\n|\n| chunk_id = %s |\n|\n| score = %s |\n|\n| text = %r",
                    i,
                    doc.get("document", "Unknown"),
                    doc.get("chunk_id", "Unknown"),
                    doc.get("score", 0),
                    doc.get("text", "")[:700],
                )

            logger.info("Context chars=%s", len(context))
            logger.info("Context preview=%r", context[:1500])

            logger.info("Prompt strategy=%s", prompt_strategy)
            logger.info("Prompt sent to LLM:\n%s", prompt)

            # 4. Generate answer
            generation_start = time.time()
            answer = self.llm_client.generate(prompt, system=PromptTemplate.SYSTEM)
            generation_time = time.time() - generation_start
            
            # 5. Build response
            total_time = time.time() - start_time
            
            response = {
                "status": "success",
                "question": question,
                "answer": answer,
                "retrieved_chunks": len(retrieved_docs),
                "processing_time_ms": int(total_time * 1000),
                "retrieval_time_ms": int(retrieval_time * 1000),
                "generation_time_ms": int(generation_time * 1000),
            }
            
            if include_sources:
                response["sources"] = [
                    {
                        "document": doc.get("document", "Unknown"),
                        "chunk_id": doc.get("chunk_id"),
                        "score": doc.get("score", 0),
                        "text": doc.get("text", "") if include_diagnostics else doc.get("text", "")[:200]
                    }
                    for doc in retrieved_docs
                ]
            if include_diagnostics:
                response['diagnostics'] = {
                    **context_details,
                    'context_mode': 'curated' if curated else 'retrieved',
                    'context_source_coordinates': [{key: doc.get(key) for key in
                        ('document', 'source_start', 'source_end')} for doc in retrieved_docs] if curated else [],
                    'system_prompt': PromptTemplate.SYSTEM,
                    'user_prompt': prompt,
                    'input_chars': len(PromptTemplate.SYSTEM) + len(prompt),
                    'generation': dict(getattr(self.llm_client, 'last_response_metadata', {})),
                }
            
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
