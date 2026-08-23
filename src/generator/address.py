"""Synthetic address generation.

SYNTHETIC — the address VALUE (pincode) is fully synthetic (India-shaped,
per the design doc Section 7). Real addr1/addr2 (332 / 74 anonymized
codes, confirmed in docs/DATASET_AUDIT.md) cannot be reversed to real
geography and are not used to derive the synthetic value itself, only
optionally as a weak co-occurrence prior for who-lives-with-whom
clustering (not implemented in Phase 1 — see docs/ENTITY_MODEL.md §1).
"""

from __future__ import annotations

import pandas as pd

from src.generator.pools import assign_individual_or_leaked_slot
from src.generator.rng import rng_for

# Illustrative Indian PIN code first-digit-to-region bucket (real PIN
# structure, fictitious mapping — not a real postal directory).
PINCODE_ZONE_FIRST_DIGIT = list("123456789")


def mint_address_id(seed: int, slot: str) -> str:
    rng = rng_for(seed, "address-id", slot)
    return f"ADDR-{rng.integers(0, 10**8):08d}"


def mint_pincode(seed: int, slot: str) -> str:
    rng = rng_for(seed, "pincode", slot)
    zone = rng.choice(PINCODE_ZONE_FIRST_DIGIT)
    rest = int(rng.integers(0, 10**5))
    return f"{zone}{rest:05d}"


def assign_base_addresses(
    customer_proxy_ids: pd.Series, seed: int, leakage_prob: float, leakage_pool_size: int
) -> pd.DataFrame:
    """Ambient (non-narrative) address assignment: mostly one UNIQUE 'home
    address' per customer_proxy_id, with rare bounded leakage. Deliberate
    household/business address sharing comes from
    src/generator/legitimate_clusters.py, not from here.
    """
    slots = assign_individual_or_leaked_slot(customer_proxy_ids, seed, "address", leakage_prob, leakage_pool_size)
    address_ids = slots.map(lambda s: mint_address_id(seed, s))
    pincodes = slots.map(lambda s: mint_pincode(seed, s))
    return pd.DataFrame(
        {
            "address_synthetic_id": address_ids,
            "pincode_synthetic": pincodes,
        },
        index=customer_proxy_ids.index,
    )
