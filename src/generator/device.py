"""Synthetic device generation.

100% SYNTHETIC — docs/DATASET_AUDIT.md Section 9 confirmed real
DeviceInfo cannot anchor device identity (dominated by OS/browser-family
labels, not fingerprints), so device identity here has no real basis and
must not be presented as one. See docs/ENTITY_MODEL.md.
"""

from __future__ import annotations

import pandas as pd

from src.generator.pools import assign_individual_or_leaked_slot
from src.generator.rng import rng_for

DEVICE_TYPES = ["mobile", "desktop"]
DEVICE_TYPE_WEIGHTS = [0.6, 0.4]  # illustrative only, not derived from real data


def mint_device_id(seed: int, slot: str) -> str:
    rng = rng_for(seed, "device-id", slot)
    return f"DEV-{rng.integers(0, 10**8):08d}"


def mint_device_type(seed: int, slot: str) -> str:
    rng = rng_for(seed, "device-type", slot)
    return rng.choice(DEVICE_TYPES, p=DEVICE_TYPE_WEIGHTS)


def assign_base_devices(
    customer_proxy_ids: pd.Series, seed: int, leakage_prob: float, leakage_pool_size: int
) -> pd.DataFrame:
    """Ambient (non-narrative) device assignment: mostly one UNIQUE device
    per customer_proxy_id, with rare bounded cross-population leakage
    (see src/generator/pools.py) — deliberate sharing comes from
    src/generator/legitimate_clusters.py, not from here.

    Returns a DataFrame indexed like customer_proxy_ids with columns
    device_synthetic_id, device_type_synthetic.
    """
    slots = assign_individual_or_leaked_slot(customer_proxy_ids, seed, "device", leakage_prob, leakage_pool_size)
    device_ids = slots.map(lambda s: mint_device_id(seed, s))
    device_types = slots.map(lambda s: mint_device_type(seed, s))
    return pd.DataFrame(
        {
            "device_synthetic_id": device_ids,
            "device_type_synthetic": device_types,
        },
        index=customer_proxy_ids.index,
    )
