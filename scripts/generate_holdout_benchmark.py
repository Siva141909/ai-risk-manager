"""Phase 5C — genuinely held-out synthetic coordinated-abuse benchmark.

**Why this script exists, distinct from `scripts/generate_full_benchmark.py`:**
`data/synthetic/full/` (seed 42, `configs/seed.yaml`) was generated once
and then used repeatedly across Phase 1/3 to make every detector design
decision — the view choice (multi-attribute vs. single-relationship),
the weighting-strategy comparison (`scripts/graph_benchmark_full.py`
grid-searches 3 weighting strategies x 2 community-detection methods
against this exact dataset), and the resulting "frozen configuration"
in `docs/GRAPH_BENCHMARK_FULL.md` §6. That makes `data/synthetic/full/`
legitimate DEVELOPMENT/VALIDATION data — never a held-out test set, no
matter how the numbers computed on it are labeled.

This script generates a SECOND, INDEPENDENT synthetic benchmark, at the
same full scale (all 590,540 real transactions — the real data itself
never changes, only which synthetic rings/clusters get injected), using
`HOLDOUT_TEST_SEED` below — a seed that has never been read by any
generator run, weighting comparison, threshold choice, or test in this
project's history (verified by grepping the repository for every prior
seed literal before choosing it; see docs/RAZORPAY_TRACK_02_COMPLIANCE.md
§3 for the grep evidence). Uses the exact same, unmodified
`src/generator/pipeline.py::run_generator` + `GeneratorConfig` the
already-frozen benchmark used — this script changes WHICH data is
generated, never HOW.

**Non-negotiable rule, stated here so it cannot be missed:** once this
script has been run and `scripts/run_track02_evaluation.py` has reported
metrics from its output, this dataset's rings/clusters/precision/recall
numbers must NEVER be used to adjust `configs/generator.yaml`,
`src/graph/signals.py::GRAPH_FLAG_MIN_COMMUNITY_SIZE`, the chosen view,
weighting, or community-detection method. Doing so would silently turn
this held-out set into another validation set. If the detector ever
needs to change for a real reason, this held-out generation must be
re-run under a NEW seed and the old held-out result must be reported as
superseded, not quietly replaced.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from src.generator.pipeline import GeneratorConfig, run_generator
from src.graph.build_graph import build_graph, edge_relationship_counts, node_type_counts

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"
OUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "holdout_test"

# Chosen as today's generation date (2026-08-24), unrelated to seed 42
# (all dev/full/design work) or seed 99 (used only in two small unit-test
# sanity checks on a tiny in-memory sample, never for benchmark
# generation or any design decision) — see the grep evidence referenced
# in the module docstring above.
HOLDOUT_TEST_SEED = 20260824

COLUMNS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6", "addr1", "P_emaildomain",
]


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW.exists():
        raise FileNotFoundError(
            f"{RAW} not found. This script never downloads the raw IEEE-CIS dataset itself "
            "(docs/DATASET_ACQUISITION.md) — acquire it first, exactly as required for "
            "scripts/generate_full_benchmark.py."
        )

    print(f"Generating HELD-OUT TEST benchmark, seed={HOLDOUT_TEST_SEED} (independent of the seed-42 dev/full/design data)...")
    df = pd.read_csv(RAW, usecols=COLUMNS)
    print(f"  {len(df)} rows, {time.time()-t0:.1f}s elapsed")

    result = run_generator(df, HOLDOUT_TEST_SEED, GeneratorConfig())
    print(f"  generator done, {time.time()-t0:.1f}s elapsed")

    g = build_graph(result.transactions)
    print(f"  full heterogeneous graph built (context only, not used for detection), {time.time()-t0:.1f}s elapsed")

    result.transactions.to_parquet(OUT_DIR / "transactions.parquet", index=False)
    with (OUT_DIR / "legitimate_clusters.json").open("w") as f:
        json.dump(result.legitimate_clusters, f, indent=2)
    with (OUT_DIR / "rings.json").open("w") as f:
        json.dump(result.rings, f, indent=2)

    t = result.transactions
    metadata = {
        "purpose": "HELD-OUT TEST — never used for any detector design decision",
        "seed": HOLDOUT_TEST_SEED,
        "n_transactions": len(df),
        "elapsed_seconds": round(time.time() - t0, 1),
        "n_customer_proxy": int(t["customer_proxy_id"].nunique()),
        "n_legitimate_clusters": len(result.legitimate_clusters),
        "legitimate_cluster_type_counts": {
            ct: sum(1 for c in result.legitimate_clusters if c["cluster_type"] == ct)
            for ct in sorted({c["cluster_type"] for c in result.legitimate_clusters})
        },
        "legitimate_cluster_row_counts": t["legitimate_cluster_type"].value_counts(dropna=True).to_dict(),
        "n_rings": len(result.rings),
        "ring_abuse_type_counts": {
            at: sum(1 for r in result.rings if r["abuse_type"] == at)
            for at in sorted({r["abuse_type"] for r in result.rings})
        },
        "ring_size_distribution": [r["size"] for r in result.rings],
        "n_decoys_total": sum(len(r["decoys"]) for r in result.rings),
        "n_noise_members_total": sum(len(r["noise_members"]) for r in result.rings),
        "synthetic_entity_label_counts": t["synthetic_entity_label"].value_counts().to_dict(),
        "full_graph_context_only": {
            "node_count": g.number_of_nodes(),
            "edge_count": g.number_of_edges(),
            "node_type_counts": node_type_counts(g),
            "edge_relationship_counts": edge_relationship_counts(g),
        },
    }
    with (OUT_DIR / "generation_metadata.json").open("w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(json.dumps({k: v for k, v in metadata.items() if k != "ring_size_distribution"}, indent=2, default=str))
    print(f"\nTotal elapsed: {time.time()-t0:.1f}s. Written to {OUT_DIR}")
    print("\nThis dataset is now HELD-OUT TEST DATA. Do not inspect its ring/cluster")
    print("composition to adjust any detector parameter. Run scripts/run_track02_evaluation.py next.")


if __name__ == "__main__":
    main()
