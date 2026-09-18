"""Bind each index directory to the one encoder that built it.

A FAISS index is only meaningful to the embedding model that produced its
vectors. A dimension mismatch already raises at load time, but two different
encoders of the *same* dimension load each other's index without any error and
return quietly wrong neighbours -- ``all-MiniLM-L6-v2`` and
``paraphrase-multilingual-MiniLM-L12-v2`` are both 384-dimensional, and both
have been configured in this project. That failure is invisible in the results,
so the pairing is declared in ``models/registry.json`` and verified here.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY = Path(__file__).resolve().parents[2] / "models" / "registry.json"


def load_registry(path=None):
    """Read the index registry; an absent file means no declared pairings."""
    registry_path = Path(path) if path else DEFAULT_REGISTRY
    if not registry_path.is_file():
        logger.warning("No index registry at %s; index/encoder pairing is unchecked.", registry_path)
        return {}

    with registry_path.open("r", encoding="utf-8") as f:
        return json.load(f).get("configs", {})


def resolve(config_id, path=None):
    """Return the registry entry for a config ID, such as ``c001``."""
    configs = load_registry(path)
    if config_id not in configs:
        raise KeyError(f"Unknown index configuration {config_id!r}. Known: {sorted(configs)}")
    return configs[config_id]


def find_by_index_dir(index_dir, path=None):
    """Return ``(config_id, entry)`` for an index directory, or ``(None, None)``.

    Directories are compared resolved, so a relative path, an absolute one and a
    symlink to the same index all match the same entry.
    """
    target = Path(index_dir).resolve()
    for config_id, entry in load_registry(path).items():
        declared = Path(entry["index_dir"])
        if not declared.is_absolute():
            declared = DEFAULT_REGISTRY.parents[1] / declared
        if declared.resolve() == target:
            return config_id, entry
    return None, None


def verify_pairing(index_dir, embedding_model, embedding_dim=None, path=None):
    """Raise when an index is about to be loaded with the wrong encoder.

    An index directory absent from the registry is allowed through, so ad-hoc
    and experimental indexes keep working; only declared pairings are enforced.
    Returns the config ID when one matched, otherwise ``None``.
    """
    config_id, entry = find_by_index_dir(index_dir, path)
    if entry is None:
        logger.warning(
            "Index directory %s is not in the registry; its encoder pairing cannot be verified.",
            index_dir,
        )
        return None

    expected_model = entry["embedding_model"]
    if embedding_model != expected_model:
        raise ValueError(
            f"Index {index_dir} ({config_id}) was built with {expected_model!r}, "
            f"but {embedding_model!r} was requested. These encoders do not share a "
            f"vector space; retrieval would be wrong without failing. Set "
            f"EMBEDDING_MODEL={expected_model} or point VECTOR_STORE_PATH at the "
            f"index built for the encoder you want."
        )

    expected_dim = entry.get("embedding_dimension")
    if embedding_dim is not None and expected_dim is not None and embedding_dim != expected_dim:
        raise ValueError(
            f"Index {index_dir} ({config_id}) declares dimension {expected_dim}, "
            f"but the loaded encoder reports {embedding_dim}. The registry entry or "
            f"the installed model is wrong."
        )

    return config_id


def audit(path=None):
    """Check every registered index against its declared files, on disk.

    Verifies presence, dimension, vector count and file hashes without loading
    any encoder, so it is cheap and needs no model downloads. Returns a list of
    problem strings; empty means the registry matches what is on disk.
    """
    import faiss
    import hashlib

    problems = []
    root = DEFAULT_REGISTRY.parents[1]
    for config_id, entry in load_registry(path).items():
        index_dir = root / entry["index_dir"]
        if not index_dir.is_dir():
            problems.append(f"{config_id}: missing directory {entry['index_dir']}")
            continue

        for name, expected_hash in entry.get("files", {}).items():
            file_path = index_dir / name
            if not file_path.is_file():
                problems.append(f"{config_id}: missing {name}")
                continue
            actual = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual != expected_hash:
                problems.append(f"{config_id}: {name} hash {actual[:12]} != declared {expected_hash[:12]}")

        index_file = index_dir / "index.faiss"
        if index_file.is_file():
            index = faiss.read_index(str(index_file))
            if index.d != entry.get("embedding_dimension"):
                problems.append(f"{config_id}: index dimension {index.d} != declared {entry.get('embedding_dimension')}")
            if index.ntotal != entry.get("vector_count"):
                problems.append(f"{config_id}: {index.ntotal} vectors != declared {entry.get('vector_count')}")

    return problems


if __name__ == "__main__":
    import sys

    found = audit()
    for problem in found:
        print(problem)
    print(f"{len(load_registry())} configurations checked, {len(found)} problems.")
    sys.exit(1 if found else 0)
