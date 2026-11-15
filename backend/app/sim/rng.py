"""The only source of randomness in the sim. Counter-based: each draw is keyed, so
Store A and Store B see the same uniforms (common random numbers) and replays match."""

import math

import numpy as np

STREAMS = {"demand": 1, "bundles": 2, "demand_shock": 3}


def uniform(seed: int, stream: str, *keys: int) -> float:
    return float(np.random.default_rng([seed, STREAMS[stream], *keys]).random())


def gamma_mean1(cv: float, seed: int, stream: str, *keys: int) -> float:
    """Keyed Gamma draw with mean 1 and coefficient of variation `cv` (cv <= 0 -> 1.0)."""
    if cv <= 0:
        return 1.0
    shape = 1 / cv**2
    return float(np.random.default_rng([seed, STREAMS[stream], *keys]).gamma(shape, 1 / shape))


def poisson_inv_cdf(u: float, lam: float) -> int:
    """Smallest k with CDF(k) >= u. Monotone in lam for fixed u (CRN property)."""
    if lam <= 0:
        return 0
    p = math.exp(-lam)
    cdf = p
    k = 0
    k_max = int(lam + 20 * math.sqrt(lam) + 20)  # guards float round-off near u≈1
    while cdf < u and k < k_max:
        k += 1
        p *= lam / k
        cdf += p
    return k
