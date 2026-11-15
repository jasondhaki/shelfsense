"""Effective-age shelf-life model (SIMULATION_ENGINE §3)."""

from app.sim.state import Batch


def beta_env(rh: float) -> float:
    return 1 + 0.5 * min(max((rh - 50) / 50, 0.0), 1.0)


def beta_sku(beta_e: float, exposure: float) -> float:
    return 1 + (beta_e - 1) * exposure


def age(b: Batch, beta: float, hours: float = 1.0) -> None:
    b.age_true += b.alpha_true * beta * hours
    b.age_known += b.alpha_known * beta * hours


def rsl_true(b: Batch, beta: float) -> float:
    return max(0.0, (b.sl_true - b.age_true) / (b.alpha_true * beta))


def rsl_known(b: Batch, beta: float) -> float:
    return max(0.0, (b.sl_known - b.age_known) / (b.alpha_known * beta))


def printed_remaining(b: Batch, sl_nominal: float, now: int) -> float:
    return sl_nominal - (now - b.received_tick)


def is_waste(b: Batch, sl_nominal: float, now: int) -> bool:
    """Actually spoiled, or past its printed date (must be pulled). Both stores."""
    return b.age_true >= b.sl_true or printed_remaining(b, sl_nominal, now) <= 0


def inspect(b: Batch) -> None:
    b.sl_known, b.alpha_known, b.age_known = b.sl_true, b.alpha_true, b.age_true
    b.inspected = True


ALPHA_DEFECTS = {"mold", "leakage", "ethylene_bruising"}


def alpha_from_vision(quality: float | None, defects: list[str]) -> float:
    """AI_PIPELINE §1.3: visual quality score (1–10) + defects -> α in [1, 3]."""
    if quality is None:
        return 1.0
    a = 1.0 if quality >= 8.0 else 1.0 + (8.0 - quality) * (2.0 / 7.0)
    a += 0.15 * len(ALPHA_DEFECTS & set(defects))
    return min(max(a, 1.0), 3.0)
