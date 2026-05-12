#!/bin/bash

# Script to setup Ollama models

echo "Setting up Ollama models..."

# Check if ollama is running
if ! curl -s http://localhost:11434/api/version > /dev/null; then
    echo "Error: Ollama is not running on http://localhost:11434"
    echo "Please start Ollama first:"
    echo "  - On Linux/Mac: ollama serve"
    echo "  - On Docker: docker run -p 11434:11434 ollama/ollama serve"
    exit 1
fi

echo "Ollama is running. Pulling models..."

# Pull models
echo "Pulling Mistral..."
ollama pull mistral

echo "Pulling Llama 2..."
ollama pull llama2

echo "Pulling Neural Chat..."
ollama pull neural-chat

echo "Done! Available models:"
ollama list
