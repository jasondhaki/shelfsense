"""Flash Surplus Mystery Boxes (§6). Store B only."""

import math

from app.sim import demand, rng
from app.sim.shelf_life import beta_sku, rsl_known
from app.sim.state import Batch, Box, LogDraft, SimState

BOX_MAX_UNITS = 3
ETHYLENE_CLASH = {"producer", "sensitive"}


def ethylene_clash(cfg, a: str, b: str) -> bool:
    """An ethylene producer boxed with an ethylene-sensitive item (AI_PIPELINE §2.4)."""
    ea = cfg.sku_by_id[a].off.get("ethylene")
    eb = cfg.sku_by_id[b].off.get("ethylene")
    return {ea, eb} == ETHYLENE_CLASH


def build_boxes(state: SimState, tick: int) -> list[LogDraft]:
    cfg = state.config
    # 1. pool of excess units per SKU: list of [batch, n_units_available]
    pool: dict[str, list[list]] = {}
    for sku in cfg.skus:
        d = state.pricing.get(sku.sku_id, {})
        beta = beta_sku(state.beta_env, sku.weather_exposure)
        m_floor = demand.price_mult(
            round(sku.price_floor_ratio * sku.base_price_usd, 2), sku, cfg.max_demand_mult
        )
        for b in state.b.batches[sku.sku_id]:
            r = rsl_known(b, beta)
            if b.qty <= 0 or r <= 0 or r >= cfg.bundle_rsl_threshold_h:
                continue
            expected = demand.lam_sum(state, sku, tick, math.ceil(r)) * m_floor
            if d.get("floor_bound") or b.qty > expected:
                excess = b.qty - round(expected)
                if excess > 0:
                    pool.setdefault(sku.sku_id, []).append([b, excess])

    def units(s: str) -> int:
        return sum(n for _, n in pool.get(s, []))

    order = [s.sku_id for s in cfg.skus]

    def pick(cands: list[str]) -> str | None:
        cands = [s for s in cands if units(s) > 0]
        return max(cands, key=lambda s: (units(s), -order.index(s))) if cands else None

    def take(s: str, into: dict[str, int]) -> None:
        entry = next(e for e in pool[s] if e[1] > 0)
        entry[1] -= 1
        into[entry[0].batch_id] = into.get(entry[0].batch_id, 0) + 1

    # 2. greedy boxes: prefer distinct SKUs in the seed's bundle_group, then any SKU
    batches = {b.batch_id: b for entries in pool.values() for b, _ in entries}
    logs: list[LogDraft] = []
    while sum(units(s) for s in order) >= 2:
        seed = pick(order)
        group = cfg.sku_by_id[seed].bundle_group
        picked: dict[str, int] = {}
        in_box = [seed]
        avoided: list[tuple[str, str]] = []
        take(seed, picked)
        while len(in_box) < BOX_MAX_UNITS:
            same = [
                s
                for s in order
                if s not in in_box and group and cfg.sku_by_id[s].bundle_group == group
            ]

            safe_same = [c for c in same if not any(ethylene_clash(cfg, c, x) for x in in_box)]
            safe_any = [c for c in order if not any(ethylene_clash(cfg, c, x) for x in in_box)]
            naive = pick(same) or pick(order)
            nxt = pick(safe_same) or pick(safe_any)  # swap away from a clash if we can
            if nxt is None and len(in_box) < 2:
                nxt = naive  # only accept a clash when the box can't reach its 2-unit minimum
            if naive and nxt != naive and any(ethylene_clash(cfg, naive, x) for x in in_box):
                clash = next(x for x in in_box if ethylene_clash(cfg, naive, x))
                avoided.append((naive, clash))
            if nxt is None:
                break
            in_box.append(nxt)
            take(nxt, picked)
        clashes = sorted(
            {tuple(sorted((a, b))) for a in in_box for b in in_box if ethylene_clash(cfg, a, b)}
        )
        items: list[Batch] = []
        for bid, n in picked.items():
            src = batches[bid]
            items.append(src.split(n, f"{bid}/box"))
        base_total = sum(i.qty * cfg.sku_by_id[i.sku_id].base_price_usd for i in items)
        box = Box(
            box_id=state.new_id("BOX-"),
            items=items,
            base_total=round(base_total, 2),
            price=round((1 - cfg.bundle_discount) * base_total, 2),
            created_tick=tick,
        )
        state.b.boxes.append(box)
        contents = ", ".join(f"{i.qty}× {i.sku_id}" for i in items)
        msg = (
            f"Flash Surplus Mystery Box {box.box_id}: {contents} — ${box.price:.2f} "
            f"(−{cfg.bundle_discount:.0%} off ${box.base_total:.2f})"
        )
        if avoided:
            msg += "; kept " + ", ".join(f"{a} away from {b}" for a, b in avoided) + " (ethylene)"
        if clashes:
            msg += "; ethylene clash unavoidable: " + ", ".join(f"{a}+{b}" for a, b in clashes)
        logs.append(
            LogDraft(
                tick,
                "PRICING_AGENT",
                "warn" if clashes else "action",
                msg,
                {
                    "box_id": box.box_id,
                    "items": [(i.sku_id, i.qty) for i in items],
                    "ethylene_avoided": avoided,
                    "ethylene_clash": [list(c) for c in clashes],
                },
            )
        )
    for s in order:
        state.b.batches[s] = [b for b in state.b.batches[s] if b.qty > 0]
    return logs


def sell_boxes(state: SimState, tick: int) -> int:
    listed = [bx for bx in state.b.boxes if bx.status == "listed"]
    if not listed:
        return 0
    cfg = state.config
    u = rng.uniform(cfg.seed, "bundles", tick)
    n = rng.poisson_inv_cdf(u, cfg.bundle_base_rate_per_h * demand.traffic(state, tick))
    for bx in listed[:n]:
        bx.status, bx.closed_tick = "sold", tick
        state.b.revenue_usd += bx.price
        for i in bx.items:
            state.b.sold[i.sku_id] += i.qty
    return min(n, len(listed))
