"""Generic pooled-assignment logic shared by device/ip/bank_account/address generation.

Phase 1D requirement: synthetic attributes must NOT be perfectly unique —
realistic populations have collisions (shared household devices, shared
office IPs) even before any deliberate legitimate-cluster or ring
narrative is injected. This module produces that *ambient* collision
rate: entities are assigned to a pool sized smaller than the entity
count, so some sharing happens purely from pool pressure, at a rate the
caller controls via `pool_ratio`.

Deterministic: distinct entity IDs are sorted before assignment so the
result never depends on input row order, only on (seed, namespace, ids).
"""

from __future__ import annotations

import pandas as pd

from src.generator.rng import rng_for


def assign_pooled_slot(entity_ids: pd.Series, seed: int, namespace: str, pool_ratio: float) -> pd.Series:
    """Map each distinct entity_id to a deterministic pool-slot index.

    pool_size = max(1, round(n_distinct_entities * pool_ratio)) — a ratio
    below 1.0 guarantees some entities share a slot (ambient collision).
    """
    if not 0 < pool_ratio <= 1:
        raise ValueError("pool_ratio must be in (0, 1]")

    distinct = sorted(entity_ids.astype(str).unique().tolist())
    n = len(distinct)
    pool_size = max(1, round(n * pool_ratio))

    rng = rng_for(seed, "pool-slot", namespace)
    slot_assignment = rng.integers(0, pool_size, size=n)
    slot_map = dict(zip(distinct, slot_assignment.tolist()))

    return entity_ids.astype(str).map(slot_map)
