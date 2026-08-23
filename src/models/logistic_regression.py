"""Phase 2C — Logistic Regression baseline.

The simpler comparison point against XGBoost (design doc Section 11:
"kept as an interpretable sanity-check baseline"). Class imbalance
handled via `class_weight='balanced'` — NOT oversampling (SMOTE etc.),
per Phase 2's explicit instruction to avoid naive oversampling before
understanding temporal-leakage implications; class weighting reweights
the existing rows' loss contribution, it never duplicates or synthesizes
rows, so it carries no risk of manufacturing a duplicate row that
straddles the temporal split.

Median imputation + standard scaling are both fit on TRAIN only.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def fit_logistic_regression(X_train: pd.DataFrame, y_train: pd.Series, seed: int) -> Pipeline:
    pipeline = Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=seed,
                    solver="lbfgs",
                ),
            ),
        ]
    )
    pipeline.fit(X_train, y_train)
    return pipeline


def predict_proba(pipeline: Pipeline, X: pd.DataFrame) -> np.ndarray:
    return pipeline.predict_proba(X)[:, 1]
