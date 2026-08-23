"""Legitimate shared-infrastructure injection — corrected model (Phase 1.5,
Decisions 1 and 6).

This is now the PRIMARY mechanism for deliberate synthetic-infra sharing
(the old Phase 1D ambient pooling layer has been narrowed to rare,
bounded background leakage — see src/generator/pools.py and
src/generator/entity_assignment.py). Four community types (household,
office, campus, business) each with **per-attribute sharing
probabilities**, not an all-or-nothing share list — per Phase 1.5's
"realism over convenience" requirement: a household does not always
share every attribute, it shares SOME attributes SOME of the time. The
probability is rolled once per cluster INSTANCE (not per member) — a
given household either shares its device or it doesn't, as a household,
matching how these patterns work in reality.

Counts are substantially higher than Phase 1 (Decision 6: "increase
legitimate shared-infrastructure cases") to give the false-positive
evaluation and the ring-recovery benchmark (docs/GRAPH_BENCHMARK.md)
enough hard negatives to be meaningful.

Real TransactionDT/TransactionAmt/isFraud are never touched; only the
synthetic overlay (device/ip/address/bank_account) and a
legitimate_cluster label are added.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.generator.address import mint_address_id, mint_pincode
from src.generator.bank_account import mint_bank_account_id
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
    share_prob: dict[str, float]  # {"device":0.4, "ip":0.5, "address":0.85, "bank_account":0.15}
    ip_range_share_prob: float = 0.0  # separate from exact-ip sharing; e.g. campus subnet
    reason: str = ""  # why this pattern is legitimate — carried into ground-truth records


DEFAULT_CLUSTER_TYPES = (
    ClusterTypeConfig(
        "household", count=60, size_min=2, size_max=5,
        share_prob={"device": 0.4, "ip": 0.5, "address": 0.85, "bank_account": 0.15},
        reason=(
            "Family members on a shared home network — occasionally a shared device "
            "or a joint account, almost always a shared mailing address; each member "
            "has independent purchase behavior and timing."
        ),
    ),
    ClusterTypeConfig(
        "office", count=20, size_min=5, size_max=15,
        share_prob={"device": 0.15, "ip": 0.8, "address": 0.0, "bank_account": 0.0},
        reason=(
            "Employees behind a shared corporate NAT egress IP — distinct devices, "
            "addresses, and payment instruments; IP is the only common signal."
        ),
    ),
    ClusterTypeConfig(
        "campus", count=5, size_min=20, size_max=60,
        share_prob={"device": 0.05, "ip": 0.0, "address": 0.0, "bank_account": 0.0},
        ip_range_share_prob=0.9,
        reason=(
            "A large population on a shared subnet (dorms/campus WiFi) — individual "
            "IPs within one shared range, minimal device overlap, independent "
            "payment instruments."
        ),
    ),
    ClusterTypeConfig(
        "business", count=15, size_min=3, size_max=8,
        share_prob={"device": 0.35, "ip": 0.45, "address": 0.55, "bank_account": 0.1},
        reason=(
            "Multiple customers associated with one shared business context (a "
            "shared workstation, a procurement account, a common delivery address) "
            "— moderate overlap on several attributes without full coordination."
        ),
    ),
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

            shared_attrs: list[str] = []

            for attr, prob in ct.share_prob.items():
                if rng.random() >= prob:
                    continue  # this instance does NOT share this attribute
                shared_attrs.append(attr)
                if attr == "device":
                    out.loc[row_mask, "device_synthetic_id"] = mint_device_id(seed, cluster_id)
                    out.loc[row_mask, "device_type_synthetic"] = mint_device_type(seed, cluster_id)
                elif attr == "ip":
                    ip, ip_range = mint_ip(seed, cluster_id)
                    out.loc[row_mask, "ip_synthetic_id"] = ip
                    out.loc[row_mask, "ip_range_synthetic"] = ip_range
                elif attr == "address":
                    out.loc[row_mask, "address_synthetic_id"] = mint_address_id(seed, cluster_id)
                    out.loc[row_mask, "pincode_synthetic"] = mint_pincode(seed, cluster_id)
                elif attr == "bank_account":
                    out.loc[row_mask, "bank_account_synthetic_id"] = mint_bank_account_id(seed, cluster_id)

            if ct.ip_range_share_prob > 0 and rng.random() < ct.ip_range_share_prob:
                shared_attrs.append("ip_range")
                prefix = mint_ip_prefix(seed, cluster_id)
                for member_i, p in enumerate(chosen):
                    ip, ip_range = mint_ip(seed, f"{cluster_id}-member-{member_i}", fixed_prefix=prefix)
                    member_mask = out["customer_proxy_id"] == p
                    out.loc[member_mask, "ip_synthetic_id"] = ip
                    out.loc[member_mask, "ip_range_synthetic"] = ip_range

            records.append(
                {
                    "cluster_id": cluster_id,
                    "cluster_type": ct.name,
                    "size": len(chosen),
                    "members": chosen,
                    "shared_attributes": shared_attrs,
                    "reason": ct.reason,
                }
            )

    return out, records
