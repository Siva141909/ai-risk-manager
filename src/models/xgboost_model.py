"""Phase 2C — XGBoost baseline (primary candidate, design doc Section 11).

Class imbalance handled via `scale_pos_weight` (fit from TRAIN only) —
NOT oversampling, same rationale as src/models/logistic_regression.py.
Native missing-value handling (design doc Section 11) — no imputation
needed; XGBoost learns the optimal default split direction for NaN
directly from the data, which additionally lets the many
docs/FEATURE_AUDIT.md §D missingness-is-signal features contribute
through their raw NaN pattern as well as their explicit `_is_missing`
indicator.

Hyperparameters are a small, reasonable fixed set plus early stopping on
the VALIDATION split's PR-AUC (aucpr) — not an exhaustive grid search.
Phase 2's instruction is explicit: "the goal is a defensible,
reproducible risk-scoring baseline," not a leaderboard score, so no
extensive tuning is performed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import xgboost as xgb


@dataclass(frozen=True)
class XGBParams:
    max_depth: int = 6
    learning_rate: float = 0.05
    n_estimators: int = 500
    early_stopping_rounds: int = 30
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: int = 5


def fit_xgboost(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    seed: int,
    params: XGBParams = XGBParams(),
) -> xgb.Booster:
    scale_pos_weight = float((y_train == 0).sum() / max((y_train == 1).sum(), 1))

    dtrain = xgb.DMatrix(X_train, label=y_train, missing=np.nan)
    dval = xgb.DMatrix(X_val, label=y_val, missing=np.nan)

    booster_params = {
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "max_depth": params.max_depth,
        "eta": params.learning_rate,
        "subsample": params.subsample,
        "colsample_bytree": params.colsample_bytree,
        "min_child_weight": params.min_child_weight,
        "scale_pos_weight": scale_pos_weight,
        "seed": seed,
        "nthread": -1,
    }

    booster = xgb.train(
        booster_params,
        dtrain,
        num_boost_round=params.n_estimators,
        evals=[(dtrain, "train"), (dval, "validation")],
        early_stopping_rounds=params.early_stopping_rounds,
        verbose_eval=False,
    )
    return booster


def predict_proba(booster: xgb.Booster, X: pd.DataFrame) -> np.ndarray:
    dmat = xgb.DMatrix(X, missing=np.nan)
    iteration_range = (0, booster.best_iteration + 1) if hasattr(booster, "best_iteration") else None
    if iteration_range:
        return booster.predict(dmat, iteration_range=iteration_range)
    return booster.predict(dmat)
