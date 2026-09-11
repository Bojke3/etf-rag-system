"""Strategy lookup -- the single place a chunking strategy is resolved by name.

Adding a third strategy (e.g. graph-based) means one entry in ``STRATEGIES``
and nothing else: the scripts, the config flag and the index naming all read
through here.
"""

from typing import Any, Dict, List, Optional

from .base import ChunkingStrategy
from .flat import FlatChunker
from .hierarchical import HierarchicalChunker

STRATEGIES: Dict[str, type] = {
    FlatChunker.strategy_id: FlatChunker,
    HierarchicalChunker.strategy_id: HierarchicalChunker,
}

#: Accepted spellings that map onto a canonical strategy id.
STRATEGY_ALIASES: Dict[str, str] = {
    "flat_512": FlatChunker.strategy_id,
    "flat": FlatChunker.strategy_id,
    "simple": FlatChunker.strategy_id,
    "baseline": FlatChunker.strategy_id,
    "parent_child": HierarchicalChunker.strategy_id,
}

DEFAULT_STRATEGY = FlatChunker.strategy_id


def available_strategies() -> List[str]:
    return sorted(STRATEGIES)


def resolve_strategy_id(strategy_id: Optional[str]) -> str:
    """Normalise a user-supplied strategy name to a canonical id."""
    if not strategy_id:
        return DEFAULT_STRATEGY

    key = str(strategy_id).strip().lower()
    key = STRATEGY_ALIASES.get(key, key)

    if key not in STRATEGIES:
        raise ValueError(
            f"Unknown chunking strategy {strategy_id!r}. "
            f"Available: {', '.join(available_strategies())} "
            f"(aliases: {', '.join(sorted(STRATEGY_ALIASES))})"
        )
    return key


def get_chunker(strategy_id: Optional[str] = None, config: Any = None, **overrides) -> ChunkingStrategy:
    """Build the chunker for ``strategy_id``, taking sizes from ``config``."""
    resolved = resolve_strategy_id(strategy_id)

    def setting(name, default):
        if name in overrides and overrides[name] is not None:
            return overrides[name]
        return getattr(config, name, default) if config is not None else default

    if resolved == FlatChunker.strategy_id:
        return FlatChunker(
            chunk_size=setting("chunk_size", 1024),
            overlap=setting("chunk_overlap", 150),
        )

    return HierarchicalChunker(
        parent_size=setting("hier_parent_size", 4500),
        parent_min=setting("hier_parent_min", 3600),
        child_size=setting("hier_child_size", 1200),
        child_min=setting("hier_child_min", 900),
        child_overlap_ratio=setting("hier_child_overlap_ratio", 0.12),
    )
