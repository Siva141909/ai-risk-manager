"""Phase 1L — generate the small development dataset.

Samples N transactions deterministically from train_transaction.csv (seeded
random sample, not just a head-slice, for temporal/fraud diversity), runs
the full Phase 1D-1G synthetic generator pipeline, and writes outputs to
data/synthetic/dev/. Does NOT touch data/raw/. Does NOT generate the full
benchmark — per Phase 1L's instruction, the full-scale run only happens
after this dev dataset passes every test.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import get_seed
from src.generator.pipeline import GeneratorConfig, run_generator
from src.graph.build_graph import build_graph, edge_relationship_counts, node_type_counts

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"
OUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "dev"

N_DEV_TRANSACTIONS = 20_000

COLUMNS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6", "addr1", "P_emaildomain",
]


def sample_dev_transactions(seed: int, n: int) -> pd.DataFrame:
    df = pd.read_csv(RAW, usecols=COLUMNS)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(df), size=n, replace=False)
    idx.sort()  # preserve original (≈chronological) row order
    return df.iloc[idx].reset_index(drop=True)


def main() -> None:
    seed = get_seed()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = sample_dev_transactions(seed, N_DEV_TRANSACTIONS)
    result = run_generator(df, seed, GeneratorConfig())
    g = build_graph(result.transactions)

    transactions_path = OUT_DIR / "transactions.csv"
    result.transactions.to_csv(transactions_path, index=False)

    with (OUT_DIR / "legitimate_clusters.json").open("w") as f:
        json.dump(result.legitimate_clusters, f, indent=2)
    with (OUT_DIR / "rings.json").open("w") as f:
        json.dump(result.rings, f, indent=2)

    metadata = {
        "seed": seed,
        "n_transactions": len(df),
        "source_file": "data/raw/train_transaction.csv",
        "sampling_method": "seeded uniform random sample (numpy default_rng), sorted to preserve row order",
        "fraud_count": int(df["isFraud"].sum()),
        "fraud_rate_pct": float(df["isFraud"].mean() * 100),
        "n_legitimate_clusters": len(result.legitimate_clusters),
        "legitimate_cluster_type_counts": (
            result.transactions["legitimate_cluster_type"].value_counts(dropna=True).to_dict()
        ),
        "n_rings": len(result.rings),
        "ring_abuse_type_counts": {
            t: sum(1 for r in result.rings if r["abuse_type"] == t)
            for t in sorted({r["abuse_type"] for r in result.rings})
        },
        "synthetic_entity_label_counts": result.transactions["synthetic_entity_label"].value_counts().to_dict(),
        "graph": {
            "node_count": g.number_of_nodes(),
            "edge_count": g.number_of_edges(),
            "node_type_counts": node_type_counts(g),
            "edge_relationship_counts": edge_relationship_counts(g),
        },
    }
    with (OUT_DIR / "generation_metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(json.dumps(metadata, indent=2, default=str))
    print(f"\nWritten to {OUT_DIR}")


if __name__ == "__main__":
    main()
