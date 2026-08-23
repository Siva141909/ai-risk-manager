"""Minimal YAML config loading utility.

Deliberately thin: reads a YAML file from configs/ relative to the project
root and returns a plain dict. No schema validation framework yet — that's
premature until Phase 1+ configs (ring_generator.yaml, thresholds.yaml)
exist with real fields to validate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"


def load_config(name: str) -> dict[str, Any]:
    """Load a YAML config file by name (e.g. "seed.yaml") from configs/."""
    path = CONFIGS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r") as f:
        return yaml.safe_load(f)


def get_seed() -> int:
    """Return the canonical project seed from configs/seed.yaml."""
    return load_config("seed.yaml")["seed"]


def get_paths() -> dict[str, Any]:
    """Return the canonical path map from configs/paths.yaml."""
    return load_config("paths.yaml")
