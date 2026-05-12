"""Chatbot and Agent implementations"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Agent(ABC):
    """Abstract base class for agents"""
    
    @abstractmethod
    def handle_message(self, user_id: str, message: str) -> str:
        """Handle user message and return response"""
        pass

class RAGAgent(Agent):
    """RAG-based agent for answering questions"""
    
    def __init__(self, rag_pipeline):
        self.rag_pipeline = rag_pipeline
        self.conversation_history: Dict[str, List[Dict]] = {}
    
    def handle_message(self, user_id: str, message: str) -> str:
        """Process message and generate response"""
        try:
            # Initialize conversation history if needed
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Add user message to history
            self.conversation_history[user_id].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            
            # Process query through RAG pipeline
            result = self.rag_pipeline.process_query(
                question=message,
                top_k=5,
                prompt_strategy="few_shot",
                include_sources=True
            )
            
            if result["status"] == "success":
                answer = result["answer"]
                # Add assistant response to history
                self.conversation_history[user_id].append({
                    "role": "assistant",
                    "content": answer,
                    "timestamp": datetime.now().isoformat(),
                    "sources": result.get("sources", [])
                })
                return answer
            else:
                error_msg = f"Sorry, I couldn't find an answer: {result.get('error', 'Unknown error')}"
                self.conversation_history[user_id].append({
                    "role": "assistant",
                    "content": error_msg,
                    "timestamp": datetime.now().isoformat()
                })
                return error_msg
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return f"Sorry, an error occurred: {str(e)}"
    
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Get conversation history for user"""
        return self.conversation_history.get(user_id, [])
    
    def clear_conversation_history(self, user_id: str) -> None:
        """Clear conversation history for user"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
