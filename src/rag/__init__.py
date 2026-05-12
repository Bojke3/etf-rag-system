"""RAG Pipeline - Main orchestration"""

from typing import List, Dict, Any, Optional, Tuple
import logging
import time

logger = logging.getLogger(__name__)

class RAGPipeline:
    """Main RAG pipeline orchestration"""
    
    def __init__(self, retriever, llm_client, embedding_model):
        self.retriever = retriever
        self.llm_client = llm_client
        self.embedding_model = embedding_model
    
    def process_query(self,
                     question: str,
                     top_k: int = 5,
                     prompt_strategy: str = "zero_shot",
                     include_sources: bool = True,
                     examples: str = "") -> Dict[str, Any]:
        """Process user query end-to-end"""
        
        start_time = time.time()
        
        try:
            # 1. Retrieve relevant documents
            retrieval_start = time.time()
            retrieved_docs = self.retriever.retrieve(question, top_k)
            retrieval_time = time.time() - retrieval_start
            
            if not retrieved_docs:
                return {
                    "status": "error",
                    "error": "No relevant documents found",
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            
            # 2. Build context
            from src.retrieval import ContextBuilder
            context = ContextBuilder.build_context(retrieved_docs)
            
            # 3. Build prompt
            from src.llm import PromptTemplate
            if prompt_strategy == "zero_shot":
                prompt = PromptTemplate.format_zero_shot(question, context)
            elif prompt_strategy == "few_shot":
                prompt = PromptTemplate.format_few_shot(question, context, examples)
            elif prompt_strategy == "chain_of_thought":
                prompt = PromptTemplate.format_chain_of_thought(question, context)
            else:
                prompt = PromptTemplate.format_zero_shot(question, context)
            
            # 4. Generate answer
            generation_start = time.time()
            answer = self.llm_client.generate(prompt)
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
                        "score": doc.get("score", 0),
                        "text": doc.get("text", "")[:200]
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
