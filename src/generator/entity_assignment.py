"""Entity assignment — Phase 1D orchestration.

Computes customer_proxy / payment_instrument_proxy (Phase 1C) and the
ambient (non-narrative) base synthetic infrastructure (device/ip/
bank_account/address) for every transaction. This is the "before any
story is injected" layer — realistic background collision only, from
pool pressure (src/generator/pools.py). Phase 1E (legitimate clusters)
and Phase 1F (rings) then override specific rows on top of this base.
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
class PoolRatios:
    device: float = 0.75
    ip: float = 0.55
    bank_account: float = 0.95
    address: float = 0.65


def assign_entities(df: pd.DataFrame, seed: int, pool_ratios: PoolRatios = PoolRatios()) -> pd.DataFrame:
    """Return a copy of df with proxy + base synthetic entity columns added.

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

    # Base synthetic infra is assigned PER customer_proxy_id (one "home"
    # device/ip/bank_account/address per proxy, realistic pool collisions),
    # then broadcast to every transaction belonging to that proxy.
    unique_proxies = pd.Series(out["customer_proxy_id"].unique(), name="customer_proxy_id")

    devices = assign_base_devices(unique_proxies, seed, pool_ratios.device)
    devices["customer_proxy_id"] = unique_proxies.values
    ips = assign_base_ips(unique_proxies, seed, pool_ratios.ip)
    ips["customer_proxy_id"] = unique_proxies.values
    banks = assign_base_bank_accounts(unique_proxies, seed, pool_ratios.bank_account)
    banks["customer_proxy_id"] = unique_proxies.values
    addresses = assign_base_addresses(unique_proxies, seed, pool_ratios.address)
    addresses["customer_proxy_id"] = unique_proxies.values

    for entity_df in (devices, ips, banks, addresses):
        out = out.merge(entity_df, on="customer_proxy_id", how="left", validate="many_to_one")

    return out
