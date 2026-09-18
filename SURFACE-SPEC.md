# Surface specification -- days 8-9

**Committed before a single empirical LGD is computed.** Same discipline as
`EXTRACTION-SPEC.md` and `MODEL-SPEC.md`, and more necessary here than in either:
by this point the answer each side wants is known, which is exactly the
condition under which axes get chosen to produce a preferred result.

---

## 1. Why the surface changed shape

The plan called for an LGD axis. **Day 5 showed that is arithmetic, not a
finding.** Required spread is `PD*LGD/T`, linear in LGD, so an LGD axis plots a
straight line through the origin and discovers nothing.

The real question is **upstream**: what empirical LGD does the loss history
imply? That is the bridge between the days 3-4 dataset and the day-5 model, and
it is the actual contribution. The dispute is 5% against 0.3-0.5%; nobody has
computed it from the realized record with the choices stated.

## 2. Axis 1 -- granularity (three points, fixed)

From the day-4 finding that concentration weakens monotonically as granularity
sharpens: 99.7% chain, 88.2% market, 73% event.

```
  CHAIN     pool all events on a chain, one LGD per chain
  MARKET    one LGD per market, then aggregate
  EVENT     the distribution over individual liquidation events
```

All three are computed and all three are reported. **Selecting one after seeing
the results is forbidden by this document.**

## 3. Axis 2 -- tail treatment (five, enumerated now with parameters)

```
  T1  include-all        no exclusion
  T2  drop-largest       exclude the single largest bad-debt event
  T3  threshold          exclude events with badDebtAssets > $100,000
  T4  bootstrap          resample events with replacement, 10,000 draws,
                         report p5 / p50 / p95
  T5  shrink             shrink toward prior LGD = 0.005 with weight
                         w = n / (n + 50), n = event count
```

T3 threshold is **$100,000**, fixed now. T5 prior is **0.005** with
pseudo-count **50**, fixed now. Both are stated in advance precisely because
either could be tuned to land on a preferred answer.

## 4. The mapping from loss history to LGD

**This is where published figures stop being comparable, so it is stated
explicitly.**

### Primary definition (LGD proper)

```
  LGD = sum(badDebtAssets) / sum(badDebtAssets + repaidAssets)
```

Numerator: loss realized. Denominator: **debt that went through liquidation** --
what was recovered plus what was not. This is loss-given-default in the credit
sense: conditional on default, what fraction was lost.

### Secondary definition (credit loss rate, NOT LGD)

```
  loss rate = sum(badDebtAssets) / average borrow outstanding
```

This is an expected-loss rate over exposure, not a conditional loss severity.
**The published bps figures on both sides are this quantity, not LGD.**
Reporting them as though they were the same number is a denominator error of the
kind days 3-4 documented. Both are computed; both are labelled.

### Time window

Two windows, both reported:

```
  W1  full pinned range
  W2  trailing 12 months from the extraction timestamp
```

**Window boundaries are a live confound, not a detail.** The day-4 temporal
finding showed bad debt realizes at liquidation, not at impairment -- the Resolv
loss realized in June 2026 for a March 2026 event. A window boundary falling
between impairment and realization assigns the loss to neither period or to the
wrong one. Each reported figure carries its window.

## 5. What the surface is, concretely

A table, not a plot: **3 granularities x 5 tail treatments x 2 windows**, each
cell reporting empirical LGD under the primary definition, with the secondary
loss rate alongside. Thirty cells per definition.

Then, and only then, the model is evaluated at the resulting LGD range to
produce required spreads, against the observed 0-20 bps.

## 6. Pre-committed reporting rules

1. **All cells are reported.** No cell is dropped for being inconvenient,
   unstable, or embarrassing.
2. **The spread of the surface is the result**, not any single cell. If
   empirical LGD ranges over an order of magnitude across defensible choices,
   that IS the finding, and it is a finding neither side has stated.
3. **No cell is designated headline** after the fact. If one is emphasised, the
   full table appears beside it.
4. **If the surface straddles both sides** -- some cells near 5%, some near
   0.3% -- that is reported as straddling, not resolved toward either.
5. **Sigma and the model mapping are held fixed across the surface.** This
   surface varies only the empirical-LGD estimation choices. Model parameter
   sensitivity is separate and already reported.

## 7. What this surface cannot do

It cannot settle the structural layer. Whether a CDP is a short put or a repo is
not a parameter and no cell of this table addresses it. That limit is carried
from `MODEL-SPEC.md` section 9 and must appear wherever the surface appears.

It also cannot correct for the exposure-pricing defect: 78% of reported borrow
exposure is unpriced, so any denominator drawn from exposure rather than from
liquidation flow inherits that problem. The primary LGD definition uses
liquidation flow specifically for this reason. The secondary loss rate does not,
and carries the caveat.
