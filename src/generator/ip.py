"""Synthetic IP address generation.

100% SYNTHETIC — no IP field exists anywhere in IEEE-CIS (confirmed,
docs/DATASET_AUDIT.md Section 14). Generated addresses are illustrative
only, not drawn from any real allocation registry.
"""

from __future__ import annotations

import pandas as pd

from src.generator.pools import assign_pooled_slot
from src.generator.rng import rng_for


def mint_ip_prefix(seed: int, salt: str) -> str:
    """A deterministic 'a.b' /16-style prefix, used to group a range (e.g. campus)."""
    rng = rng_for(seed, "ip-prefix", salt)
    a = int(rng.integers(10, 224))
    b = int(rng.integers(0, 256))
    return f"{a}.{b}"


def mint_ip(seed: int, salt: str, fixed_prefix: str | None = None) -> tuple[str, str]:
    """Return (ip_synthetic, ip_range_synthetic).

    If fixed_prefix ('a.b') is given, the host octets are minted fresh but
    the prefix (and therefore the /16 range) is shared — used for
    same-range-different-host scenarios (e.g. a campus/office subnet).
    """
    rng = rng_for(seed, "ip", salt)
    if fixed_prefix is not None:
        prefix = fixed_prefix
    else:
        a = int(rng.integers(10, 224))
        b = int(rng.integers(0, 256))
        prefix = f"{a}.{b}"
    c = int(rng.integers(0, 256))
    d = int(rng.integers(1, 255))
    ip = f"{prefix}.{c}.{d}"
    ip_range = f"{prefix}.0.0/16"
    return ip, ip_range


def assign_base_ips(customer_proxy_ids: pd.Series, seed: int, pool_ratio: float) -> pd.DataFrame:
    """Ambient (non-narrative) IP assignment: one 'home IP' per
    customer_proxy_id, with realistic pool-driven collisions (heavier
    pooling than devices — ISP/NAT sharing is common in the real world).
    """
    slots = assign_pooled_slot(customer_proxy_ids, seed, "ip", pool_ratio)
    minted = slots.map(lambda s: mint_ip(seed, s))
    return pd.DataFrame(
        {
            "ip_synthetic_id": minted.map(lambda t: t[0]),
            "ip_range_synthetic": minted.map(lambda t: t[1]),
        },
        index=customer_proxy_ids.index,
    )
