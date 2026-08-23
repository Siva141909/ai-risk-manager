"""Phase 1G — ground-truth consolidation.

Combines the real label with the synthetic overlay labels into clearly
separated, explicitly named columns — never merged into one ambiguous
field, and the real `isFraud` column is never overwritten (an explicit
`original_isFraud` alias is added instead, so any future synthetic
fraud-like field can never be confused with it downstream). See
src/features/leakage_guard.py (Phase 1H) for the rule that none of these
synthetic columns may reach a model feature matrix.
"""

from __future__ import annotations

import pandas as pd

GROUND_TRUTH_COLUMNS = [
    "original_isFraud",
    "synthetic_ring_id",
    "synthetic_abuse_type",
    "synthetic_ring_role",
    "legitimate_cluster_id",
    "legitimate_cluster_type",
    "synthetic_entity_label",
]


def _label_row(ring_id, ring_role, legit_cluster_id) -> str:
    if pd.notna(ring_id):
        return "ring_member"
    if pd.notna(ring_role) and ring_role == "decoy_bystander":
        return "decoy_bystander"
    if pd.notna(legit_cluster_id):
        return "legitimate_shared_infra"
    return "normal"


def consolidate_ground_truth(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["original_isFraud"] = out["isFraud"]

    for col in ("synthetic_ring_id", "synthetic_ring_role", "legitimate_cluster_id"):
        if col not in out.columns:
            out[col] = pd.NA

    out["synthetic_entity_label"] = [
        _label_row(r, role, c)
        for r, role, c in zip(
            out["synthetic_ring_id"], out["synthetic_ring_role"], out["legitimate_cluster_id"]
        )
    ]
    return out
