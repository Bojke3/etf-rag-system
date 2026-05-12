"""Constants for ETF RAG System"""

# Supported document formats
SUPPORTED_FORMATS = ['.pdf', '.docx', '.doc', '.txt']

# Supported embedding models
EMBEDDING_MODELS = {
    'all-MiniLM-L6-v2': 'sentence-transformers/all-MiniLM-L6-v2',
    'all-mpnet-base-v2': 'sentence-transformers/all-mpnet-base-v2',
    'multilingual-e5-base': 'intfloat/multilingual-e5-base',
}

# Supported Ollama models
OLLAMA_MODELS = {
    'llama2': 'llama2',
    'mistral': 'mistral',
    'neural-chat': 'neural-chat',
    'deepseek': 'deepseek-coder',
    'qwen': 'qwen',
}

# Prompt strategies
PROMPT_STRATEGIES = ['zero_shot', 'few_shot', 'chain_of_thought']

# Evaluation metrics
AVAILABLE_METRICS = ['bleu', 'rouge', 'bertscore', 'llm_judge']

# Difficulty levels
DIFFICULTY_LEVELS = ['easy', 'medium', 'hard']

# Document categories
DOCUMENT_CATEGORIES = ['studies', 'master', 'phd', 'other']

# Default timeouts (seconds)
DEFAULT_TIMEOUTS = {
    'retrieval': 30,
    'embedding': 60,
    'llm': 120,
    'overall': 180,
}
