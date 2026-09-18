#!/usr/bin/env python3
"""
blackcox.py -- Black-Cox first-passage model for a Morpho lending position.

Mapping is stated in MODEL-SPEC.md section 1 and is an assumption, not a
derivation.

Numerical requirement carried from days 1-2: the standard normal CDF is
computed as 0.5*erfc(-x/sqrt(2)), NEVER 0.5*(1+erf(x/sqrt(2))). Default
probability for well-collateralized markets sits deep in the left tail, which
is exactly where the naive form has already discarded its significant digits.

Pure stdlib. Closed form only.
"""
import math

SQRT2 = math.sqrt(2.0)


def norm_cdf(x):
    """Standard normal CDF via erfc. See MODEL-SPEC.md section 5."""
    return 0.5 * math.erfc(-x / SQRT2)


def first_passage_pd(ltv, lltv, sigma, r, T):
    """P(collateral value touches the LLTV barrier before T).

    Continuous monitoring, geometric Brownian motion, absorbing barrier.

    b = log(V0 / B) where V0/D = 1/ltv and B/D = 1/lltv, so b = log(lltv/ltv).
    """
    if T <= 0.0:
        return 0.0
    b = math.log(lltv / ltv)          # log-distance to barrier, > 0 when ltv < lltv
    if b <= 0.0:
        return 1.0                     # already at or through the barrier
    if sigma <= 0.0:
        # Deterministic: drift r carries log-value up; barrier never touched
        # from below unless drift alone reaches it.
        return 1.0 if (r * T) <= -b else 0.0
    mu = r - 0.5 * sigma * sigma       # risk-neutral drift of log value
    s = sigma * math.sqrt(T)
    d1 = (-b - mu * T) / s
    d2 = (-b + mu * T) / s
    return norm_cdf(d1) + math.exp(-2.0 * mu * b / (sigma * sigma)) * norm_cdf(d2)


def required_spread(pd, lgd, T=1.0):
    """Annualised spread compensating expected loss. bps."""
    return (pd * lgd / T) * 1e4


def mc_first_passage(ltv, lltv, sigma, r, T, paths, steps, seed=12345):
    """Native Monte Carlo cross-check. Validation only -- never enters the
    machine. See MODEL-SPEC.md section 5."""
    b = math.log(lltv / ltv)
    dt = T / steps
    mu = r - 0.5 * sigma * sigma
    drift = mu * dt
    vol = sigma * math.sqrt(dt)
    state = seed & 0xFFFFFFFF
    hits = 0
    for _ in range(paths):
        x = 0.0
        hit = False
        for _ in range(steps):
            # Box-Muller from a deterministic LCG, so the check is reproducible
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            u1 = (state + 1) / 4294967297.0
            state = (1664525 * state + 1013904223) & 0xFFFFFFFF
            u2 = state / 4294967296.0
            z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
            x += drift + vol * z
            if x <= -b:
                hit = True
                break
        if hit:
            hits += 1
    return hits / paths
