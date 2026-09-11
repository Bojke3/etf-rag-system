"""FAISS vector store implementation."""

from typing import Dict, List
import logging

import numpy as np

from .base import VectorStore

logger = logging.getLogger(__name__)


class FAISSVectorStore(VectorStore):
    """FAISS-based vector store using cosine similarity (IndexFlatIP on L2-normalised vectors)"""

    def __init__(self, embedding_dim: int):
        try:
            import faiss
            self.index = faiss.IndexFlatIP(embedding_dim)
            self.metadatas = []
        except Exception as e:
            logger.error(f"Error initializing FAISS: {e}")
            raise

    def add(self, embeddings: np.ndarray, metadatas: List[Dict]) -> None:
        """Add embeddings to FAISS index"""
        import faiss
        vecs = embeddings.astype('float32').copy()
        faiss.normalize_L2(vecs)
        self.index.add(vecs)
        self.metadatas.extend(metadatas)

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Search FAISS index"""
        import faiss
        vec = query_embedding.astype('float32').reshape(1, -1).copy()
        faiss.normalize_L2(vec)
        scores, indices = self.index.search(vec, top_k)

        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0:
                result = self.metadatas[idx].copy()
                result['score'] = float(score)  # cosine similarity in [-1, 1]
                results.append(result)

        return results

    @staticmethod
    def artifact_names(name=None):
        """File names for an index, optionally namespaced by chunking strategy.

        With no name this is the historical ``index.faiss`` / ``metadatas.json``
        pair, so existing stores keep loading unchanged.
        """
        suffix = f"_{name}" if name else ""
        return f"index{suffix}.faiss", f"metadatas{suffix}.json"

    def save(self, path: str, name=None) -> None:
        """Save FAISS index, optionally under a strategy-specific file name"""
        import faiss
        import json
        from pathlib import Path

        index_file, metadata_file = self.artifact_names(name)

        Path(path).mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(Path(path) / index_file))

        with open(Path(path) / metadata_file, 'w') as f:
            json.dump(self.metadatas, f)

    def load(self, path: str, name=None) -> None:
        """Load FAISS index, optionally from a strategy-specific file name"""
        import faiss
        import json
        from pathlib import Path

        index_file, metadata_file = self.artifact_names(name)

        self.index = faiss.read_index(str(Path(path) / index_file))

        with open(Path(path) / metadata_file, 'r') as f:
            self.metadatas = json.load(f)

    @staticmethod
    def exists(path: str, name=None) -> bool:
        """Whether both artifacts for this index are present on disk"""
        from pathlib import Path

        index_file, metadata_file = FAISSVectorStore.artifact_names(name)
        base = Path(path)
        return (base / index_file).exists() and (base / metadata_file).exists()
