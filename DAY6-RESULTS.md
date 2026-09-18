# Day 6 results: market population and the regime gate

## 1. The population is 3,904 markets, not 1,000

```
pages 40, final page 4 of 100   -- trap 12 assertion PASSED
USDC-loan markets               3,904
duplicate marketIds                 0
with collateral > 0               423
with collateral and borrow > 0    389
inactive / zero, retained       3,481
```

The day-3 enumeration returned exactly 1,000 and looked complete. The true
population is **3.9x larger**. Trap 12 was worth more than it appeared.

## 2. FINDING: 78% of reported exposure sits in markets with impossible LTV

Before any modelling, the classification produced nonsense:

```
        coll        borrowUsd         collUsd              LTV
        PAXG    9,078,714,827          260.46   3,485,637,829%
      sdeUSD    6,001,989,178            0.10  6,267,746,086,240%
      wstUSR      191,285,693      660,994.66          28,939%
         msY      121,849,371   16,864,078.14             723%
         RLP       63,136,092      158,427.00          39,852%
         USR       24,324,102      132,564.16          18,349%
```

LTV cannot exceed 100% in a functioning market -- above LLTV the position is
liquidatable. **37 markets report LTV above 100%, and they carry $15.5B of the
$19.9B total reported borrow exposure -- 78.1%.**

`collateralAssetsUsd` is near-zero or unpriced for these markets, most likely
because the collateral asset has no price feed in the indexer. `PAXG` reporting
$9.08bn borrowed against $260.46 of collateral is not a market state; it is a
missing price.

**Consequence: exposure-weighted statistics over the raw population are
meaningless.** Any figure of the form "X% of Morpho USDC exposure" computed from
this source without a validity filter is wrong by a factor of roughly five.

This is the same shape as trap 12 and the emulated clock: a complete-looking
number that is measuring something other than what it claims. It is recorded as
**trap 13**.

## 3. The regime gate -- evaluated on the physically possible subset

Markets with LTV above 100% are excluded as unpriced, not as inconvenient. The
exclusion rule is `LTV > 1.0`, which is a statement about physical possibility
rather than about the result.

```
CLEAN   352 markets   $2,812,215,241 exposure
EXCLUDED 37 markets  $15,506,541,191 (unpriced collateral)

     regime  markets  count %          exposure   exposure %
     LOW-PD      124    35.2%         1,075,287        0.04%
        MID      125    35.5%     2,110,792,816       75.06%
  SATURATED      103    29.3%       700,347,139       24.90%
```

**Pre-registered threshold: MATERIAL = LOW-PD exposure >= 20%.
Measured: 0.04%. NOT MATERIAL.**

**The `MODEL-SPEC.md` section 3 decision to fix sigma is CONFIRMED**, on the
clean subset, by the criterion fixed before the data was seen.

### The count-versus-exposure divergence must be stated

**35.2% of markets by count sit in the LOW-PD regime. They carry 0.04% of
exposure.** The gate is exposure-weighted and therefore passes, but a
count-weighted reading would fail it outright.

That is the correct weighting for this question -- the model is for pricing
lender risk, and a market with no borrowing carries none -- but the write-up
must state both numbers. A reader told only that the gate passed would form a
wrong picture of the book.

## 4. The dominant real market is MID, not saturated

```
   cbBTC/USDC   LTV 46.5%   LLTV 86%   PD 0.5234   MID   $1.42bn
```

The largest genuine market by exposure sits at **LTV 46.5%**, not the 70% used
in Source A. From the day-5 measurement, sigma leverage at LTV 40-50% is
**2.9x to 6.2x**, against **1.33x** at LTV 70%.

**So the actual book is not in the regime where the reduces-to-LGD conclusion is
strongest.** It is in the middle regime, where sigma does materially more work
than at Source A parameters -- though still far less than LGD, which is exactly
proportional at every LTV.

### The reciprocal observation, stated for balance

Source A selects LTV 70%, which is the saturated regime where sigma is damped
and the conclusion becomes parameter-robust in LGD.

Source B derives a near-zero LGD from Steakhouse Prime vaults, which concentrate
in **cbBTC/USDC at LTV 46.5%** -- a lower-LTV, lower-volatility book where the
sigma term does more work than an LGD-only framing credits.

**Both parameter choices sit in regimes that favour their conclusions.** Neither
observation is a claim about intent. Both are statements about what a reader
cannot check without re-executing the model, which is the point of the artifact.

## 5. Open

- The convexity bias is unaddressed: PD is computed at aggregate market LTV, and
  PD is convex in LTV, so this understates PD. Direction known, magnitude not.
- sigma is still the single day-5 reference value, not parameterized by
  collateral class.
- The $2.13 check is not yet run.
