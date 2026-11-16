"""SimState -> API contracts. Read-only; all numbers come from app.sim."""

from app.models.contracts import (
    AppliedEvent,
    Bundle,
    BundleItem,
    ChartPoint,
    EslView,
    FormulaBreakdown,
    Kpis,
    PoRow,
)
from app.sim import kpi, pricing
from app.sim.demand import storm_active
from app.sim.shelf_life import beta_sku, printed_remaining, rsl_known
from app.sim.state import SimState, SkuConfig

MAX_BUNDLES = 30  # newest boxes shown in Zone D


def kpis(state: SimState) -> Kpis:
    return Kpis(**kpi.kpis(state))


def esl(state: SimState) -> list[EslView]:
    return [esl_card(state, s) for s in state.config.skus]


def esl_a(state: SimState) -> list[EslView]:
    """Baseline store's labels: it knows only the printed date, marks down 50% on the last day."""
    out = []
    for sku in state.config.skus:
        sid, t = sku.sku_id, state.tick
        batches = state.a.batches[sid]
        price = state.a.price[sid]
        on_hand = sum(b.qty for b in batches)
        printed = printed_remaining(batches[0], sku.sl_nominal_hours, t) if batches else 0.0
        if on_hand == 0:
            risk = "sold_out"
        elif price < sku.base_price_usd:
            risk = "surplus_risk"
        else:
            risk = "ok"
        out.append(
            EslView(
                sku_id=sid,
                name=sku.name,
                category=sku.category,
                nutri_score=sku.off.get("nutri_score"),
                packaging=sku.off.get("packaging"),
                ethylene=sku.off.get("ethylene"),
                on_hand=on_hand,
                forecast_24h=round(pricing.forecast_24h(state, sku, t, price), 1),
                surplus_risk_units=pricing.surplus_risk_units(
                    state, sku, t, price, state.a, printed
                ),
                rsl_hours=round(max(printed, 0.0), 1),
                printed_remaining_hours=printed,
                base_price=sku.base_price_usd,
                current_price=price,
                markdown_pct=round(1 - price / sku.base_price_usd, 4),
                risk_state=risk,
                store_a_price=price,
                shelf_life_hours=sku.sl_nominal_hours,
            )
        )
    return out


def esl_card(state: SimState, sku: SkuConfig) -> EslView:
    sid, t = sku.sku_id, state.tick
    batches = state.b.batches[sid]
    price = state.b.price[sid]
    on_hand = sum(b.qty for b in batches)
    oldest = batches[0] if batches else None
    beta = beta_sku(state.beta_env, sku.weather_exposure)
    d = state.pricing.get(sid, {})
    bundled = any(
        i.sku_id == sid for bx in state.b.boxes if bx.status == "listed" for i in bx.items
    )
    if on_hand == 0:
        risk = "sold_out"
    elif bundled:
        risk = "bundled"
    elif d.get("floor_bound"):
        risk = "floor_bound"
    elif d.get("risk"):
        risk = "surplus_risk"
    else:
        risk = "ok"
    return EslView(
        sku_id=sid,
        name=sku.name,
        category=sku.category,
        nutri_score=sku.off.get("nutri_score"),
        packaging=sku.off.get("packaging"),
        ethylene=sku.off.get("ethylene"),
        on_hand=on_hand,
        forecast_24h=round(pricing.forecast_24h(state, sku, t, price), 1),
        surplus_risk_units=pricing.surplus_risk_units(state, sku, t, price),
        rsl_hours=round(rsl_known(oldest, beta), 1) if oldest else 0.0,
        printed_remaining_hours=printed_remaining(oldest, sku.sl_nominal_hours, t)
        if oldest
        else 0.0,
        base_price=sku.base_price_usd,
        current_price=price,
        markdown_pct=round(1 - price / sku.base_price_usd, 4),
        risk_state=risk,
        store_a_price=state.a.price[sid],
        shelf_life_hours=sku.sl_nominal_hours,
    )


def formula(state: SimState, sku: SkuConfig) -> FormulaBreakdown:
    d = state.pricing.get(sku.sku_id) or pricing.store_b_decision(state, sku, state.tick)
    return FormulaBreakdown(
        **{k: v for k, v in d.items() if k in FormulaBreakdown.model_fields},
        p_current=state.b.price[sku.sku_id],
        sources=list(sku.sources),
    )


def po_table(state: SimState) -> list[PoRow]:
    return [PoRow(**r, reason=state.po_reason) for r in state.po_rows]


def bundles(state: SimState) -> list[Bundle]:
    cfg = state.config
    out = []
    for bx in state.b.boxes[-MAX_BUNDLES:]:
        if bx.status == "listed":
            exp = min(
                rsl_known(i, beta_sku(state.beta_env, cfg.sku_by_id[i.sku_id].weather_exposure))
                for i in bx.items
            )
        else:
            exp = 0.0
        out.append(
            Bundle(
                bundle_id=bx.box_id,
                items=[
                    BundleItem(sku_id=i.sku_id, name=cfg.sku_by_id[i.sku_id].name, qty=i.qty)
                    for i in bx.items
                ],
                base_total=bx.base_total,
                price=bx.price,
                created_tick=bx.created_tick,
                expires_in_hours=round(exp, 1),
                status=bx.status,
            )
        )
    return out


def chart(state: SimState) -> list[ChartPoint]:
    return [ChartPoint(**p) for p in state.chart]


def active_events(state: SimState) -> list[AppliedEvent]:
    out = []
    s = state.storm_start
    if s is not None and storm_active(state, state.tick):
        end = s + state.config.rain_duration_h
        ev = next((e for e in reversed(state.event_log) if e["type"] == "rainstorm"), None)
        out.append(
            AppliedEvent(
                tick=s, type="rainstorm", payload=ev["payload"] if ev else {}, active_until_tick=end
            )
        )
    if state.cold_chain_pending:
        ev = next((e for e in reversed(state.event_log) if e["type"] == "cold_chain_delay"), None)
        out.append(
            AppliedEvent(
                tick=ev["tick"] if ev else state.tick,
                type="cold_chain_delay",
                payload={"skus": sorted(state.cold_chain_pending)},
            )
        )
    return out
