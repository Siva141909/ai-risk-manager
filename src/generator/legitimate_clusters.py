"""Phase 1E — legitimate shared-infrastructure injection (mandatory hard negatives).

Households, offices, campuses, and small businesses: groups of distinct
customer_proxy entities that legitimately share device/IP/address, but
show NO coordinated fraud behavior — no deliberate temporal clustering
of transactions, no amount synchronization, no refund concentration.
Real TransactionDT/TransactionAmt/isFraud are never touched; only the
synthetic overlay (device/ip/address) and a legitimate_cluster label are
added. See docs/SYNTHETIC_DATA_GENERATION.md for pattern-by-pattern
rationale, expected size, and probability.

Candidate participants are customer_proxy entities with a small
transaction count in the working dataframe — injecting a shared-infra
narrative onto a proxy that already has hundreds of transactions
wouldn't make behavioral sense (and such proxies are already
low-confidence per docs/ENTITY_MODEL.md anyway).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.generator.address import mint_address_id, mint_pincode
from src.generator.device import mint_device_id, mint_device_type
from src.generator.ip import mint_ip, mint_ip_prefix
from src.generator.rng import rng_for

MAX_CANDIDATE_TXNS = 3


@dataclass(frozen=True)
class ClusterTypeConfig:
    name: str
    count: int
    size_min: int
    size_max: int
    share: tuple[str, ...]  # subset of {"device", "ip", "ip_range", "address"}


DEFAULT_CLUSTER_TYPES = (
    ClusterTypeConfig("household", count=15, size_min=2, size_max=5, share=("device", "ip", "address")),
    ClusterTypeConfig("office", count=6, size_min=5, size_max=15, share=("ip",)),
    ClusterTypeConfig("campus", count=2, size_min=20, size_max=60, share=("ip_range",)),
    ClusterTypeConfig("business", count=5, size_min=3, size_max=8, share=("address",)),
)


def _eligible(df: pd.DataFrame, used: set[str]) -> list[str]:
    counts = df["customer_proxy_id"].value_counts()
    return sorted(p for p in counts[counts <= MAX_CANDIDATE_TXNS].index if p not in used)


def inject_legitimate_clusters(
    df: pd.DataFrame, seed: int, cluster_types: tuple[ClusterTypeConfig, ...] = DEFAULT_CLUSTER_TYPES
) -> tuple[pd.DataFrame, list[dict]]:
    out = df.copy()
    out["legitimate_cluster_id"] = pd.NA
    out["legitimate_cluster_type"] = pd.NA

    used: set[str] = set()
    records: list[dict] = []

    for ct in cluster_types:
        rng = rng_for(seed, "legit-cluster", ct.name)
        eligible = _eligible(out, used)

        for i in range(ct.count):
            size = int(rng.integers(ct.size_min, ct.size_max + 1))
            if len(eligible) < size:
                break  # not enough remaining candidates in this dataframe slice

            chosen_pos = sorted(rng.choice(len(eligible), size=size, replace=False).tolist())
            chosen = [eligible[j] for j in chosen_pos]
            for p in chosen:
                eligible.remove(p)
            used.update(chosen)

            cluster_id = f"LEGIT-{ct.name.upper()}-{i:03d}"
            row_mask = out["customer_proxy_id"].isin(chosen)
            out.loc[row_mask, "legitimate_cluster_id"] = cluster_id
            out.loc[row_mask, "legitimate_cluster_type"] = ct.name

            if "device" in ct.share:
                out.loc[row_mask, "device_synthetic_id"] = mint_device_id(seed, cluster_id)
                out.loc[row_mask, "device_type_synthetic"] = mint_device_type(seed, cluster_id)
            if "ip" in ct.share:
                ip, ip_range = mint_ip(seed, cluster_id)
                out.loc[row_mask, "ip_synthetic_id"] = ip
                out.loc[row_mask, "ip_range_synthetic"] = ip_range
            if "ip_range" in ct.share:
                prefix = mint_ip_prefix(seed, cluster_id)
                for member_i, p in enumerate(chosen):
                    ip, ip_range = mint_ip(seed, f"{cluster_id}-member-{member_i}", fixed_prefix=prefix)
                    member_mask = out["customer_proxy_id"] == p
                    out.loc[member_mask, "ip_synthetic_id"] = ip
                    out.loc[member_mask, "ip_range_synthetic"] = ip_range
            if "address" in ct.share:
                out.loc[row_mask, "address_synthetic_id"] = mint_address_id(seed, cluster_id)
                out.loc[row_mask, "pincode_synthetic"] = mint_pincode(seed, cluster_id)

            records.append(
                {
                    "cluster_id": cluster_id,
                    "cluster_type": ct.name,
                    "size": len(chosen),
                    "members": chosen,
                }
            )

    return out, records
