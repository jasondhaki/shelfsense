"""SIMULATION_ENGINE §12 test vectors + invariants (conservation, no negative stock,
determinism) + §11 edge cases."""

import pytest

from app.sim import engine, kpi, pricing, procurement, rng
from app.sim.cli import load_config, run
from app.sim.demand import price_mult
from app.sim.events import Event
from app.sim.shelf_life import age, alpha_from_vision, beta_sku, rsl_known, rsl_true
from app.sim.state import CYCLE_TICKS, Batch, SkuConfig


def _batch(sl: float, alpha: float = 1.0) -> Batch:
    return Batch("b", "X", 10, 0, sl_true=sl, sl_known=sl, alpha_true=alpha, alpha_known=alpha)


def _aged(b: Batch, beta: float, ticks: int) -> Batch:
    for _ in range(ticks):
        age(b, beta)
    return b


# --- §12 vectors ----------------------------------------------------------------


def test_rsl_healthy():
    b = _aged(_batch(72), 1.0, 10)
    assert b.age_true == 10 and rsl_true(b, 1.0) == 62


def test_rsl_damaged_spoils_at_36_not_72():
    b = _aged(_batch(72, alpha=2.0), 1.0, 10)
    assert b.age_true == 20 and rsl_true(b, 1.0) == 26
    b = _batch(72, alpha=2.0)
    ticks = 0
    while b.age_true < b.sl_true:
        age(b, 1.0)
        ticks += 1
    assert ticks == 36


def test_rsl_humid():
    beta = beta_sku(1.3, 1.0)
    b = _aged(_batch(96), beta, 10)
    assert b.age_true == pytest.approx(13)
    assert rsl_known(b, beta) == pytest.approx((96 - 13) / 1.3)


def test_pricing_vector():
    vt, _ = pricing.v_target([(40, 10.0)])
    d = pricing.gap_price(vt, 2.5, -2.0, 4.99, 0.4)
    assert vt == 4.0
    assert d["delta_q_pct"] == pytest.approx(60)
    assert d["delta_p_pct"] == pytest.approx(-30)
    assert d["p_new"] == 3.49 and not d["floor_bound"]


def test_floor_clamp():
    d = pricing.gap_price(4.0, 0.5, -2.0, 4.99, 0.4)
    assert d["delta_q_pct"] == pytest.approx(700)
    assert d["p_raw"] < 0 and d["p_new"] == 2.00 and d["floor_bound"]


def test_fefo_v_target():
    vt, idx = pricing.v_target([(10, 5.0), (30, 40.0)])
    assert vt == 2.0 and idx == 0


def test_po_quantity():
    assert procurement.po_quantity(60, 18, 1.0) == 50


def test_price_mult():
    sku = SkuConfig.from_dict(
        {
            "sku_id": "X",
            "name": "x",
            "category": "c",
            "unit_weight_kg": 1,
            "base_price_usd": 10,
            "unit_cost_usd": 5,
            "sl_nominal_hours": 48,
            "elasticity": -1.8,
            "price_floor_ratio": 0.4,
            "base_daily_units": 10,
            "weather_exposure": 1,
            "bundle_group": None,
            "supplier": "s",
        }
    )
    assert price_mult(5.0, sku, 3.0) == pytest.approx(1.9)


def test_crn_monotone():
    for i in range(500):
        u = rng.uniform(1, "demand", 0, i)
        assert rng.poisson_inv_cdf(u, 3.0) >= rng.poisson_inv_cdf(u, 2.0)


def test_determinism():
    a, la = run(load_config(42), scenario="demo")
    b, lb = run(load_config(42), scenario="demo")
    assert a.chart == b.chart
    assert kpi.kpis(a) == kpi.kpis(b)
    assert [x.message for x in la] == [x.message for x in lb]


# --- invariants -------------------------------------------------------------------


def _check_invariants(state):
    for st in (state.a, state.b):
        for sid in st.received:
            assert all(b.qty > 0 for b in st.batches[sid]), "non-positive batch qty"
            assert st.received[sid] == (
                st.sold[sid] + st.wasted[sid] + st.on_hand(sid) + st.in_boxes(sid)
            ), f"units not conserved: store {st.name} {sid}"


@pytest.mark.parametrize(
    "par, timeline",
    [
        (1.25, {}),
        # stressed: big par + every event type, so waste, boxes and box sales all occur
        (
            4.0,
            {
                10: [Event("cold_chain_delay", {"immediate": True})],
                30: [Event("rainstorm")],
                40: [Event("cold_chain_delay")],
                60: [Event("vision_override", {"sku_id": "STRW-01", "alpha": 3.0})],
                61: [Event("vision_override", {"sku_id": "SOUR-01", "alpha": 3.0})],
            },
        ),
    ],
)
def test_conservation_and_no_negative_stock(par, timeline):
    state = engine.new_sim(load_config(7, store_a_par_mult=par))
    for _ in range(CYCLE_TICKS):
        state, _ = engine.step(state, timeline.get(state.tick, []))
        _check_invariants(state)
    if timeline:
        assert state.b.boxes, "stress run should exercise bundling"
        assert state.a.waste_kg > 0


def test_cli_speed():
    import time

    t0 = time.perf_counter()
    run(load_config(42))
    assert time.perf_counter() - t0 < 2.0


# --- §11 edge cases ---------------------------------------------------------------


def test_zero_forecast_goes_to_floor():
    d = pricing.gap_price(1.0, 0.0, -2.0, 4.99, 0.4)
    assert d["p_new"] == 2.00 and d["floor_bound"]


def test_all_rsl_zero_is_no_risk():
    vt, idx = pricing.v_target([(10, 0.0)])
    assert vt == 0 and idx is None
    assert pricing.gap_price(vt, 0.0, -2.0, 4.99, 0.4)["p_new"] == 4.99


def test_waste_reduction_none_when_no_baseline_waste():
    state = engine.new_sim(load_config(1))
    assert kpi.kpis(state)["waste_reduction_pct"] is None


def test_positive_elasticity_rejected():
    with pytest.raises(ValueError):
        SkuConfig.from_dict(
            {
                "sku_id": "X",
                "name": "x",
                "category": "c",
                "unit_weight_kg": 1,
                "base_price_usd": 1,
                "unit_cost_usd": 1,
                "sl_nominal_hours": 1,
                "elasticity": 0.5,
                "price_floor_ratio": 0.4,
                "base_daily_units": 1,
                "weather_exposure": 1,
                "bundle_group": None,
                "supplier": "s",
            }
        )


def test_step_after_cycle_is_noop():
    state, _ = run(load_config(3))
    assert state.finished
    tick, chart_len = state.tick, len(state.chart)
    state, logs = engine.step(state)
    assert (state.tick, len(state.chart), logs) == (tick, chart_len, [])


def test_sold_out_keeps_price():
    state = engine.new_sim(load_config(1))
    state.b.batches["SALM-01"] = []
    state.b.price["SALM-01"] = 9.99
    engine.step(state)
    assert state.b.price["SALM-01"] == 9.99


def test_unknown_event_rejected():
    state = engine.new_sim(load_config(1))
    with pytest.raises(ValueError):
        engine.step(state, [Event("meteor")])


# --- vision α mapping (AI_PIPELINE §1.3) -----------------------------------------


@pytest.mark.parametrize(
    "q, defects, alpha",
    [
        (9.2, [], 1.0),
        (6.4, ["sugar_spotting", "surface_moisture", "ethylene_bruising"], 1.607),
        (3.8, ["mold", "ethylene_bruising", "soft_spots"], 2.5),
        (1.0, ["mold", "leakage"], 3.0),
        (None, [], 1.0),
    ],
)
def test_alpha_from_vision(q, defects, alpha):
    assert alpha_from_vision(q, defects) == pytest.approx(alpha, abs=1e-3)
