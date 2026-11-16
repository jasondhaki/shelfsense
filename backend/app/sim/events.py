"""User/scenario events (§8). Applied at the start of a tick; recorded for replay."""

import math
from dataclasses import dataclass, field

from app.sim import procurement
from app.sim.shelf_life import inspect
from app.sim.state import LogDraft, SimState, sim_time

DEFAULT_COLD_CHAIN_SKUS = ["STRW-01", "SPIN-01", "SALM-01"]


@dataclass(frozen=True)
class Event:
    type: str  # rainstorm | cold_chain_delay | vision_override
    payload: dict = field(default_factory=dict)


def apply(state: SimState, ev: Event, tick: int) -> list[LogDraft]:
    handler = HANDLERS.get(ev.type)
    if handler is None:
        raise ValueError(f"unknown event type {ev.type!r}")
    state.event_log.append({"tick": tick, "type": ev.type, "payload": dict(ev.payload)})
    return handler(state, ev.payload, tick)


def _rainstorm(state: SimState, payload: dict, tick: int) -> list[LogDraft]:
    cfg = state.config
    state.storm_start = tick
    end = tick + cfg.rain_duration_h
    logs = [
        LogDraft(
            tick,
            "SYSTEM",
            "warn",
            f"Heavy rainstorm for {cfg.rain_duration_h}h: traffic ×{cfg.traffic_rain_mult:.2f}, "
            f"humidity ×{cfg.humidity_spike_mult:.2f}",
            dict(payload),
        ),
        LogDraft(
            tick,
            "DEMAND_AGENT",
            "action",
            f"Storm: foot traffic −{1 - cfg.traffic_rain_mult:.0%} until "
            f"{sim_time(end)}; "
            "forecasts and clearance velocities recalculated",
        ),
    ]
    return logs + procurement.compute_pos(state, tick, reason="rainstorm")


def _cold_chain(state: SimState, payload: dict, tick: int) -> list[LogDraft]:
    skus = [s for s in payload.get("skus", DEFAULT_COLD_CHAIN_SKUS) if s in state.config.sku_by_id]
    if not payload.get("immediate"):
        state.cold_chain_pending.update(skus)
        return [
            LogDraft(
                tick,
                "SYSTEM",
                "warn",
                f"Cold-chain delay: next delivery of {', '.join(skus)} arrives with "
                f"{state.config.cold_chain_sl_mult:.0%} shelf life",
                {"skus": skus},
            )
        ]
    for sid in skus:  # emergency delivery now, identical in both stores
        sku = state.config.sku_by_id[sid]
        qty = math.ceil(sku.base_daily_units * state.config.emergency_delivery_days)
        procurement.receive(state, state.a, sku, qty, tick, cold_chain=True)
        procurement.receive(state, state.b, sku, qty, tick, cold_chain=True)
    return [
        LogDraft(
            tick,
            "VISION_AGENT",
            "warn",
            f"Emergency cold-chain delivery inspected on receipt: {', '.join(skus)} — shelf life "
            f"×{state.config.cold_chain_sl_mult:.2f}",
            {"skus": skus, "immediate": True},
        )
    ]


def _vision_override(state: SimState, payload: dict, tick: int) -> list[LogDraft]:
    sid = payload["sku_id"]
    alpha = float(payload["alpha"])
    if sid not in state.config.sku_by_id or not 1.0 <= alpha <= 3.0:
        raise ValueError("vision_override needs a known sku_id and 1.0 <= alpha <= 3.0")
    # ground truth for the bay: same shelf in both stores; only B gains the knowledge
    for store in (state.a, state.b):
        if store.batches[sid]:
            store.batches[sid][0].alpha_true = alpha
    if state.b.batches[sid]:
        inspect(state.b.batches[sid][0])
    return [
        LogDraft(
            tick,
            "VISION_AGENT",
            "action",
            _vision_message(sid, alpha, payload),
            dict(payload),
        )
    ]


def _vision_message(sid: str, alpha: float, p: dict) -> str:
    msg = f"{sid} scan {p.get('frame_id', '—')}"
    if p.get("mode"):
        msg += f" ({p['mode']})"
    if p.get("quality") is not None:
        msg += f": quality {p['quality']:.1f}"
    if p.get("defects"):
        msg += f", {', '.join(p['defects'])}"
    msg += f". α_vision {alpha:.2f}"
    if p.get("rsl_before_h") is not None and p.get("rsl_after_h") is not None:
        msg += f" → RSL {p['rsl_before_h']:.1f}h → {p['rsl_after_h']:.1f}h"
    return msg + " (oldest batch, both stores; ShelfSense now knows)"


HANDLERS = {
    "rainstorm": _rainstorm,
    "cold_chain_delay": _cold_chain,
    "vision_override": _vision_override,
}
