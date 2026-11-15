"""One tick of the twin-store simulation, in the fixed order of SIMULATION_ENGINE §10.

`step` mutates and returns the state it is given (no I/O, no clock, no global RNG):
same seed + same event timeline ⇒ identical output."""

from collections.abc import Iterable

from app.sim import bundling, demand, events, kpi, pricing, procurement
from app.sim.shelf_life import age, beta_env, beta_sku, inspect, is_waste
from app.sim.state import (
    DELIVERY_HOUR,
    PO_HOUR,
    Batch,
    LogDraft,
    SimConfig,
    SimState,
    StoreState,
    is_open,
)

RH_DECAY_H = 6


def new_sim(config: SimConfig) -> SimState:
    """§7.5: both stores start with par_A fresh units of every SKU."""

    def store(name: str) -> StoreState:
        z = {s.sku_id: 0 for s in config.skus}
        return StoreState(
            name=name,
            batches={s.sku_id: [] for s in config.skus},
            price={s.sku_id: s.base_price_usd for s in config.skus},
            received=dict(z),
            sold=dict(z),
            wasted=dict(z),
        )

    state = SimState(config=config, a=store("A"), b=store("B"))
    for sku in config.skus:
        qty = procurement.par_a(state, sku)
        for st in (state.a, state.b):
            procurement.receive(state, st, sku, qty, 0, cold_chain=False)
    update_env(state, 0)
    return state


def update_env(state: SimState, t: int) -> None:
    cfg = state.config
    base = cfg.rh_base
    spike = min(98.0, base * cfg.humidity_spike_mult)
    s = state.storm_start
    if s is not None and s <= t < s + cfg.rain_duration_h:
        rh = spike
    elif s is not None and 0 <= t - (s + cfg.rain_duration_h) < RH_DECAY_H:
        rh = spike + (base - spike) * (t - (s + cfg.rain_duration_h) + 1) / RH_DECAY_H
    else:
        rh = base
    state.rh = rh
    state.beta_env = beta_env(rh)
    state.traffic = demand.traffic(state, t)


def _demand_log(state: SimState, t: int) -> LogDraft:
    lams = {s.sku_id: demand.lam(state, s, t) for s in state.config.skus}
    top = sorted(lams.items(), key=lambda kv: -kv[1])[:3]
    msg = (
        f"Traffic ×{state.traffic:.2f}, RH {state.rh:.0f}% (β_env {state.beta_env:.2f}). "
        f"Expected {sum(lams.values()):.1f} units this hour; top: "
        + ", ".join(f"{k} {v:.1f}/h" for k, v in top)
    )
    return LogDraft(t, "DEMAND_AGENT", "info", msg, {"lambda": lams, "traffic": state.traffic})


def _price_step(state: SimState, t: int) -> list[LogDraft]:
    cfg = state.config
    logs = []
    for sku in cfg.skus:
        sid = sku.sku_id
        state.a.price[sid] = pricing.store_a_price(state, sku, t)
        d = pricing.store_b_decision(state, sku, t)
        state.pricing[sid] = d
        if d["inventory"] == 0:  # §11: sold out → keep the label
            continue
        cur = state.b.price[sid]
        if pricing.should_publish(d["p_new"], cur, sku.base_price_usd, cfg.price_hysteresis):
            state.b.price[sid] = d["p_new"]
            if d["risk"]:
                msg = (
                    f"{sid} RSL {d['rsl_known']:.1f}h. V_target {d['v_target']:.1f}/h > "
                    f"V_forecast {d['v_forecast']:.1f}/h → ΔQ {d['delta_q_pct']:+.0f}% → "
                    f"ΔP {d['delta_p_pct']:+.0f}% → ${d['p_new']:.2f}"
                    + (" (floor)" if d["floor_bound"] else "")
                )
            else:
                msg = f"{sid} risk cleared → price restored ${cur:.2f} → ${d['p_new']:.2f}"
            logs.append(LogDraft(t, "PRICING_AGENT", "action", msg, d))
    return logs


def _sell(state: SimState, store: StoreState, sid: str, qty: int, price: float) -> None:
    left = qty
    for b in store.batches[sid]:  # FEFO: list is kept oldest-first
        n = min(left, b.qty)
        b.qty -= n
        left -= n
        if left == 0:
            break
    sold = qty - left
    store.sold[sid] += sold
    store.revenue_usd += sold * price
    store.batches[sid] = [b for b in store.batches[sid] if b.qty > 0]


def _waste(state: SimState, store: StoreState, sid: str, batch: Batch) -> None:
    sku = state.config.sku_by_id[sid]
    store.wasted[sid] += batch.qty
    store.waste_kg += batch.qty * sku.unit_weight_kg
    store.written_off_usd += batch.qty * sku.unit_cost_usd


def _age_and_remove(state: SimState, t: int) -> list[LogDraft]:
    now = t + 1  # end of this hour
    betas = {s.sku_id: beta_sku(state.beta_env, s.weather_exposure) for s in state.config.skus}
    logs = []
    for store in (state.a, state.b):
        for sid, batches in store.batches.items():
            keep = []
            for b in batches:
                age(b, betas[sid])
                if is_waste(b, state.config.sku_by_id[sid].sl_nominal_hours, now):
                    _waste(state, store, sid, b)
                else:
                    keep.append(b)
            store.batches[sid] = keep
    for bx in state.b.boxes:
        if bx.status != "listed":
            continue
        for i in bx.items:
            age(i, betas[i.sku_id])
        if any(i.age_true >= i.sl_true for i in bx.items):
            bx.status, bx.closed_tick = "expired", t
            for i in bx.items:
                _waste(state, state.b, i.sku_id, i)
            logs.append(
                LogDraft(
                    t,
                    "PRICING_AGENT",
                    "warn",
                    f"{bx.box_id} expired unsold — {sum(i.qty for i in bx.items)} units to waste",
                )
            )
    return logs


def step(state: SimState, queued: Iterable[events.Event] = ()) -> tuple[SimState, list[LogDraft]]:
    if state.finished:
        return state, []
    cfg = state.config
    t = state.tick
    hour = t % 24
    logs: list[LogDraft] = []

    # 1. queued events
    for ev in queued:
        logs += events.apply(state, ev, t)
    # 2. environment
    update_env(state, t)
    # 3. deliveries
    if hour == DELIVERY_HOUR:
        logs += procurement.deliver(state, t)
    # 4. automatic camera sweep (Store B gains knowledge of camera-covered SKUs)
    if t % cfg.auto_scan_every_h == 0:
        changed = []
        for sid in cfg.camera_skus:
            for b in state.b.batches.get(sid, []):
                if (b.alpha_known, b.sl_known) != (b.alpha_true, b.sl_true):
                    changed.append(sid)
                inspect(b)
        if changed:
            logs.append(
                LogDraft(
                    t,
                    "VISION_AGENT",
                    "action",
                    "CAM-04 auto-sweep: shelf-life belief updated for "
                    + ", ".join(sorted(set(changed))),
                )
            )
    # 5. demand agent (one summary line per open hour)
    if is_open(t):
        logs.append(_demand_log(state, t))
    # 6. pricing
    logs += _price_step(state, t)
    # 7. bundling
    logs += bundling.build_boxes(state, t)
    # 8. realised demand (common random numbers) + FEFO sales + box sales
    if is_open(t):
        for sku in cfg.skus:
            for store in (state.a, state.b):
                d = demand.realised(state, sku, t, store.price[sku.sku_id])
                _sell(state, store, sku.sku_id, d, store.price[sku.sku_id])
        bundling.sell_boxes(state, t)
    # 9. age, spoil, expire
    logs += _age_and_remove(state, t)
    # 10. tomorrow's PO
    if hour == PO_HOUR:
        logs += procurement.compute_pos(state, t + 1)
    # 11. KPIs + chart
    state.chart.append(kpi.chart_point(state, t))
    state.tick = t + 1
    if state.finished:
        k = kpi.kpis(state)
        red = k["waste_reduction_pct"]
        logs.append(
            LogDraft(
                t,
                "SYSTEM",
                "info",
                "Cycle complete: waste reduction "
                + (f"{red:.1f}%" if red is not None else "—")
                + f", {k['food_diverted_kg']:.1f} kg diverted",
                k,
            )
        )
    return state, logs
