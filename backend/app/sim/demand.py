"""Demand: expected λ (the forecast), price response, realised demand with CRN (§4)."""

import math

from app.sim import rng
from app.sim.state import SimState, SkuConfig


def storm_active(state: SimState, tick: int) -> bool:
    s = state.storm_start
    return s is not None and s <= tick < s + state.config.rain_duration_h


def traffic(state: SimState, tick: int) -> float:
    """Known traffic multiplier for any (current or future) hour."""
    cfg = state.config
    if storm_active(state, tick):
        return cfg.traffic_rain_mult
    day = tick // 24
    p = cfg.p_heavy_rain[day] if day < len(cfg.p_heavy_rain) else 0.0
    return 1 - 0.22 * p


def lam(state: SimState, sku: SkuConfig, tick: int) -> float:
    cfg = state.config
    dow = (cfg.start_dow + tick // 24) % 7
    return (
        sku.base_daily_units
        * cfg.dow_weight[sku.category][dow]
        * cfg.hour_share[sku.category][tick % 24]
        * traffic(state, tick)
    )


def lam_sum(state: SimState, sku: SkuConfig, start: int, hours: int) -> float:
    return sum(lam(state, sku, h) for h in range(start, start + max(0, hours)))


def v_forecast(state: SimState, sku: SkuConfig, tick: int, rsl: float) -> float:
    """Average λ over the wall-clock risk horizon H = ceil(RSL)."""
    h = math.ceil(rsl)
    return lam_sum(state, sku, tick, h) / h if h > 0 else 0.0


def price_mult(price: float, sku: SkuConfig, max_mult: float) -> float:
    return min(max(1 + sku.elasticity * (price / sku.base_price_usd - 1), 0.0), max_mult)


def realised(state: SimState, sku: SkuConfig, tick: int, price: float) -> int:
    cfg = state.config
    u = rng.uniform(cfg.seed, "demand", cfg.sku_index[sku.sku_id], tick)
    mean = lam(state, sku, tick) * price_mult(price, sku, cfg.max_demand_mult)
    return rng.poisson_inv_cdf(u, mean)
