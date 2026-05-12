"""Embedding layer - Vector representations and storage"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EmbeddingModel(ABC):
    """Abstract base class for embedding models"""
    
    @abstractmethod
    def embed_text(self, text: str) -> np.ndarray:
        """Embed single text"""
        pass
    
    @abstractmethod
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts"""
        pass
    
    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Return embedding dimension"""
        pass

class SentenceTransformerEmbedding(EmbeddingModel):
    """Embedding using Sentence Transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name, device=device)
            self.model_name = model_name
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            raise
    
    def embed_text(self, text: str) -> np.ndarray:
        """Embed single text"""
        return self.model.encode(text, convert_to_numpy=True)
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed multiple texts"""
        return self.model.encode(texts, convert_to_numpy=True)
    
    @property
    def embedding_dim(self) -> int:
        """Return embedding dimension"""
        return self.model.get_sentence_embedding_dimension()

class VectorStore(ABC):
    """Abstract base class for vector stores"""
    
    @abstractmethod
    def add(self, embeddings: np.ndarray, metadatas: List[Dict]) -> None:
        """Add embeddings to store"""
        pass
    
    @abstractmethod
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Search similar embeddings"""
        pass
    
    @abstractmethod
    def save(self, path: str) -> None:
        """Save vector store"""
        pass
    
    @abstractmethod
    def load(self, path: str) -> None:
        """Load vector store"""
        pass

class FAISSVectorStore(VectorStore):
    """FAISS-based vector store"""
    
    def __init__(self, embedding_dim: int):
        try:
            import faiss
            self.index = faiss.IndexFlatL2(embedding_dim)
            self.metadatas = []
        except Exception as e:
            logger.error(f"Error initializing FAISS: {e}")
            raise
    
    def add(self, embeddings: np.ndarray, metadatas: List[Dict]) -> None:
        """Add embeddings to FAISS index"""
        import faiss
        self.index.add(embeddings.astype('float32'))
        self.metadatas.extend(metadatas)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Search FAISS index"""
        distances, indices = self.index.search(
            query_embedding.astype('float32').reshape(1, -1), 
            top_k
        )
        
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx >= 0:
                result = self.metadatas[idx].copy()
                result['distance'] = float(distance)
                result['score'] = 1.0 / (1.0 + float(distance))
                results.append(result)
        
        return results
    
    def save(self, path: str) -> None:
        """Save FAISS index"""
        import faiss
        import json
        from pathlib import Path
        
        Path(path).mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(Path(path) / "index.faiss"))
        
        with open(Path(path) / "metadatas.json", 'w') as f:
            json.dump(self.metadatas, f)
    
    def load(self, path: str) -> None:
        """Load FAISS index"""
        import faiss
        import json
        from pathlib import Path
        
        self.index = faiss.read_index(str(Path(path) / "index.faiss"))
        
        with open(Path(path) / "metadatas.json", 'r') as f:
            self.metadatas = json.load(f)
