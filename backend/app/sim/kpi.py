"""KPIs (§9) and chart points."""

from app.sim.state import SimState


def kpis(state: SimState) -> dict:
    cfg = state.config
    wa, wb = state.a.waste_kg, state.b.waste_kg
    co2e = sum(
        (state.a.wasted[s.sku_id] - state.b.wasted[s.sku_id])
        * s.unit_weight_kg
        * cfg.co2e_factor[s.category]
        for s in cfg.skus
    )
    gm_a = state.a.revenue_usd - state.a.cost_received_usd
    gm_b = state.b.revenue_usd - state.b.cost_received_usd
    return {
        "waste_reduction_pct": (wa - wb) / wa * 100 if wa > 0 else None,
        "food_diverted_kg": wa - wb,
        "co2e_avoided_kg": co2e,
        "net_margin_recovered_usd": gm_b - gm_a,
        "waste_kg_a": wa,
        "waste_kg_b": wb,
    }


def store_totals(state: SimState) -> dict:
    out = {}
    for st in (state.a, state.b):
        out[st.name] = {
            "units_received": sum(st.received.values()),
            "units_sold": sum(st.sold.values()),
            "units_wasted": sum(st.wasted.values()),
            "revenue_usd": st.revenue_usd,
            "written_off_usd": st.written_off_usd,
            "gross_margin_usd": st.revenue_usd - st.cost_received_usd,
            "waste_kg": st.waste_kg,
        }
    return out


def chart_point(state: SimState, tick: int) -> dict:
    return {
        "tick": tick,
        "waste_kg_a": state.a.waste_kg,
        "waste_kg_b": state.b.waste_kg,
        "revenue_a": state.a.revenue_usd,
        "revenue_b": state.b.revenue_usd,
    }
