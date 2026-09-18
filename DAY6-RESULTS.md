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


---

## 6. The $2.13 check -- the counter-argument foundation HOLDS

First: the vaults query also truncated at exactly its page cap (200 of 200),
returning 1 Steakhouse vault. Paginated properly: **980 vaults, 55 Steakhouse,
16 USDC-denominated.** Trap 13 again, in a third place.

`Steakhouse Prime USDC` on Base, $20.3m, allocates to six markets:

```
  cbBTC     lltv 86%   $18,660,571     <- 92% of the vault
  cbETH     lltv 77%        735,315
  WETH      lltv 86%        425,726
  cbETH     lltv 86%        262,900
  wstETH    lltv 86%        224,470
  idle                            0
```

Cross-referencing those markets against the committed bad-debt dataset:

```
  bad debt in currently-allocated Prime markets    $0.08
  wider: all Steakhouse USDC vaults, 41 markets    $0.15
  adcv published claim                             $2.13
```

**The substantive claim is confirmed.** Bad debt in the Steakhouse Prime book is
essentially zero -- eight cents against a $20.3m vault, fifteen cents across all
41 markets Steakhouse USDC vaults currently allocate to.

### Why the cent-level figure does not reproduce, and which direction it cuts

The measurement is **$0.08 against a published $2.13** and the gap is explained
by scope, not by error:

- This check uses **current** allocations. The claim covers **since January
  2024**. Markets a vault held historically and has since exited are invisible
  here and would count there.
- This check sums **market-level** bad debt. The claim is **vault-attributed** -
  a vault holding 30% of a market bears 30% of its loss.

Note those two cut in opposite directions. Market-level totals **overstate** any
single vault share, so on that axis alone the measurement should exceed the
claim. It is lower instead, which points to historical allocations rather than
attribution as the explanation.

**Resolving it would require MetaMorpho allocation history over time** -- the
second dataset explicitly scoped out in `MODEL-SPEC.md` section 4. The check is
therefore recorded as **confirming the order of magnitude and the substantive
claim, not reproducing the exact figure**.

### This is the first published figure in this project that checks out

Days 3-6 found published figures diverging from chain state on amount
(gross vs net, 41%), identity (RLP not USR), time (June not March), and
exposure (78% unpriced). **This one holds.** That matters: it is evidence the
method is not producing divergence by construction.

## 7. FOURTH AXIS: are the published figures computed on unfiltered exposure?

78% of reported borrow exposure carries prices that cannot be right, in the API
that essentially every analysis of this protocol runs through -- including both
sides of this dispute.

Any exposure-weighted figure drawn from this source **without a validity filter
is wrong by roughly 5x**. That potentially touches observed depositor rate
aggregates, repaid-debt totals, and any retail-capital-at-risk framing.

**What can be stated, and what cannot.** It cannot be established here whether
either side applied such a filter. What can be stated is that **the filter is
necessary, no published methodology documents applying one, and the correction
is a factor of about five.** That is a claim about what a reader cannot verify,
not an accusation that anyone got it wrong.

## 8. The low-PD tail: markets exist, nobody borrows

35.2% of markets by count sit at low PD carrying 0.04% of exposure. The
explanation is visible in the population: of 3,904 USDC-loan markets, only
**423 hold any collateral** and only **389 have both collateral and borrowing**.

The low-PD tail is overwhelmingly **markets created and never used**, plus
markets with conservative LLTVs that attracted no borrowing demand. Permissionless
market creation makes an empty market free to create.

This supports exposure-weighting as the right basis for the regime gate: a
market with no borrower carries no lender risk. It also means the count-weighted
figure should not be read as describing the active book.
