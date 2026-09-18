# Findings: published figures and chain state measure different things

Produced by the day 3-4 reconciliation gate. Every item below was found by a
target written and committed **before** the data existed, then failed against
it. None was the intended output of the phase.

Three independent axes on which published incident figures diverge from
on-chain quantities: **amount**, **identity**, and **time**.

---

## 1. Amount — gross realization vs net of recovery

The Aerodrome cUSDO/USDC oracle manipulation, Base, 2025-05-25.

| Source | Figure |
|---|---|
| Post-mortem headline | 49,303.14 USDC |
| On-chain, attack's two liquidations | 83,787.159294 USDC |
| Market lifetime `badDebtAssets` | 98,738.726499 USDC |

The post-mortem's own arithmetic resolves it:

> "The total loss for the lenders thereby sums up to ...
> (11,541.64 + 72,242.78 − 34,480.95)"

**The published figure is net of a 34,480.95 USDC recovery. `badDebtAssets` is
gross.** Comparing gross to gross, chain and post-mortem agree to **0.0033%**.

A reader comparing the headline to chain data sees a **41% discrepancy** on the
same event, with no error anywhere. Both numbers are correct; they measure
different quantities, and neither source says which.

## 2. Identity — the named asset is not the collateral

Pre-registered: the dominant Ethereum concentration sits in markets
collateralized by **USR or wstUSR**, the tokens named in public reporting of the
Resolv exploit.

Measured: **99.7%** of Ethereum USDC bad debt sits in a market collateralized by
**RLP** (Resolv Liquidity Pool). wstUSR markets appear at trivial size.

Right protocol family, wrong instrument. Analysis filtered on the token names
that appear in incident reporting would miss essentially all of the loss.

## 3. Time — impairment vs realization

**The most consequential, and the one that is demonstrated rather than
inferred.**

Pre-registered: the dominant Ethereum concentration is dated **March 2026**, when
the Resolv exploit is publicly dated.

Measured: **2026-06-06 15:05 UTC**, block 25259134,
tx `0x267a017b5f011558223af8aee98cdaf4b6e2418ab204b0a12b8fc892eeec150f`.
**100% of Ethereum USDC bad debt falls in June 2026. March carries none.**

The full liquidation history of that market
(`0xe1b65304edd8ceaea9b629df4c3c926a37d1216e27900505c04f14b2ed279f33`,
RLP collateral, 86% LLTV) shows the mechanism:

```
month      liqs      repaid USDC     badDebt USDC
2025-05       1             4.30             0.00
2026-02      15        57,831.16             0.00
2026-03       1          4,001.50            0.00     <- exploit month
2026-04      43        103,094.30            0.00
2026-05       5      1,674,702.22            0.00
2026-06       1              0.00    1,181,253.93     <- terminal event
```

**Bad debt is realized at liquidation, not at impairment.** Through the exploit
month and the three months after, 65 liquidations repaid **$1.84M with zero bad
debt** — liquidators seizing collateral while it still covered the debt. The
entire loss then lands in a **single terminal liquidation that repaid nothing**,
three months after the exploit that caused it.

This is not an indexing artifact. It is how the protocol works: loss is
recognised when a position is liquidated with insufficient collateral, and
nothing forces that to happen when the collateral becomes impaired.

### Why it matters beyond this dataset

Any analysis computing **loss rates over time windows** — which is what an LGD
parameter dispute runs on — keyed to **incident dates** will place losses in the
wrong period. Here it would attribute $1.18M to March 2026, a month whose
on-chain bad debt is **zero**.

Monthly, quarterly and annualised loss rates are all affected, and the
distortion is largest exactly where it matters: around the tail events that
dominate the series.

---

## Consequence for the model: concentration is granularity-dependent

```
                 single event      single market
ETHEREUM            99.7%             99.7%
BASE                64.6%             88.2%
```

The Aerodrome attack is **73%** of its own market's lifetime bad debt; that
market is **88.2%** of Base; the largest single Base event is **64.6%**.

"Almost all credit loss traces to a single event" is **true for Ethereum** and
**qualified for Base**, and concentration weakens monotonically as granularity
sharpens: chain → market → event.

**Design consequence, recorded before the surface is built:** the tail-treatment
axis cannot assume single-event dominance. It must be **parameterized by
granularity**, with chain-, market- and event-level treatments as distinct
points rather than one assumed regime. A surface built on the Ethereum figure
alone would encode 99.7% concentration as though it were general; Base shows it
is not.

---

## Scope and limits

- Dataset: `dataset-baddebt-usdc.tsv`, SHA-256
  `54e7610b891365ea28d000f7c9521ad7251c2e51b9c194115c548f7230da5028`,
  611 USDC-loan bad-debt events, Ethereum and Base.
- The temporal mechanism is demonstrated for **one market**. It is consistent
  with how Morpho realizes bad debt generally, but generalisation across markets
  is not established here.
- Target C (cross-check against independent prior-art implementation) is
  **unevaluated**, not passed. It needs that project's Dune queries run.
- Range is indexer-defined; see `EXTRACTION-SPEC.md`.
