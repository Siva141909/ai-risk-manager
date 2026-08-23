"""Deterministic seeding utility.

Section 24 of the design doc requires the entire synthetic pipeline to be
reproducible from a single fixed seed. This module is the one place that
seeds every stochastic library in use. Extend it as new libraries
(numpy, later torch, etc.) actually get used — do not pre-seed libraries
that aren't dependencies yet.
"""

from __future__ import annotations

import random


def set_global_seed(seed: int) -> None:
    """Seed all stochastic sources currently in use by the project."""
    random.seed(seed)
    try:
        import numpy as np

        np.random.seed(seed)
    except ImportError:
        pass
