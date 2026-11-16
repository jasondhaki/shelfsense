"""Store B velocity-gap pricing (§5) and Store A's printed-date markdown (§5.3)."""

import math

from app.sim import demand
from app.sim.shelf_life import beta_sku, printed_remaining, rsl_known
from app.sim.state import SimState, SkuConfig


def v_target(qty_rsl: list[tuple[int, float]]) -> tuple[float, int | None]:
    """FEFO-aware: max over batches of cumulative qty / RSL. Skips RSL == 0.
    Returns (V_target, index of the binding batch)."""
    best, idx, cum = 0.0, None, 0
    for i, (qty, rsl) in enumerate(qty_rsl):
        cum += qty
        if rsl > 0 and cum / rsl > best:
            best, idx = cum / rsl, i
    return best, idx


def gap_price(
    v_t: float,
    v_fc: float,
    elasticity: float,
    p_base: float,
    floor_ratio: float,
    model: str = "linear",
) -> dict:
    p_floor = round(floor_ratio * p_base, 2)
    out = {"delta_q_pct": 0.0, "delta_p_pct": 0.0, "p_raw": p_base, "p_floor": p_floor}
    if v_t <= 0 or (v_fc > 0 and v_t <= v_fc):
        return out | {"p_new": p_base, "risk": False, "floor_bound": False}
    if v_fc <= 0:  # §11: no forecast demand inside the horizon
        return out | {"p_raw": p_floor, "p_new": p_floor, "risk": True, "floor_bound": True}
    dq = (v_t - v_fc) / v_fc * 100
    if model == "constant":  # (P/P_base)^ε = V_t/V_f
        p_raw = p_base * (v_t / v_fc) ** (1 / elasticity)
        dp = (p_raw / p_base - 1) * 100
    else:
        dp = dq / elasticity
        p_raw = p_base * (1 + dp / 100)
    return {
        "delta_q_pct": dq,
        "delta_p_pct": dp,
        "p_raw": p_raw,
        "p_floor": p_floor,
        "p_new": round(max(p_floor, p_raw), 2),
        "risk": True,
        "floor_bound": p_raw < p_floor,
    }


def store_b_decision(state: SimState, sku: SkuConfig, tick: int) -> dict:
    """Full breakdown behind Store B's candidate price for this tick."""
    batches = state.b.batches[sku.sku_id]
    beta = beta_sku(state.beta_env, sku.weather_exposure)
    rsls = [rsl_known(b, beta) for b in batches]
    vt, i = v_target([(b.qty, r) for b, r in zip(batches, rsls, strict=True)])
    rsl = rsls[i] if i is not None else (rsls[0] if rsls else 0.0)
    vf = demand.v_forecast(state, sku, tick, rsl) if i is not None else 0.0
    d = gap_price(
        vt,
        vf,
        sku.elasticity,
        sku.base_price_usd,
        sku.price_floor_ratio,
        state.config.demand_model,
    )
    oldest = batches[0] if batches else None
    return d | {
        "sku_id": sku.sku_id,
        "tick": tick,
        "rsl_known": rsl,
        "alpha_known": oldest.alpha_known if oldest else 1.0,
        "beta_sku": beta,
        "inventory": sum(b.qty for b in batches),
        "v_target": vt,
        "v_forecast": vf,
        "elasticity": sku.elasticity,
    }


def should_publish(p_new: float, p_current: float, p_base: float, hysteresis: float) -> bool:
    return abs(p_new - p_current) / p_base >= hysteresis


def store_a_price(state: SimState, sku: SkuConfig, now: int) -> float:
    batches = state.a.batches[sku.sku_id]
    if batches and printed_remaining(batches[0], sku.sl_nominal_hours, now) <= 24:
        return round(sku.base_price_usd * (1 - state.config.store_a_markdown), 2)
    return sku.base_price_usd


# --- ESL display helpers (§5.2) -------------------------------------------------


def forecast_24h(state: SimState, sku: SkuConfig, tick: int, price: float) -> float:
    m = demand.price_mult(price, sku, state.config.max_demand_mult, state.config.demand_model)
    return demand.lam_sum(state, sku, tick, 24) * m


def surplus_risk_units(
    state: SimState,
    sku: SkuConfig,
    tick: int,
    price: float,
    store=None,
    horizon_h: float | None = None,
) -> int:
    """Stock beyond expected sales within min(24 h, shelf life). Store B uses its known RSL;
    pass `store` + `horizon_h` (e.g. printed remaining) for Store A's view."""
    store = store or state.b
    batches = store.batches[sku.sku_id]
    if not batches:
        return 0
    if horizon_h is None:
        horizon_h = rsl_known(batches[0], beta_sku(state.beta_env, sku.weather_exposure))
    h = min(24, math.ceil(max(horizon_h, 0)))
    m = demand.price_mult(price, sku, state.config.max_demand_mult, state.config.demand_model)
    return max(0, math.ceil(sum(b.qty for b in batches) - demand.lam_sum(state, sku, tick, h) * m))
