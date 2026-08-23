"""Synthetic bank-account generation.

100% SYNTHETIC — no settlement/bank-account field exists anywhere in
IEEE-CIS (confirmed, docs/DATASET_AUDIT.md Section 14).
"""

from __future__ import annotations

import pandas as pd

from src.generator.pools import assign_individual_or_leaked_slot
from src.generator.rng import rng_for

# Illustrative-only prefixes, not real IFSC codes.
IFSC_BANK_CODES = ["HDFC", "ICIC", "SBIN", "AXIS", "KKBK", "UTIB"]


def mint_bank_account_id(seed: int, slot: str) -> str:
    rng = rng_for(seed, "bank-account-id", slot)
    return f"BANK-{rng.integers(0, 10**10):010d}"


def mint_ifsc_prefix(seed: int, slot: str) -> str:
    rng = rng_for(seed, "ifsc-prefix", slot)
    bank = rng.choice(IFSC_BANK_CODES)
    branch_code = int(rng.integers(0, 10**4))
    return f"{bank}0{branch_code:04d}"


def assign_base_bank_accounts(
    customer_proxy_ids: pd.Series, seed: int, leakage_prob: float, leakage_pool_size: int
) -> pd.DataFrame:
    """Ambient (non-narrative) bank-account assignment — mostly 1:1 with a
    customer_proxy; rare bounded leakage covers the odd coincidental
    collision. Deliberate joint accounts come from
    src/generator/legitimate_clusters.py, not from here.
    """
    slots = assign_individual_or_leaked_slot(
        customer_proxy_ids, seed, "bank_account", leakage_prob, leakage_pool_size
    )
    account_ids = slots.map(lambda s: mint_bank_account_id(seed, s))
    ifsc_prefixes = slots.map(lambda s: mint_ifsc_prefix(seed, s))
    return pd.DataFrame(
        {
            "bank_account_synthetic_id": account_ids,
            "ifsc_prefix_synthetic": ifsc_prefixes,
        },
        index=customer_proxy_ids.index,
    )
