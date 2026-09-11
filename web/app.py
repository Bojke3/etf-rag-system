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
        from src.data.chunking import LEVEL_PARENT, resolve_strategy_id
        from src.embedding import SentenceTransformerEmbedding, FAISSVectorStore
        from src.retrieval import ParentAwareRetriever, SimpleRetriever, load_parent_store
        from src.llm import OllamaClient
        from src.rag import RAGPipeline

        strategy_id = resolve_strategy_id(config.chunk_strategy)

        embedding_model = SentenceTransformerEmbedding(
            model_name=config.embedding_model,
            device=config.embedding_device,
        )
        vector_store = FAISSVectorStore(embedding_dim=embedding_model.embedding_dim)

        # Load the index built for this chunking strategy. Falls back to the
        # unnamed legacy index (index.faiss) when no per-strategy one exists.
        if FAISSVectorStore.exists(config.vector_store_path, strategy_id):
            vector_store.load(config.vector_store_path, name=strategy_id)
        elif FAISSVectorStore.exists(config.vector_store_path):
            app.logger.warning(
                "No index for strategy %s — falling back to the legacy index. "
                "Run scripts/index_documents.py --strategy %s to build it.",
                strategy_id, strategy_id,
            )
            vector_store.load(config.vector_store_path)

        retriever = SimpleRetriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            threshold=config.retrieval_threshold,
        )

        # Hierarchical strategies embed child chunks but feed the LLM their
        # parents, looked up by id.
        if config.hier_expand_to_parent:
            parent_store = load_parent_store(config.vector_store_path, strategy_id)
            if parent_store:
                retriever = ParentAwareRetriever(retriever, parent_store)

        llm_client = OllamaClient(
            base_url=config.ollama_base_url,
            model=_selected_ollama_model,
            timeout=config.ollama_timeout
        )
        _pipeline = RAGPipeline(
            retriever=retriever,
            llm_client=llm_client,
            embedding_model=embedding_model,
            context_max_length=config.context_max_length,
            chunk_strategy=strategy_id,
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
        "chunk_strategy": config.chunk_strategy,
        "context_max_length": config.context_max_length,
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


