"""Phase 5C, Requirement 13 — frozen detector configuration manifest.

Hashes exactly the files/values that determine what the coordinated-abuse
detector does: the generator (what gets injected), the graph/ring-
recovery code (how detection and scoring work), and the explicit frozen
parameters chosen in `docs/GRAPH_BENCHMARK_FULL.md` §6. Computed at the
start of every `scripts/run_track02_evaluation.py` run and written
alongside the evaluation report — if any of these files or values ever
change, the hash changes, and a stale report is visibly stale rather
than silently still claimed valid.

This does not itself PREVENT someone from editing the detector and
re-running the held-out evaluation — it makes such a change visible
(a different hash in the new report) so it can never be silently
conflated with the original, unmodified-detector result.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Every file whose content fully determines detector behavior for the
# coordinated-abuse graph pipeline (generation -> detection -> scoring).
# Deliberately does NOT include src/models/* (the ML layer is supporting
# context, not the measured detector here) or src/api/* (the API layer
# never changes detection behavior).
FROZEN_SOURCE_FILES = [
    "configs/generator.yaml",
    "configs/seed.yaml",
    "src/generator/pipeline.py",
    "src/generator/rings.py",
    "src/generator/legitimate_clusters.py",
    "src/generator/entity_assignment.py",
    "src/generator/pools.py",
    "src/generator/ground_truth.py",
    "src/generator/rng.py",
    "src/graph/relationship_views.py",
    "src/graph/ring_recovery.py",
    "src/graph/signals.py",
    "src/graph/build_graph.py",
]

# The explicit frozen configuration decision from docs/GRAPH_BENCHMARK_FULL.md
# §6 — recorded as literal values (not just "whatever the code currently
# does") so a silent code change that alters behavior without changing
# these stated values is still caught by the file hashes above.
FROZEN_DETECTOR_PARAMETERS = {
    "view": "multi_attribute",
    "relationship_types": ["SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"],
    "weighting": "flat",
    "community_detection_method": "connected_components",
    "graph_flag_min_community_size": 3,
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit_hash() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:  # noqa: BLE001 — provenance is best-effort, never fatal
        return None


def compute_frozen_config_manifest() -> dict:
    file_hashes = {}
    for rel_path in FROZEN_SOURCE_FILES:
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            raise FileNotFoundError(f"frozen source file missing: {rel_path}")
        file_hashes[rel_path] = _sha256_file(path)

    combined = hashlib.sha256(
        json.dumps(file_hashes, sort_keys=True).encode("utf-8")
        + json.dumps(FROZEN_DETECTOR_PARAMETERS, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return {
        "manifest_version": "track02-v1",
        "git_commit": _git_commit_hash(),
        "frozen_detector_parameters": FROZEN_DETECTOR_PARAMETERS,
        "source_file_sha256": file_hashes,
        "combined_config_hash": combined,
    }
