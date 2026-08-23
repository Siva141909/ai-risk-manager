"""Phase 2M leakage tests #3, #4, #5 — synthetic ground truth, target,
and identifiers must never appear in the feature column list the
pipeline actually produces (not just in the denylist definition, which
Phase 1H already tests in isolation)."""

from __future__ import annotations

import inspect

import pandas as pd

from src.features.leakage_guard import NON_FEATURE_COLUMNS, assert_no_leakage
from src.features.pipeline import build_feature_matrix, get_split
from src.generator.ground_truth import GROUND_TRUTH_COLUMNS
from src.models.thresholds import select_thresholds


def _toy_transactions(n: int = 300) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append(
            {
                "TransactionID": i,
                "isFraud": 1 if i % 20 == 0 else 0,
                "TransactionDT": 86400 + i * 500,
                "TransactionAmt": 20.0 + (i % 50),
                "ProductCD": ["W", "C", "R", "H", "S"][i % 5],
                "card1": 1000 + (i % 40),
                "card2": 100.0,
                "card3": 150.0,
                "card4": "visa",
                "card5": 200.0,
                "card6": "debit",
                "addr1": 300.0 if i % 7 else None,
                "addr2": 87.0,
                "dist1": None,
                "dist2": None,
                "P_emaildomain": "gmail.com",
                "R_emaildomain": None,
                **{f"C{j}": float(j) for j in range(1, 15)},
                **{f"D{j}": (float(j) if i % 3 else None) for j in range(1, 16)},
                **{f"M{j}": ("T" if i % 2 else "F") for j in range(1, 10)},
                **{f"V{j}": (1.0 if i % 4 else None) for j in range(1, 10)},  # small V subset for speed
            }
        )
    return pd.DataFrame(rows)


def test_feature_columns_never_include_ground_truth_columns():
    df = _toy_transactions()
    artifact = build_feature_matrix(df)
    for col in GROUND_TRUTH_COLUMNS:
        assert col not in artifact.feature_columns


def test_feature_columns_never_include_target():
    df = _toy_transactions()
    artifact = build_feature_matrix(df)
    assert "isFraud" not in artifact.feature_columns


def test_feature_columns_never_include_transaction_id():
    df = _toy_transactions()
    artifact = build_feature_matrix(df)
    assert "TransactionID" not in artifact.feature_columns


def test_feature_columns_never_include_proxy_identifiers():
    df = _toy_transactions()
    artifact = build_feature_matrix(df)
    assert "customer_proxy_id" not in artifact.feature_columns
    assert "payment_instrument_proxy_id" not in artifact.feature_columns


def test_get_split_output_passes_leakage_guard():
    df = _toy_transactions()
    artifact = build_feature_matrix(df)
    for split_name in ("train", "validation", "test"):
        X, y = get_split(artifact, split_name)
        assert_no_leakage(X)  # must not raise


def test_no_feature_column_is_denylisted():
    df = _toy_transactions()
    artifact = build_feature_matrix(df)
    overlap = set(artifact.feature_columns) & NON_FEATURE_COLUMNS
    assert overlap == set()


def test_threshold_selection_has_no_test_data_parameter():
    """Structural guard for leakage test #6 (validation/test thresholds
    must not be selected using test data): select_thresholds's signature
    accepts no test-split argument at all -- there is no way to pass test
    data into it even by mistake."""
    sig = inspect.signature(select_thresholds)
    param_names = set(sig.parameters.keys())
    assert not any("test" in p.lower() for p in param_names)
