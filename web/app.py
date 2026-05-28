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
_selected_ollama_model = config.ollama_model


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
            model=_selected_ollama_model,
            timeout=config.ollama_timeout
        )
        _pipeline = RAGPipeline(
            retriever=retriever,
            llm_client=llm_client,
            embedding_model=embedding_model,
        )
    return _pipeline



def get_current_model():
    """Return the model currently selected for Ollama generation."""
    return _selected_ollama_model

@app.route("/chat", methods=["GET"])
def chat():
    return render_template("chat.html", model=get_current_model())


@app.route("/", methods=["GET"])
def health():
    """Health check / system info."""
    return jsonify({
        "status": "ok",
        "system": "ETF RAG System",
        "llm_type": config.llm_type,
        "ollama_model": get_current_model(),
        "embedding_model": config.embedding_model,
    })



@app.route("/models", methods=["GET"])
def models():
    """Return locally available Ollama models."""
    try:
        from src.llm import OllamaClient

        client = OllamaClient(
            base_url=config.ollama_base_url,
            model=get_current_model(),
            timeout=config.ollama_timeout,
        )
        available_models = client.list_available_models()
        return jsonify({
            "status": "success",
            "current_model": get_current_model(),
            "models": available_models,
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/models/current", methods=["POST"])
def set_current_model():
    """Switch the Ollama model used by the current web session."""
    global _selected_ollama_model

    body = request.get_json(force=True, silent=True) or {}
    model = body.get("model", "").strip()
    if not model:
        return jsonify({"status": "error", "error": "Missing 'model' field"}), 400

    try:
        from src.llm import OllamaClient

        client = OllamaClient(
            base_url=config.ollama_base_url,
            model=get_current_model(),
            timeout=config.ollama_timeout,
        )
        available_models = client.list_available_models()
        if available_models and model not in available_models:
            return jsonify({
                "status": "error",
                "error": f"Model '{model}' is not available in Ollama.",
                "models": available_models,
            }), 400

        _selected_ollama_model = model
        if _pipeline is not None:
            _pipeline.llm_client.model = model

        return jsonify({
            "status": "success",
            "current_model": get_current_model(),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

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


