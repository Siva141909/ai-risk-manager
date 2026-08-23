"""Phase 1D-1G orchestration — the full synthetic generator pipeline.

Deterministic end-to-end: same (seed, input transactions, config) ->
byte-identical output (Phase 1K reproducibility requirement, verified in
tests/unit/test_reproducibility.py).

Order matters: legitimate clusters are injected before rings, and rings
are told which customer_proxy entities are already "used" by a
legitimate cluster so no proxy is ever double-cast as both.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.generator.entity_assignment import LeakageConfig, assign_entities
from src.generator.ground_truth import consolidate_ground_truth
from src.generator.legitimate_clusters import DEFAULT_CLUSTER_TYPES, ClusterTypeConfig, inject_legitimate_clusters
from src.generator.rings import DEFAULT_RING_TYPES, RingTypeConfig, inject_rings


@dataclass
class GeneratorResult:
    transactions: pd.DataFrame
    legitimate_clusters: list[dict]
    rings: list[dict]


@dataclass(frozen=True)
class GeneratorConfig:
    leakage: LeakageConfig = field(default_factory=LeakageConfig)
    cluster_types: tuple[ClusterTypeConfig, ...] = DEFAULT_CLUSTER_TYPES
    ring_types: tuple[RingTypeConfig, ...] = DEFAULT_RING_TYPES
    decoy_attach_probability: float = 0.3


def run_generator(df: pd.DataFrame, seed: int, config: GeneratorConfig = GeneratorConfig()) -> GeneratorResult:
    assigned = assign_entities(df, seed, config.leakage)
    with_clusters, cluster_records = inject_legitimate_clusters(assigned, seed, config.cluster_types)

    used_by_clusters = {m for c in cluster_records for m in c["members"]}
    with_rings, ring_records, _ = inject_rings(
        with_clusters,
        seed,
        config.ring_types,
        config.decoy_attach_probability,
        already_used=used_by_clusters,
        legitimate_cluster_members=used_by_clusters,
    )

    final = consolidate_ground_truth(with_rings)
    return GeneratorResult(transactions=final, legitimate_clusters=cluster_records, rings=ring_records)
