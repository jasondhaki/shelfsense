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
    gm_a = state.a.gross_margin_usd(cfg.sku_by_id)
    gm_b = state.b.gross_margin_usd(cfg.sku_by_id)
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
            "closing_stock_usd": st.closing_stock_usd(state.config.sku_by_id),
            "gross_margin_usd": st.gross_margin_usd(state.config.sku_by_id),
            "waste_kg": st.waste_kg,
        }
    return out


def chart_point(state: SimState, tick: int) -> dict:
    k = kpis(state)
    return {
        "tick": tick,
        "waste_kg_a": state.a.waste_kg,
        "waste_kg_b": state.b.waste_kg,
        "revenue_a": state.a.revenue_usd,
        "revenue_b": state.b.revenue_usd,
        "co2e_avoided_kg": k["co2e_avoided_kg"],  # KPI sparklines need the hourly history
        "net_margin_recovered_usd": k["net_margin_recovered_usd"],
    }


def category_waste_pct(state: SimState) -> dict[str, dict[str, float]]:
    """Per category: units wasted / units received × 100 for each store (FAO's '% of what
    enters the stage'), for the calibration check against retail_waste_pct."""
    out: dict[str, dict[str, float]] = {}
    for st in (state.a, state.b):
        rec: dict[str, int] = {}
        wst: dict[str, int] = {}
        for s in state.config.skus:
            rec[s.category] = rec.get(s.category, 0) + st.received[s.sku_id]
            wst[s.category] = wst.get(s.category, 0) + st.wasted[s.sku_id]
        for c in rec:
            out.setdefault(c, {})[st.name] = wst[c] / rec[c] * 100 if rec[c] else 0.0
    return out
