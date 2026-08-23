"""Phase 1F — synthetic coordinated-abuse ring injection.

Three ring types (design doc Section 4/8): shared_device,
shared_bank_account, multi_attribute (device+ip+bank_account).

Real TransactionDT/TransactionAmt/isFraud are NEVER modified. "Temporal
concentration" and "amount pattern" are achieved by SELECTION: among
eligible small-transaction-count customer_proxy candidates, this module
picks the subset whose REAL transaction times/amounts already best match
the target pattern, rather than fabricating timing or amount. Only the
synthetic overlay (device/ip/bank_account values) and ground-truth labels
are injected.

Noise: `noise_ratio` of each ring's members are labeled as ring members
in ground truth but deliberately NOT given the shared synthetic
attribute — an evasive participant who doesn't reuse infrastructure
(design doc Judge Q&A #20).

Decoys: with `decoy_attach_probability`, 1-2 unrelated, non-ring
customer_proxy entities are attached to the ring's shared synthetic
attribute value as innocent bystanders — NOT labeled as ring members.
This is what forces "shared attribute" to be insufficient evidence on
its own, per Phase 1F's brief.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.generator.bank_account import mint_bank_account_id
from src.generator.device import mint_device_id
from src.generator.ip import mint_ip
from src.generator.rng import rng_for

MAX_CANDIDATE_TXNS = 3
MAX_WINDOW_EXPANSION_MINUTES = 48 * 60  # cap how far the burst-window search will expand


@dataclass(frozen=True)
class RingTypeConfig:
    name: str
    count: int
    size_min: int
    size_max: int
    burst_window_minutes: int
    amount_pattern: str  # "near_identical" | "varied"
    noise_ratio: float
    shared_attrs: tuple[str, ...]  # subset of {"device", "ip", "bank_account"}


DEFAULT_RING_TYPES = (
    RingTypeConfig(
        "shared_device", count=3, size_min=3, size_max=8, burst_window_minutes=360,
        amount_pattern="near_identical", noise_ratio=0.2, shared_attrs=("device",),
    ),
    RingTypeConfig(
        "shared_bank_account", count=3, size_min=3, size_max=8, burst_window_minutes=360,
        amount_pattern="varied", noise_ratio=0.2, shared_attrs=("bank_account",),
    ),
    RingTypeConfig(
        "multi_attribute", count=2, size_min=4, size_max=8, burst_window_minutes=180,
        amount_pattern="near_identical", noise_ratio=0.15, shared_attrs=("device", "ip", "bank_account"),
    ),
)


def _select_participants(
    candidates: pd.DataFrame, rng, size: int, burst_window_minutes: int, amount_pattern: str
) -> list[str] | None:
    """candidates: index=customer_proxy_id, columns include TransactionDT, TransactionAmt.

    Returns the chosen customer_proxy_ids, or None if fewer than `size`
    candidates can be found even after expanding the search window.
    """
    if len(candidates) < size:
        return None

    anchor_pos = int(rng.integers(0, len(candidates)))
    anchor_dt = candidates["TransactionDT"].iloc[anchor_pos]

    window = burst_window_minutes
    while window <= MAX_WINDOW_EXPANSION_MINUTES:
        lo, hi = anchor_dt - window * 60, anchor_dt + window * 60
        in_window = candidates[(candidates["TransactionDT"] >= lo) & (candidates["TransactionDT"] <= hi)]
        if len(in_window) >= size:
            if amount_pattern == "near_identical":
                median_amt = in_window["TransactionAmt"].median()
                ordered = in_window.assign(_dist=(in_window["TransactionAmt"] - median_amt).abs()).sort_values(
                    "_dist", kind="mergesort"
                )
                chosen = ordered.head(size)
            else:
                pos = sorted(rng.choice(len(in_window), size=size, replace=False).tolist())
                chosen = in_window.iloc[pos]
            return chosen.index.tolist()
        window *= 2
    return None


def inject_rings(
    df: pd.DataFrame,
    seed: int,
    ring_types: tuple[RingTypeConfig, ...] = DEFAULT_RING_TYPES,
    decoy_attach_probability: float = 0.3,
    already_used: set[str] | None = None,
) -> tuple[pd.DataFrame, list[dict], set[str]]:
    out = df.copy()
    out["synthetic_ring_id"] = pd.NA
    out["synthetic_abuse_type"] = pd.NA
    out["synthetic_ring_role"] = pd.NA  # "core_member" | "noise_member" | "decoy_bystander"

    used: set[str] = set(already_used) if already_used else set()
    records: list[dict] = []

    for rt in ring_types:
        rng = rng_for(seed, "ring", rt.name)
        counts = out["customer_proxy_id"].value_counts()
        eligible_ids = [p for p in counts[counts <= MAX_CANDIDATE_TXNS].index if p not in used]

        rep = (
            out[out["customer_proxy_id"].isin(eligible_ids)]
            .sort_values("TransactionDT", kind="mergesort")
            .drop_duplicates("customer_proxy_id", keep="first")
            .set_index("customer_proxy_id")[["TransactionDT", "TransactionAmt"]]
        )

        for i in range(rt.count):
            size = int(rng.integers(rt.size_min, rt.size_max + 1))
            candidates = rep.loc[[p for p in rep.index if p not in used]]
            chosen = _select_participants(candidates, rng, size, rt.burst_window_minutes, rt.amount_pattern)
            if chosen is None:
                continue

            used.update(chosen)
            ring_id = f"RING-{rt.name.upper()}-{i:03d}"

            n_noise = int(round(len(chosen) * rt.noise_ratio))
            noise_members = (
                set(rng.choice(chosen, size=n_noise, replace=False).tolist()) if n_noise > 0 else set()
            )
            core_members = [c for c in chosen if c not in noise_members]

            for member in chosen:
                mask = out["customer_proxy_id"] == member
                out.loc[mask, "synthetic_ring_id"] = ring_id
                out.loc[mask, "synthetic_abuse_type"] = rt.name
                out.loc[mask, "synthetic_ring_role"] = (
                    "noise_member" if member in noise_members else "core_member"
                )

            shared_values: dict[str, str] = {}
            if "device" in rt.shared_attrs:
                shared_values["device_synthetic_id"] = mint_device_id(seed, ring_id)
            if "ip" in rt.shared_attrs:
                ip, ip_range = mint_ip(seed, ring_id)
                shared_values["ip_synthetic_id"] = ip
                shared_values["ip_range_synthetic"] = ip_range
            if "bank_account" in rt.shared_attrs:
                shared_values["bank_account_synthetic_id"] = mint_bank_account_id(seed, ring_id)

            core_mask = out["customer_proxy_id"].isin(core_members)
            for col, val in shared_values.items():
                out.loc[core_mask, col] = val

            decoys: list[str] = []
            if shared_values and rng.random() < decoy_attach_probability:
                remaining = [p for p in eligible_ids if p not in used]
                if remaining:
                    n_decoys = min(int(rng.integers(1, 3)), len(remaining))
                    pos = sorted(rng.choice(len(remaining), size=n_decoys, replace=False).tolist())
                    decoys = [remaining[j] for j in pos]
                    used.update(decoys)
                    decoy_mask = out["customer_proxy_id"].isin(decoys)
                    for col, val in shared_values.items():
                        out.loc[decoy_mask, col] = val
                    out.loc[decoy_mask, "synthetic_ring_role"] = "decoy_bystander"
                    # synthetic_ring_id / synthetic_abuse_type stay NA for decoys —
                    # they are not ring members, only infra-sharing bystanders.

            records.append(
                {
                    "ring_id": ring_id,
                    "abuse_type": rt.name,
                    "size": len(chosen),
                    "core_members": core_members,
                    "noise_members": sorted(noise_members),
                    "decoys": decoys,
                    "shared_attrs": list(shared_values.keys()),
                }
            )

    return out, records, used
