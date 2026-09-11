"""RAG Pipeline - Main orchestration"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import time
from src.data import TextPreprocessor

logger = logging.getLogger(__name__)

class RAGPipeline:
    """Main RAG pipeline orchestration"""
    
    def __init__(self, retriever, llm_client, embedding_model,
                 context_max_length=None, chunk_strategy=None):
        self.retriever = retriever
        self.llm_client = llm_client
        self.embedding_model = embedding_model
        # Queries are normalised (transliterated) but never OCR-repaired — the
        # cleanup passes exist to fix scanned documents, not user questions.
        self.preprocessor = TextPreprocessor(ocr_cleanup=False)
        self.context_max_length = context_max_length
        self.chunk_strategy = chunk_strategy
    
    def process_query(self,
                     question: str,
                     top_k: int = 5,
                     prompt_strategy: str = "zero_shot",
                     include_sources: bool = True,
                     examples: str = "") -> Dict[str, Any]:
        """Process user query end-to-end"""
        
        start_time = time.time()
        
        try:
            # Corpus is transliterated to Latin script at ingestion time (see
            # process_documents.py), so the query must match or retrieval
            # silently degrades for Cyrillic input.
            normalized_question = self.preprocessor.clean(question)

            # 1. Retrieve relevant documents
            retrieval_start = time.time()
            retrieved_docs = self.retriever.retrieve(normalized_question, top_k)
            retrieval_time = time.time() - retrieval_start
            
            if not retrieved_docs:
                return {
                    "status": "error",
                    "error": "No relevant documents found",
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            
            # 2. Build context
            from src.retrieval import ContextBuilder
            context = ContextBuilder.build_context(
                retrieved_docs, max_length=self.context_max_length
            )
            
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
                "chunk_strategy": self.chunk_strategy,
                "context_chars": len(context),
                "processing_time_ms": int(total_time * 1000),
                "retrieval_time_ms": int(retrieval_time * 1000),
                "generation_time_ms": int(generation_time * 1000),
            }
            
            if include_sources:
                # chunk_id / parent_chunk_id / strategy_id are additive: existing
                # consumers read document/score/text exactly as before, and
                # retrieval-level metrics now have chunk-level ids to work with.
                response["sources"] = [
                    {
                        "document": doc.get("document", "Unknown"),
                        "score": doc.get("score", 0),
                        "text": doc.get("text", "")[:200],
                        "chunk_id": doc.get("id", doc.get("chunk_id")),
                        "parent_chunk_id": doc.get("parent_chunk_id"),
                        "strategy_id": doc.get("strategy_id", self.chunk_strategy),
                        "section": doc.get("section"),
                        "page": doc.get("page"),
                        "expanded_to_parent": doc.get("expanded_to_parent", False),
                    }
                    for doc in retrieved_docs
                ]
            
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "status": "error",
                "error": str(e),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
