"""Flask web interface for the ETF RAG System"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from src.config import config
from src.utils import setup_logging

setup_logging(config.log_dir, config.log_level)

app = Flask(__name__)
CORS(app)

# Lazy-initialized pipeline — avoids crashing on startup if Ollama is not running
_pipeline = None


def get_pipeline():
    """Initialize and return the RAG pipeline (once)."""
    global _pipeline
    if _pipeline is None:
        from src.embedding import SentenceTransformerEmbedding, FAISSVectorStore
        from src.retrieval import SimpleRetriever
        from src.llm import OllamaClient
        from src.rag import RAGPipeline

        embedding_model = SentenceTransformerEmbedding(
            model_name=config.embedding_model,
            device=config.embedding_device,
        )
        vector_store = FAISSVectorStore(embedding_dim=embedding_model.embedding_dim)

        # Load persisted index if it exists
        import os
        if os.path.exists(config.vector_store_path):
            vector_store.load(config.vector_store_path)

        retriever = SimpleRetriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            threshold=config.retrieval_threshold,
        )
        llm_client = OllamaClient(
            base_url=config.ollama_base_url,
            model=config.ollama_model,
            timeout=config.ollama_timeout
        )
        _pipeline = RAGPipeline(
            retriever=retriever,
            llm_client=llm_client,
            embedding_model=embedding_model,
        )
    return _pipeline


@app.route("/chat", methods=["GET"])
def chat():
    return render_template("chat.html", model=config.ollama_model)


@app.route("/", methods=["GET"])
def health():
    """Health check / system info."""
    return jsonify({
        "status": "ok",
        "system": "ETF RAG System",
        "llm_type": config.llm_type,
        "ollama_model": config.ollama_model,
        "embedding_model": config.embedding_model,
    })


@app.route("/query", methods=["POST"])
def query():
    """Answer a question using the RAG pipeline.

    Expected JSON body:
        {
            "question": "...",
            "top_k": 5,                   (optional, default 5)
            "prompt_strategy": "zero_shot" (optional: zero_shot | few_shot | chain_of_thought)
        }
    """
    body = request.get_json(force=True, silent=True) or {}
    question = body.get("question", "").strip()
    if not question:
        return jsonify({"status": "error", "error": "Missing 'question' field"}), 400

    top_k = int(body.get("top_k", config.retrieval_top_k))
    prompt_strategy = body.get("prompt_strategy", "zero_shot")
    examples = body.get("examples", "")

    try:
        pipeline = get_pipeline()
        result = pipeline.process_query(
            question=question,
            top_k=top_k,
            prompt_strategy=prompt_strategy,
            include_sources=True,
            examples=examples,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(
        host=config.web_host,
        port=config.web_port,
        debug=config.web_debug,
    )
