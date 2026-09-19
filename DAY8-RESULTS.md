# Day 8 results: the empirical LGD surface

Computed against axes fixed in SURFACE-SPEC.md before any cell existed.

## 1. A bug found and fixed before any cell was reported

The first implementation returned **identical values for CHAIN and MARKET
granularity in every cell**. Not coincidence, algebra. Weighting each market
LGD by that market own (bd + rp) collapses exactly to the pooled figure:

```
  sum_m [ (BD_m / D_m) * D_m ] / sum_m D_m  ==  sum_m BD_m / sum_m D_m
```

The granularity axis was varying nothing. MARKET now uses **equal weight per
market**. Fixed before publication; recorded because the broken version looked
entirely plausible.

## 2. The surface

Primary LGD = badDebt / (badDebt + repaid), conditional on default, over 611
bad-debt events. Every cell carries n and a bootstrap 90% interval.

```
W1 full | ETHEREUM | 206 events
  CHAIN   include-all  99.7501%  [26.39, 99.92]     drop-largest  50.0516%
  MARKET  include-all  39.4322%  [33.60, 43.41]     drop-largest  38.2446%
  EVENT   include-all  31.9726%  [28.78, 35.21]     drop-largest  31.6408%

W1 full | BASE | 405 events
  CHAIN   include-all  18.6639%  [ 8.16, 39.18]     drop-largest  16.8308%
  MARKET  include-all  44.9631%  [35.41, 49.56]     drop-largest  46.3057%
  EVENT   include-all  17.2557%  [14.92, 19.65]     drop-largest  17.2493%

W2 trailing 12m | ETHEREUM | 77 events
  CHAIN   include-all  99.9541%  [50.06, 99.99]     drop-largest  61.8200%
  MARKET  include-all  42.6728%  [37.11, 47.65]     shrink        26.0693%
  EVENT   include-all  43.1219%  [36.11, 50.27]     shrink        26.3416%

W2 trailing 12m | BASE | 220 events
  CHAIN   include-all   6.5357%  [ 4.07, 19.94]     drop-largest  14.1783%
  MARKET  include-all  47.3675%  [38.29, 52.59]     shrink        38.6884%
  EVENT   include-all  23.3699%  [19.55, 27.34]     shrink        19.1348%
```

**SURFACE SPREAD: 5.42% to 99.95%, a factor of 18 across defensible choices.**

Per the pre-committed rule, **the spread is the result.** No cell is headline.

## 3. Where the cells fall

```
  cells within 3-7%      (near Source A LGD of 5%)       4 of 60
  cells within 0.2-0.8%  (near Source B LGD 0.3-0.5%)    0 of 60
  lowest cell anywhere on the surface                    5.42%
```

**No cell of the conditional-LGD surface reaches the Source B range.** The floor
is 5.42%, an order of magnitude above 0.5%.

## 4. The denominator finding, which is the day result

The surface measures **loss given default**: conditional on a liquidation having
produced bad debt, what fraction of the debt was lost. The Source A figure of
about 5% is that quantity.

The Source B figure of a few basis points is almost certainly **not** that
quantity. It is an unconditional loss rate over all liquidation flow, including
the great majority of liquidations that produce no bad debt at all.

In the all-liquidations pull, **611 of 7,447 USDC liquidations carry bad debt**,
so the two definitions differ by roughly two orders of magnitude, which is about
the size of the disagreement.

**Both sides may be internally correct about different quantities.** The
conditional severity really is tens of percent. The unconditional rate really is
single-digit basis points. Neither figure is wrong; they are not the same
measurement, and neither publication states which it uses.

Fifth axis of published-figure divergence, and the one sitting directly under
the dispute rather than beside it.

## 5. The secondary metric is BLOCKED -- trap 14

The all-liquidations extraction ran clean: monthly chunks, no skip ceiling hit,
short final pages, 7,447 USDC liquidations, printed complete.

**It is missing 377 of 611 known bad-debt events, including the largest.**

```
  committed bad-debt rows            611
  all-liquidations pull (USDC)     7,447
  bad-debt rows absent from pull     377
  bad debt in absent rows      $1,192,173.81  of $1,296,112
  largest absent   2026-06-06 blk 25259134  $1,181,253.93  RLP
```

A badDebtAssets_gte query returns events that a timestamp-range query over the
same period omits. **Two filters over the same events return inconsistent sets,
with no error and no indication of loss.**

**The unconditional rate cannot be computed reliably from this source.** A naive
calculation gives $103,938 / $175.2M = 5.9 bps, lands squarely in the Source B
range, and is wrong, because the numerator is missing 92% of its mass.

Most serious data-source finding in the project: the four pagination hazards
truncate at the end, but this one **omits from the middle of a complete-looking
result**.

## 6. Exit criteria

```
1. all-liquidations extraction   COMPLETED but PROVEN LOSSY, unusable
2. observed depositor band       NOT RUN, deferred
3. per-cell n and interval       DONE, all 60 cells
4. degenerate cells reported     DONE, CHAIN include-all at 99.75 and 99.95
                                 are the concentration finding as numbers
5. spread stated as the result   DONE, 18x
```

**On straddling:** the conditional surface does **not** straddle. It sits
entirely above the Source B range and brackets Source A only at its floor.
Reporting that plainly is required by the rule, and it is the opposite of what
the parametric work suggested, which is exactly why the rule was written first.
