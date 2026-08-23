"""Phase 0 infrastructure tests.

Deliberately narrow: this validates the scaffold itself (imports, config
loading, seed reproducibility, directory layout, raw-dataset detection).
It must NOT assert anything about the content of IEEE-CIS data, because
that data is not present yet (see docs/DATASET_ACQUISITION.md) — a test
that asserted dataset facts right now would be a fake test asserting
unavailable data exists, which Phase 0 explicitly forbids.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_project_imports():
    """Core Phase 0 modules import without error."""
    import src.config  # noqa: F401
    import src.logging_conf  # noqa: F401
    import src.seed  # noqa: F401


def test_config_loading():
    from src.config import get_paths, get_seed

    assert get_seed() == 42
    paths = get_paths()
    assert paths["data"]["raw_dir"] == "data/raw"
    assert paths["data"]["ieee_cis"]["train_transaction"] == "data/raw/train_transaction.csv"


def test_seed_reproducibility():
    import random

    from src.seed import set_global_seed

    set_global_seed(42)
    first = [random.random() for _ in range(5)]

    set_global_seed(42)
    second = [random.random() for _ in range(5)]

    assert first == second


def test_required_directories_exist():
    required = [
        "data/raw",
        "data/synthetic",
        "data/processed",
        "configs",
        "src/ingestion",
        "src/generator",
        "src/features",
        "src/models",
        "src/graph",
        "src/agents",
        "src/tools",
        "src/rag",
        "src/evaluation",
        "src/api",
        "tests/unit",
        "tests/integration",
        "tests/adversarial",
        "notebooks",
        "scripts",
        "frontend",
        "docs",
    ]
    for rel in required:
        path = PROJECT_ROOT / rel
        assert path.is_dir(), f"Missing required directory: {rel}"


def test_raw_dataset_detection():
    """Reports whether IEEE-CIS files are present — does not assume either way.

    This test always passes; it exists to make dataset presence/absence a
    visible, checked fact rather than something discovered by accident
    later. See docs/DATASET_ACQUISITION.md for what to do if files are
    missing.
    """
    from src.config import get_paths

    raw_dir = PROJECT_ROOT / get_paths()["data"]["raw_dir"]
    expected_files = get_paths()["data"]["ieee_cis"].values()

    present = [f for f in expected_files if (PROJECT_ROOT / f).exists()]
    missing = [f for f in expected_files if not (PROJECT_ROOT / f).exists()]

    assert raw_dir.is_dir()
    # Informational only — surfaced via pytest -s / -v, not asserted on.
    print(f"IEEE-CIS files present: {present}")
    print(f"IEEE-CIS files missing: {missing}")
