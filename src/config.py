"""Configuration management for ETF RAG System"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional

class Config(BaseSettings):
    """Main configuration class"""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # LLM Configuration
    llm_type: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral"
    ollama_temperature: float = 0.7
    ollama_top_p: float = 0.9
    ollama_max_tokens: int = 2048
    
    # Embedding Configuration
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    
    # Vector Store Configuration
    vector_store_type: str = "faiss"
    vector_store_path: str = "./models/vectorstore"
    
    # Data Paths
    data_dir: str = "./data/documents"
    processed_data_dir: str = "./data/processed"
    embedding_dir: str = "./data/embeddings"
    
    # Chunking Strategy
    chunk_size: int = 512
    chunk_overlap: int = 100
    
    # Retrieval Configuration
    retrieval_top_k: int = 5
    retrieval_threshold: float = 0.7
    
    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"
    
    # Web Configuration
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    web_debug: bool = False
    
    # Optional: Cloud LLM APIs
    openai_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    
    # Chatbot Integrations
    telegram_bot_token: Optional[str] = None
    discord_bot_token: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

# Create config instance
config = Config()
