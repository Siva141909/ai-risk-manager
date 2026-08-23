"""Ambient-sharing assignment logic — corrected model (Phase 1.5, Decision 1).

**Superseded mechanism, kept only as history:** Phase 1 used
`assign_pooled_slot`, uniform random pooling across the ENTIRE customer
population (pool_size = n_customers * pool_ratio). `docs/GRAPH_DATA_MODEL.md`
Finding 1 showed this percolates the whole graph into one giant connected
component **even at pool_ratio -> 0.999** — a mathematical property of
uniform pooling across multiple independent channels at this population
size, not something fixable by raising the ratio.

**Corrected model:** ambient (non-narrative) sharing is now
`assign_individual_or_leaked_slot` — each entity gets a UNIQUE slot with
high probability, and only a small, FIXED-size (not population-scaled)
global "leakage pool" accounts for occasional realistic cross-population
coincidence (the same public hotspot, a popular budget phone model,
etc.), per Phase 1.5's "realism over convenience" requirement. Because
the leakage pool size is constant rather than growing with the customer
count, and only a small fraction of customers ever draw from it, this
cannot reproduce Finding 1's percolation — only a small, bounded
sub-population is ever at risk of incidental collision.

The bulk of deliberate, structured sharing now comes from
`src/generator/legitimate_clusters.py` (household/office/campus/business),
not from this ambient layer — this module's job is narrow: realistic
background noise, not the primary sharing mechanism.
"""

from __future__ import annotations

import pandas as pd

from src.generator.rng import rng_for


def assign_individual_or_leaked_slot(
    entity_ids: pd.Series, seed: int, namespace: str, leakage_prob: float, leakage_pool_size: int
) -> pd.Series:
    """Mostly-unique assignment with rare, bounded cross-population leakage.

    Each distinct entity_id gets a slot guaranteed unique to it (built
    from the id itself) with probability `1 - leakage_prob`. With
    probability `leakage_prob` it instead draws from a small FIXED-size
    pool shared by the whole population (`leakage_pool_size`, a constant,
    not scaled with population size) — this is what produces "occasional
    cross-community reuse" without reintroducing percolation.
    """
    if not 0 <= leakage_prob <= 1:
        raise ValueError("leakage_prob must be in [0, 1]")
    if leakage_pool_size < 1:
        raise ValueError("leakage_pool_size must be >= 1")

    distinct = sorted(entity_ids.astype(str).unique().tolist())
    roll_rng = rng_for(seed, "leakage-roll", namespace)
    pool_rng = rng_for(seed, "leakage-pool", namespace)
    rolls = roll_rng.random(size=len(distinct))
    pool_slots = pool_rng.integers(0, leakage_pool_size, size=len(distinct))

    slot_map: dict[str, str] = {}
    for entity_id, roll, pool_slot in zip(distinct, rolls, pool_slots):
        if roll < leakage_prob:
            slot_map[entity_id] = f"leak-{namespace}-{pool_slot}"
        else:
            slot_map[entity_id] = f"indiv-{namespace}-{entity_id}"

    return entity_ids.astype(str).map(slot_map)
