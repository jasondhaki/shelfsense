"""Store A static order-up-to (§7.1), Store B throttled PO (§7.2), 06:00 deliveries."""

import math

from app.sim import demand
from app.sim.shelf_life import beta_sku, inspect, rsl_known
from app.sim.state import (
    CLOSE_HOUR,
    DELIVERY_HOUR,
    OPEN_HOUR,
    Batch,
    LogDraft,
    SimState,
    SkuConfig,
    StoreState,
)

CARRYOVER_MIN_RSL_H = 15  # still sellable through tomorrow ~noon


def par_a(state: SimState, sku: SkuConfig) -> int:
    return math.ceil(state.config.store_a_par_mult * sku.base_daily_units)


def order_a(state: SimState, sku: SkuConfig) -> int:
    return max(0, par_a(state, sku) - state.a.on_hand(sku.sku_id))


def po_quantity(d_hat: float, carryover: float, z: float) -> int:
    return max(0, math.ceil(d_hat - carryover + z * math.sqrt(max(d_hat, 0.0))))


def next_delivery_day_start(tick: int) -> int:
    day = tick // 24 + (0 if tick % 24 < DELIVERY_HOUR else 1)
    return day * 24


def po_row(state: SimState, sku: SkuConfig, from_tick: int) -> dict:
    """Store B's PO for the next 06:00 delivery. `from_tick` = first hour not yet sold."""
    day0 = next_delivery_day_start(from_tick)
    d_hat = demand.lam_sum(state, sku, day0, 24)
    beta = beta_sku(state.beta_env, sku.weather_exposure)
    sellable = sum(
        b.qty for b in state.b.batches[sku.sku_id] if rsl_known(b, beta) >= CARRYOVER_MIN_RSL_H
    )
    carry = max(0.0, sellable - demand.lam_sum(state, sku, from_tick, day0 - from_tick))
    ai = po_quantity(d_hat, carry, state.config.safety_z)
    open_hours = range(day0 + OPEN_HOUR, day0 + CLOSE_HOUR)
    modifier = sum(demand.traffic(state, h) for h in open_hours) / len(open_hours)
    baseline = order_a(state, sku)  # projected: nothing sells overnight
    return {
        "sku_id": sku.sku_id,
        "supplier": sku.supplier,
        "baseline_order": baseline,
        "projected_carryover": round(carry),
        "weather_modifier": round(modifier, 3),
        "ai_order": ai,
        "waste_prevention_units": baseline - ai,
        "waste_prevention_kg": round((baseline - ai) * sku.unit_weight_kg, 3),
        "d_hat": d_hat,
    }


def compute_pos(state: SimState, from_tick: int, reason: str | None = None) -> list[LogDraft]:
    old = {r["sku_id"]: r["ai_order"] for r in state.po_rows}
    rows = [po_row(state, s, from_tick) for s in state.config.skus]
    state.po_rows = rows
    state.po_reason = reason
    state.b.pending_order = {r["sku_id"]: r["ai_order"] for r in rows}
    ai = sum(r["ai_order"] for r in rows)
    base = sum(r["baseline_order"] for r in rows)
    kg = sum(r["waste_prevention_kg"] for r in rows)
    if reason and old:
        changes = [
            f"{r['sku_id']} {old[r['sku_id']]}→{r['ai_order']}"
            for r in rows
            if r["sku_id"] in old and old[r["sku_id"]] != r["ai_order"]
        ]
        msg = f"PO recomputed ({reason}): " + (", ".join(changes) or "no quantity changes")
    else:
        msg = (
            f"Next-day POs: AI {ai} units vs baseline {base} (Δ {base - ai:+d} units, {kg:+.1f} kg)"
        )
    return [LogDraft(from_tick, "PROCUREMENT_AGENT", "action", msg, {"po_rows": rows})]


def receive(
    state: SimState, store: StoreState, sku: SkuConfig, qty: int, tick: int, cold_chain: bool
) -> Batch | None:
    if qty <= 0:
        return None
    sl = sku.sl_nominal_hours * (state.config.cold_chain_sl_mult if cold_chain else 1.0)
    b = Batch(
        batch_id=state.new_id(f"{sku.sku_id}@{tick}#"),
        sku_id=sku.sku_id,
        qty=qty,
        received_tick=tick,
        sl_true=sl,
        sl_known=sku.sl_nominal_hours,
    )
    if cold_chain and store.name == "B":
        inspect(b)  # "immediate vision re-evaluation" on receipt
    store.batches[sku.sku_id].append(b)
    store.batches[sku.sku_id].sort(key=lambda x: x.received_tick)
    store.received[sku.sku_id] += qty
    store.cost_received_usd += qty * sku.unit_cost_usd
    return b


def deliver(state: SimState, tick: int) -> list[LogDraft]:
    logs: list[LogDraft] = []
    flagged = []
    for sku in state.config.skus:
        cold = sku.sku_id in state.cold_chain_pending
        qa = order_a(state, sku)
        qb = state.b.pending_order.pop(sku.sku_id, 0)
        receive(state, state.a, sku, qa, tick, cold)
        receive(state, state.b, sku, qb, tick, cold)
        if cold and (qa or qb):
            flagged.append(sku.sku_id)
            state.cold_chain_pending.discard(sku.sku_id)
    if flagged:
        logs.append(
            LogDraft(
                tick,
                "VISION_AGENT",
                "warn",
                f"Cold-chain delivery inspected on receipt: {', '.join(flagged)} — shelf life "
                f"×{state.config.cold_chain_sl_mult:.2f}",
                {"skus": flagged},
            )
        )
    return logs
