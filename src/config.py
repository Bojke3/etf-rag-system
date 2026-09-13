"""Configuration management for ETF RAG System"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path
from typing import Optional, Union, Literal

class Config(BaseSettings):
    """Main configuration class"""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # LLM Configuration
    llm_type: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "mistral:7b"
    ollama_temperature: float = 0.7
    ollama_top_p: float = 0.9
    ollama_max_tokens: int = 512
    ollama_timeout: int = 900
    # Token window; None leaves the Ollama server/model default in effect.
    ollama_num_ctx: Optional[int] = Field(default=None, gt=0)
    ollama_think: Optional[Union[bool, Literal["low", "medium", "high"]]] = None

    # Answer collection: retrieval stays local; SSH forwards only Ollama traffic.
    benchmark_execution: str = "ask"
    ssh_host: str = ""
    ssh_user: str = ""
    ssh_port: int = 22
    ssh_identity_file: str = ""
    ssh_local_port: int = 11435
    ssh_ollama_host: str = "127.0.0.1"
    ssh_ollama_port: int = 11434
    ssh_ollama_model: str = "mistral:latest"
    ssh_startup_timeout: int = 120
    
    # Embedding Configuration
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_device: str = "cpu"
    
    # Vector Store Configuration
    vector_store_type: str = "faiss"
    vector_store_path: str = "./models/vectorstore"
    
    # Data Paths
    data_dir: str = "./data/documents"
    processed_data_dir: str = "./data/processed"
    embedding_dir: str = "./data/embeddings"
    
    # Chunking Strategy
    # chunk_strategy selects the chunker, its index and its retrieval path.
    # "flat_512" is accepted as an alias for "flat_baseline".
    chunk_strategy: str = "flat_baseline"
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # OCR text repair (hyphenation, wrapped lines, page furniture, headers).
    # Set to false to reproduce pre-cleanup chunk output exactly.
    ocr_cleanup: bool = True

    # Hierarchical chunking. Sizes are CHARACTERS, not tokens (~3.5 chars/token
    # for Serbian): parent ~1024-1536 tokens, child ~256-384 tokens.
    hier_parent_size: int = 4500
    hier_parent_min: int = 3600
    hier_child_size: int = 1200
    hier_child_min: int = 900
    hier_child_overlap_ratio: float = 0.12
    # Expand a retrieved child chunk to its parent before building context.
    hier_expand_to_parent: bool = True

    # Retrieval Configuration
    retrieval_top_k: int = 3
    retrieval_threshold: float = 0.0
    # Character budget for the retrieved text handed to the LLM (separators
    # included; prompts and question excluded). Hold this FIXED across
    # strategies when A/B testing, or the comparison measures context budget
    # rather than chunking. See CONTEXT_MAX_CHARS in .env.example.
    context_max_chars: int = Field(default=2000, gt=0)
    
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
