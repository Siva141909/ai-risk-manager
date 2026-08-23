"""Phase 2A feature schema — the classification in docs/FEATURE_AUDIT.md,
encoded so the feature pipeline (src/features/engineering.py) has a
single source of truth instead of re-deriving column lists inline.
"""

from __future__ import annotations

# A. Safe numeric — direct use after imputation.
SAFE_NUMERIC = [
    "TransactionAmt",
    *[f"C{i}" for i in range(1, 15)],
    "D1", "D4", "D10", "D15",
    "card2", "card3", "card5",
]

# Borderline A/D — real numeric signal, moderate missingness (28-52%),
# a real but modest present/absent fraud-rate gap (docs/FEATURE_AUDIT.md §A) —
# kept as numeric AND given a missingness indicator (not pure indicator-only
# like the severe D6-D14 block).
MODERATE_MISSINGNESS_NUMERIC = ["D2", "D3", "D5", "D11"]

# B. Safe categorical — real, measurably predictive via fraud-rate spread.
SAFE_CATEGORICAL = ["ProductCD", "card4", "card6", "card1"]

# High-missingness categorical (M-block) — raw value has modest individual
# spread; kept for encoding, but the indicator (below) carries more weight.
HIGH_MISSINGNESS_CATEGORICAL = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]

EMAIL_DOMAIN_CATEGORICAL = ["P_emaildomain", "R_emaildomain"]

# D. Severe high-missingness — measured missingness-as-signal
# (docs/FEATURE_AUDIT.md §D): present/absent fraud-rate ratio 2.3x-5.5x.
# Indicator is the primary feature; raw value is kept but de-emphasized
# (imputed, not dropped).
SEVERE_MISSINGNESS_NUMERIC = ["D6", "D7", "D8", "D9", "D12", "D13", "D14", "dist1", "dist2"]

# addr1/addr2: moderate missingness (11%) but a STRONG, inverted-direction
# present/absent signal (missing -> 4.8x HIGHER fraud rate) - distinct
# enough from the other buckets to name explicitly.
ADDRESS_NUMERIC = ["addr1", "addr2"]

V_BLOCK = [f"V{i}" for i in range(1, 340)]
V_BLOCK_HIGH_MISSINGNESS_THRESHOLD = 80.0  # percent — see docs/FEATURE_AUDIT.md §D

ID_BLOCK = [f"id_{i:02d}" for i in range(1, 39)]
IDENTITY_CATEGORICAL = ["DeviceType"]

# C. Temporal — TransactionDT itself is never used raw (docs/FEATURE_AUDIT.md
# §C/§F); only derived features from it are permitted. See
# src/features/engineering.py::add_temporal_features.
RAW_TEMPORAL_SOURCE_EXCLUDED = ["TransactionDT"]

# E/G. Excluded outright — identifiers, target, synthetic overlay/ground
# truth. Single source of truth is src/features/leakage_guard.py; this
# list is kept in sync for documentation/reference only.
from src.features.leakage_guard import NON_FEATURE_COLUMNS  # noqa: E402

ALL_NAMED_TRANSACTION_COLUMNS = (
    SAFE_NUMERIC
    + MODERATE_MISSINGNESS_NUMERIC
    + SAFE_CATEGORICAL
    + HIGH_MISSINGNESS_CATEGORICAL
    + EMAIL_DOMAIN_CATEGORICAL
    + SEVERE_MISSINGNESS_NUMERIC
    + ADDRESS_NUMERIC
    + V_BLOCK
)
