"""Phase 3A — full-benchmark synthetic graph generation.

Runs the corrected (Phase 1.5) generator against ALL 590,540 real
transactions — not the 20,000-row dev sample. Uses the SAME
configuration as the dev run (configs/generator.yaml defaults,
src/generator/pipeline.py::GeneratorConfig) — the established
reproducibility configuration is not retuned for scale; only the input
data size changes. This is a deliberately more stringent test: the same
absolute number of injected rings/clusters against ~30x more background
transactions makes ring detection a much sparser "needle in haystack"
problem than the dev run.

Does NOT touch data/raw/. Ground-truth separation rules (original_isFraud
vs synthetic_* columns) are unchanged from Phase 1/1.5.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from src.config import get_seed
from src.generator.pipeline import GeneratorConfig, run_generator
from src.graph.build_graph import build_graph, edge_relationship_counts, node_type_counts

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"
OUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "full"

COLUMNS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6", "addr1", "P_emaildomain",
]


def main() -> None:
    t0 = time.time()
    seed = get_seed()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all real transactions...")
    df = pd.read_csv(RAW, usecols=COLUMNS)
    print(f"  {len(df)} rows, {time.time()-t0:.1f}s elapsed")

    print("Running generator (entity assignment + legitimate clusters + rings)...")
    result = run_generator(df, seed, GeneratorConfig())
    print(f"  done, {time.time()-t0:.1f}s elapsed")

    print("Building full heterogeneous graph (for node/edge counts only — NOT used for ring detection)...")
    g = build_graph(result.transactions)
    print(f"  done, {time.time()-t0:.1f}s elapsed")

    transactions_path = OUT_DIR / "transactions.parquet"
    result.transactions.to_parquet(transactions_path, index=False)

    with (OUT_DIR / "legitimate_clusters.json").open("w") as f:
        json.dump(result.legitimate_clusters, f, indent=2)
    with (OUT_DIR / "rings.json").open("w") as f:
        json.dump(result.rings, f, indent=2)

    t = result.transactions
    metadata = {
        "seed": seed,
        "n_transactions": len(df),
        "elapsed_seconds": round(time.time() - t0, 1),
        "n_customer_proxy": int(t["customer_proxy_id"].nunique()),
        "n_payment_instrument_proxy": int(t["payment_instrument_proxy_id"].nunique()),
        "n_devices_synthetic": int(t["device_synthetic_id"].nunique()),
        "n_ips_synthetic": int(t["ip_synthetic_id"].nunique()),
        "n_bank_accounts_synthetic": int(t["bank_account_synthetic_id"].nunique()),
        "n_addresses_synthetic": int(t["address_synthetic_id"].nunique()),
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
        "full_graph": {
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


if __name__ == "__main__":
    main()
