"""Unit tests for the corrected ambient-assignment mechanism (Phase 1.5,
Decision 1) — src/generator/pools.py."""

from __future__ import annotations

import pandas as pd

from src.generator.pools import assign_individual_or_leaked_slot


def test_zero_leakage_prob_gives_every_entity_a_unique_slot():
    ids = pd.Series([f"C{i}" for i in range(200)])
    slots = assign_individual_or_leaked_slot(ids, seed=42, namespace="test", leakage_prob=0.0, leakage_pool_size=5)
    assert slots.nunique() == 200


def test_full_leakage_prob_collapses_into_pool_size_slots():
    ids = pd.Series([f"C{i}" for i in range(200)])
    slots = assign_individual_or_leaked_slot(ids, seed=42, namespace="test", leakage_prob=1.0, leakage_pool_size=5)
    assert slots.nunique() <= 5


def test_deterministic_across_runs():
    ids = pd.Series([f"C{i}" for i in range(200)])
    s1 = assign_individual_or_leaked_slot(ids, seed=42, namespace="test", leakage_prob=0.1, leakage_pool_size=10)
    s2 = assign_individual_or_leaked_slot(ids, seed=42, namespace="test", leakage_prob=0.1, leakage_pool_size=10)
    pd.testing.assert_series_equal(s1, s2)


def test_leakage_pool_size_is_a_hard_bound_on_leaked_slots():
    """Regardless of how many entities leak, they can never spread across
    more than leakage_pool_size distinct leak slots — this is what keeps
    leakage bounded and non-percolating even at large population sizes."""
    ids = pd.Series([f"C{i}" for i in range(5000)])
    slots = assign_individual_or_leaked_slot(ids, seed=42, namespace="test", leakage_prob=0.5, leakage_pool_size=8)
    leaked = slots[slots.str.startswith("leak-")]
    assert leaked.nunique() <= 8


def test_low_leakage_prob_leaves_most_entities_individual():
    ids = pd.Series([f"C{i}" for i in range(1000)])
    slots = assign_individual_or_leaked_slot(ids, seed=42, namespace="test", leakage_prob=0.01, leakage_pool_size=5)
    n_individual = slots.str.startswith("indiv-").sum()
    assert n_individual > 950  # ~99% should remain individual at 1% leakage
