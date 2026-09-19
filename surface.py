#!/usr/bin/env python3
"""
surface.py -- empirical LGD surface, per SURFACE-SPEC.md.

Axes fixed before any cell was computed:
  granularity   CHAIN / MARKET / EVENT
  tail          T1 include-all, T2 drop-largest, T3 threshold $100k,
                T4 bootstrap, T5 shrink toward 0.005 with pseudo-count 50
  window        W1 full range, W2 trailing 12 months

Primary LGD  = sum(badDebt) / sum(badDebt + repaid)   -- loss given default,
               conditional on default, computed over bad-debt events.

Every cell carries an event count and a bootstrap 90% interval.
No cell is dropped, including degenerate ones.
"""
import csv, math, random, sys

THRESHOLD = 100_000 * 10**6      # $100,000 in raw 6dp USDC
PRIOR_LGD = 0.005
PSEUDO_N = 50
BOOT = 10_000
SEED = 20260918


def load(path="dataset-baddebt-usdc.tsv"):
    out = []
    for r in csv.DictReader(open(path), delimiter="\t"):
        bd = int(r["badDebtAssets"]); rp = int(r["repaidAssets"])
        if bd <= 0:
            continue
        out.append(dict(chain=int(r["chainId"]), market=r["marketId"],
                        bd=bd, rp=rp, ts=int(r["timestamp"])))
    return out


def lgd(events):
    """Flow-weighted: total loss over total debt that went through liquidation."""
    d = sum(e["bd"] + e["rp"] for e in events)
    return (sum(e["bd"] for e in events) / d) if d else float("nan")


def apply_tail(events, treatment):
    if treatment == "T1":
        return events
    if treatment == "T2":
        if not events:
            return events
        big = max(events, key=lambda e: e["bd"])
        return [e for e in events if e is not big]
    if treatment == "T3":
        return [e for e in events if e["bd"] <= THRESHOLD]
    return events          # T4 and T5 act at aggregation, not on the set


def bootstrap_ci(events, stat, n=BOOT, seed=SEED):
    if len(events) < 2:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    vals = []
    k = len(events)
    for _ in range(n):
        s = [events[rng.randrange(k)] for _ in range(k)]
        v = stat(s)
        if v == v:
            vals.append(v)
    if not vals:
        return (float("nan"), float("nan"))
    vals.sort()
    return (vals[int(0.05 * len(vals))], vals[int(0.95 * len(vals)) - 1])


def cell(events, gran, treat, chain=None):
    """Returns (point, n, lo, hi).

    CHAIN  -- flow-weighted LGD pooled within one chain. Caller passes `chain`.
    MARKET -- per-market LGD, then EQUAL weight across markets. Equal weighting
              is deliberate: weighting each market by its own (bd+rp) collapses
              algebraically to the pooled figure, which would make the
              granularity axis vary nothing. That bug was present in the first
              implementation and is recorded in DAY8-RESULTS.md.
    EVENT  -- equal weight per event.
    """
    ev = apply_tail(events, treat)
    if chain is not None:
        ev = [e for e in ev if e["chain"] == chain]
    n = len(ev)
    if n == 0:
        return (0.0, 0, 0.0, 0.0)

    if gran == "CHAIN":
        stat = lgd
    elif gran == "MARKET":
        def stat(s):
            by = {}
            for e in s:
                by.setdefault(e["market"], []).append(e)
            vs = [lgd(v) for v in by.values()]
            vs = [v for v in vs if v == v]
            return sum(vs) / len(vs) if vs else float("nan")
    else:
        def stat(s):
            vs = [e["bd"] / (e["bd"] + e["rp"]) for e in s if (e["bd"] + e["rp"]) > 0]
            return sum(vs) / len(vs) if vs else float("nan")

    point = stat(ev)
    lo, hi = bootstrap_ci(ev, stat)

    if treat == "T4":
        # bootstrap treatment reports the resample median as its point
        rng = random.Random(SEED)
        k = len(ev)
        vals = []
        for _ in range(2000):
            s = [ev[rng.randrange(k)] for _ in range(k)]
            v = stat(s)
            if v == v:
                vals.append(v)
        if vals:
            vals.sort()
            point = vals[len(vals) // 2]

    if treat == "T5":
        w = n / (n + PSEUDO_N)
        point = w * point + (1 - w) * PRIOR_LGD
        lo = w * lo + (1 - w) * PRIOR_LGD
        hi = w * hi + (1 - w) * PRIOR_LGD
    return (point, n, lo, hi)
