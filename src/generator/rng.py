"""Deterministic RNG derivation for the synthetic generator.

Every synthetic value in this project must be reproducible from
(canonical seed, stable ID, generation context) alone — never from
uncontrolled randomness. Python's built-in hash() is salted per-process
by default and is NOT safe for this; this module uses SHA-256 instead,
which is stable across processes, machines, and Python versions.
"""

from __future__ import annotations

import hashlib

import numpy as np


def derive_seed(seed: int, *parts: str) -> int:
    """Deterministically derive a 64-bit integer seed from (seed, *parts)."""
    material = f"{seed}:" + ":".join(str(p) for p in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def rng_for(seed: int, *parts: str) -> np.random.Generator:
    """Return a numpy Generator deterministically derived from (seed, *parts)."""
    return np.random.default_rng(derive_seed(seed, *parts))
