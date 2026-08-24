"""Phase 5C, Requirement 14 — the single, reproducible Track 02
held-out evaluation entrypoint.

Steps (in order, matching the Track 02 compliance requirement exactly):
 1. verify required inputs
 2. verify configuration (frozen detector manifest)
 3. verify test-set manifest (held-out benchmark immutability)
 4. run detector (the frozen, unmodified src/graph/* pipeline)
 5. calculate metrics (precision/recall/F1, overall + by ring type, 95% CI)
 6. calculate false-positive cost (illustrative)
 7. output final report

Never downloads the raw IEEE-CIS dataset — that must already exist
locally per docs/DATASET_ACQUISITION.md; this script only reads it.

Run:
    python -m scripts.run_track02_evaluation
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

from src.evaluation.track02_cost import compute_false_positive_cost
from src.evaluation.track02_manifest import compute_frozen_config_manifest
from src.graph.relationship_views import build_multi_attribute_graph
from src.graph.ring_recovery import (
    detect_communities,
    evaluate_legitimate_false_positives,
    evaluate_ring_recovery,
    summarize_false_positives,
    summarize_false_positives_by_cluster_type,
    summarize_ring_recovery,
    summarize_ring_recovery_by_abuse_type,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw" / "train_transaction.csv"
HOLDOUT_DIR = PROJECT_ROOT / "data" / "synthetic" / "holdout_test"
TEST_SET_MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "track02_holdout_test_manifest.json"
REPORT_PATH = PROJECT_ROOT / "data" / "processed" / "track02_holdout_evaluation_report.json"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def step1_verify_inputs() -> None:
    print("=== Step 1: verify required inputs ===")
    if not RAW.exists():
        sys.exit(
            f"FAIL: {RAW} not found. The raw IEEE-CIS dataset must already exist locally "
            "(docs/DATASET_ACQUISITION.md) — this script never downloads it."
        )
    required = ["transactions.parquet", "rings.json", "legitimate_clusters.json", "generation_metadata.json"]
    missing = [f for f in required if not (HOLDOUT_DIR / f).exists()]
    if missing:
        sys.exit(
            f"FAIL: held-out benchmark files missing in {HOLDOUT_DIR}: {missing}. "
            "Run `python -m scripts.generate_holdout_benchmark` first."
        )
    print("  OK: raw dataset and held-out benchmark files present.\n")


def step2_verify_configuration() -> dict:
    print("=== Step 2: verify configuration (frozen detector manifest) ===")
    manifest = compute_frozen_config_manifest()
    print(f"  combined_config_hash = {manifest['combined_config_hash']}")
    print(f"  git_commit           = {manifest['git_commit']}")
    print(f"  frozen parameters    = {json.dumps(manifest['frozen_detector_parameters'])}\n")
    return manifest


def step3_verify_test_set_manifest() -> dict:
    print("=== Step 3: verify held-out test-set manifest (immutability) ===")
    current_hashes = {
        f: _sha256_file(HOLDOUT_DIR / f)
        for f in ("transactions.parquet", "rings.json", "legitimate_clusters.json")
    }
    with (HOLDOUT_DIR / "generation_metadata.json").open() as f:
        gen_meta = json.load(f)

    current_manifest = {
        "seed": gen_meta["seed"],
        "n_transactions": gen_meta["n_transactions"],
        "n_rings": gen_meta["n_rings"],
        "n_legitimate_clusters": gen_meta["n_legitimate_clusters"],
        "file_sha256": current_hashes,
    }

    if TEST_SET_MANIFEST_PATH.exists():
        with TEST_SET_MANIFEST_PATH.open() as f:
            saved_manifest = json.load(f)
        if saved_manifest["file_sha256"] != current_hashes:
            sys.exit(
                "FAIL: the held-out benchmark files on disk do not match the previously "
                f"recorded manifest ({TEST_SET_MANIFEST_PATH}). The held-out test set must "
                "never change silently — if it was intentionally regenerated (new seed), "
                "delete the old manifest and treat this as a NEW held-out result, not a "
                "continuation of the previous one."
            )
        print("  OK: held-out benchmark matches the previously recorded manifest (unchanged since first freeze).\n")
        return saved_manifest

    with TEST_SET_MANIFEST_PATH.open("w") as f:
        json.dump(current_manifest, f, indent=2)
    print(f"  First run: recorded held-out test-set manifest at {TEST_SET_MANIFEST_PATH}")
    print("  Any future run with different held-out files will now FAIL step 3 rather than silently re-scoring.\n")
    return current_manifest


def step4_run_detector(transactions: pd.DataFrame) -> dict[str, int]:
    print("=== Step 4: run detector (frozen multi-attribute view, flat weighting, connected components) ===")
    g = build_multi_attribute_graph(transactions, weighting="flat")
    node_to_comm = detect_communities(g, method="connected_components")
    print(f"  graph: {g.number_of_nodes()} nodes, {g.number_of_edges()} edges, "
          f"{len(set(node_to_comm.values()))} components\n")
    return node_to_comm


def step5_and_6_metrics_and_cost(
    transactions: pd.DataFrame, rings: list[dict], clusters: list[dict], node_to_comm: dict
) -> dict:
    print("=== Step 5: calculate metrics (precision / recall / F1, held-out test) ===")
    ring_results = evaluate_ring_recovery(rings, node_to_comm)
    ring_overall = summarize_ring_recovery(ring_results)
    ring_by_type = summarize_ring_recovery_by_abuse_type(ring_results)

    total_detected = sum(r.get("detected_size", 0) for r in ring_results if "note" not in r)
    total_tp = sum(r.get("true_positives", 0) for r in ring_results if "note" not in r)
    member_level_false_positives = total_detected - total_tp

    print(f"  overall: precision(mean)={ring_overall['mean_precision']} recall(mean)={ring_overall['mean_recall']} "
          f"f1(mean)={ring_overall['mean_f1']}")
    print(f"  pooled precision 95% CI = {ring_overall['pooled_precision_95ci']}")
    print(f"  pooled recall 95% CI    = {ring_overall['pooled_recall_95ci']}")
    print(f"  rings: missed={ring_overall['n_missed']} partial={ring_overall['n_partial']} full={ring_overall['n_full']}")
    for at, summ in ring_by_type.items():
        print(f"    {at:22s} P(mean)={summ['mean_precision']} R(mean)={summ['mean_recall']} F1(mean)={summ['mean_f1']} "
              f"missed={summ['n_missed']} partial={summ['n_partial']} full={summ['n_full']}")

    print("\n=== Step 6: calculate false-positive cost (hard negatives) ===")
    fp_results = evaluate_legitimate_false_positives(clusters, node_to_comm, rings)
    fp_overall = summarize_false_positives(fp_results)
    fp_by_type = summarize_false_positives_by_cluster_type(fp_results)
    fp_cost = compute_false_positive_cost(fp_results, clusters, transactions)

    print(f"  FP rate = {fp_overall['false_positive_rate']} (n_scored={fp_overall['n_scored']}), "
          f"95% CI = {fp_overall['false_positive_rate_95ci']}")
    for ct, summ in fp_by_type.items():
        print(f"    {ct:12s} scored={summ['n_scored']} fp={summ['n_false_positive']} rate={summ['false_positive_rate']} "
              f"95% CI={summ['false_positive_rate_95ci']}")
    print(f"  ILLUSTRATIVE cost: {fp_cost.n_false_positive_clusters} FP clusters x "
          f"Rs.{fp_cost.cost_per_investigation_inr} = Rs.{fp_cost.total_illustrative_cost_inr}\n")

    return {
        "ring_recovery": {
            "overall": ring_overall,
            "by_abuse_type": ring_by_type,
            "detail": ring_results,
            "member_level_pooled": {
                "predicted_positive_members": total_detected,
                "true_positive_members": total_tp,
                "false_positive_members": member_level_false_positives,
            },
        },
        "false_positives": {
            "overall": fp_overall,
            "by_cluster_type": fp_by_type,
            "detail": fp_results,
            "cost": {
                "n_false_positive_clusters": fp_cost.n_false_positive_clusters,
                "n_false_positive_transactions": fp_cost.n_false_positive_transactions,
                "cost_per_investigation_inr": fp_cost.cost_per_investigation_inr,
                "total_illustrative_cost_inr": fp_cost.total_illustrative_cost_inr,
                "label": "ILLUSTRATIVE COST MODEL — not Razorpay's real internal cost, see src/evaluation/track02_cost.py",
            },
        },
    }


def main() -> None:
    step1_verify_inputs()
    config_manifest = step2_verify_configuration()
    test_set_manifest = step3_verify_test_set_manifest()

    transactions = pd.read_parquet(HOLDOUT_DIR / "transactions.parquet")
    with (HOLDOUT_DIR / "rings.json").open() as f:
        rings = json.load(f)
    with (HOLDOUT_DIR / "legitimate_clusters.json").open() as f:
        clusters = json.load(f)

    node_to_comm = step4_run_detector(transactions)
    metrics_and_cost = step5_and_6_metrics_and_cost(transactions, rings, clusters, node_to_comm)

    print("=== Step 7: output final report ===")
    report = {
        "label": "TRACK 02 HELD-OUT TEST EVALUATION — coordinated payment fraud / abuse-ring detection",
        "real_vs_synthetic_disclaimer": (
            "IEEE-CIS transactions are REAL. Ring/legitimate-cluster membership is SYNTHETIC "
            "EVALUATION GROUND TRUTH injected by src/generator/ — these precision/recall/F1 "
            "figures measure recovery of INJECTED coordinated-abuse structures, NOT real-world "
            "fraud detection against IEEE-CIS's isFraud label (see docs/ML_BASELINE.md for that, "
            "separate, evaluation)."
        ),
        "held_out_test_set": {
            "seed": test_set_manifest["seed"],
            "n_transactions": test_set_manifest["n_transactions"],
            "n_rings": test_set_manifest["n_rings"],
            "n_legitimate_clusters": test_set_manifest["n_legitimate_clusters"],
        },
        "detector_config_manifest": config_manifest,
        **metrics_and_cost,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
