"""Read-only, offline check of the saved index against cached embedding models."""

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[4]
RUN = ROOT / "benchmarking/runs/baselineNo1"
metadata = json.loads((ROOT / "models/vectorstore/metadatas.json").read_text(encoding="utf-8"))
index = faiss.read_index(str(ROOT / "models/vectorstore/index.faiss"))
sample_ids = np.linspace(0, len(metadata) - 1, 12, dtype=int).tolist()
stored = np.stack([index.reconstruct(i) for i in sample_ids])
results = []
for name in ["all-MiniLM-L6-v2", "paraphrase-multilingual-MiniLM-L12-v2"]:
    print(f"Checking cached model: {name}", flush=True)
    try:
        model = SentenceTransformer("sentence-transformers/" + name, device="cpu", local_files_only=True)
        encoded = model.encode([metadata[i]["text"] for i in sample_ids], normalize_embeddings=True,
                               convert_to_numpy=True, show_progress_bar=False)
        similarities = (stored * encoded).sum(axis=1)
        record = {"model": name, "sample_ids": sample_ids,
                  "same_text_cosine_similarities": similarities.tolist(),
                  "minimum": float(similarities.min()), "mean": float(similarities.mean())}
        results.append(record)
        print(json.dumps(record), flush=True)
    except Exception as exc:
        results.append({"model": name, "error": str(exc)})
        print(f"Check unavailable: {exc}", flush=True)
(RUN / "diagnostics/index_consistency.json").write_text(
    json.dumps({"method": "Compare 12 evenly spaced stored vectors with fresh embeddings of identical metadata text; cached models only; existing index is not modified.",
                "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
