"""Entity assignment — corrected ambient layer (Phase 1.5, Decision 1).

Computes customer_proxy / payment_instrument_proxy (Phase 1C, UNCHANGED —
Decision 8 keeps this proxy definition) and a mostly-INDIVIDUAL ambient
synthetic infrastructure baseline (device/ip/bank_account/address) with
only rare, bounded cross-population leakage. This replaces Phase 1's
uniform-pooling ambient layer, which `docs/GRAPH_DATA_MODEL.md` Finding 1
showed percolates the whole graph into one giant connected component
regardless of how tight the pool ratio was pushed.

`src/generator/legitimate_clusters.py` (household/office/campus/business)
is now the PRIMARY source of deliberate sharing, applied on top of this
individual baseline — this module's job is deliberately narrow.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.generator.address import assign_base_addresses
from src.generator.bank_account import assign_base_bank_accounts
from src.generator.customer_proxy import resolve_customer_proxy, resolve_payment_instrument_proxy
from src.generator.device import assign_base_devices
from src.generator.ip import assign_base_ips


@dataclass(frozen=True)
class LeakageConfig:
    """Rare, bounded cross-population coincidence, per entity type.

    Specified as a TARGET EXPECTED COUNT of customers who leak (not a
    percentage) — a first attempt at this used a flat probability
    (e.g. 3-5%), which for the dev sample's ~11,500-20,000 customers still
    meant hundreds of people drawing from a small fixed pool, which
    itself birthday-paradox-collided into a smaller percolating clump
    (measured: a ~2,000-node component even after excluding all hub
    entity types). Using an absolute target count and deriving
    `leakage_prob = target_leak_count / n_customers` at call time keeps
    the EXPECTED number of leaking customers constant regardless of
    population size, which is what actually prevents percolation — see
    docs/GRAPH_BENCHMARK.md.
    """

    device_target_leak_count: int = 15
    device_leakage_pool_size: int = 8
    ip_target_leak_count: int = 25
    ip_leakage_pool_size: int = 12
    bank_account_target_leak_count: int = 8
    bank_account_leakage_pool_size: int = 5
    address_target_leak_count: int = 15
    address_leakage_pool_size: int = 8


def _leak_prob(target_count: int, n_customers: int) -> float:
    return min(1.0, target_count / n_customers) if n_customers > 0 else 0.0


def assign_entities(df: pd.DataFrame, seed: int, leakage: LeakageConfig = LeakageConfig()) -> pd.DataFrame:
    """Return a copy of df with proxy + ambient synthetic entity columns added.

    Required input columns: TransactionID, card1-card6, addr1,
    P_emaildomain, TransactionDT, TransactionAmt, isFraud.

    Added columns:
      customer_proxy_id, customer_proxy_confidence,
      payment_instrument_proxy_id, payment_instrument_proxy_confidence,
      device_synthetic_id, device_type_synthetic,
      ip_synthetic_id, ip_range_synthetic,
      bank_account_synthetic_id, ifsc_prefix_synthetic,
      address_synthetic_id, pincode_synthetic
    """
    out = df.copy()

    cust_id, cust_conf = resolve_customer_proxy(out)
    pi_id, pi_conf = resolve_payment_instrument_proxy(out)
    out["customer_proxy_id"] = cust_id
    out["customer_proxy_confidence"] = cust_conf
    out["payment_instrument_proxy_id"] = pi_id
    out["payment_instrument_proxy_confidence"] = pi_conf

    unique_proxies = pd.Series(out["customer_proxy_id"].unique(), name="customer_proxy_id")
    n = len(unique_proxies)

    devices = assign_base_devices(
        unique_proxies, seed, _leak_prob(leakage.device_target_leak_count, n), leakage.device_leakage_pool_size
    )
    devices["customer_proxy_id"] = unique_proxies.values
    ips = assign_base_ips(
        unique_proxies, seed, _leak_prob(leakage.ip_target_leak_count, n), leakage.ip_leakage_pool_size
    )
    ips["customer_proxy_id"] = unique_proxies.values
    banks = assign_base_bank_accounts(
        unique_proxies,
        seed,
        _leak_prob(leakage.bank_account_target_leak_count, n),
        leakage.bank_account_leakage_pool_size,
    )
    banks["customer_proxy_id"] = unique_proxies.values
    addresses = assign_base_addresses(
        unique_proxies, seed, _leak_prob(leakage.address_target_leak_count, n), leakage.address_leakage_pool_size
    )
    addresses["customer_proxy_id"] = unique_proxies.values

    for entity_df in (devices, ips, banks, addresses):
        out = out.merge(entity_df, on="customer_proxy_id", how="left", validate="many_to_one")

    return out
