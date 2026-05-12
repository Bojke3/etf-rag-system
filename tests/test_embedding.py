"""Tests for embedding models"""

import pytest
import numpy as np
from src.embedding import SentenceTransformerEmbedding

class TestSentenceTransformerEmbedding:
    """Test embedding models"""
    
    def test_embedding_initialization(self):
        """Test embedding model initialization"""
        model = SentenceTransformerEmbedding(device="cpu")
        assert model.embedding_dim > 0
    
    def test_embed_text(self):
        """Test embedding single text"""
        model = SentenceTransformerEmbedding(device="cpu")
        embedding = model.embed_text("This is a test")
        
        assert isinstance(embedding, np.ndarray)
        assert len(embedding) == model.embedding_dim
    
    def test_embed_texts(self):
        """Test embedding multiple texts"""
        model = SentenceTransformerEmbedding(device="cpu")
        texts = ["This is test 1", "This is test 2"]
        embeddings = model.embed_texts(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (len(texts), model.embedding_dim)
