# Reconciliation — pre-registered

**Committed before the first query, while there is no stake in the outcome.**

A reconciliation that can only confirm what you expect is the same mistake as a
harness that always prints MATCH. The conditions below, including what counts
as a failure, are fixed before any number exists.

---

## 1. Why both chains

The natural scope was Ethereum mainnet alone. That was changed, and the reason
is recorded here rather than in a later commit message:

**The only credit-loss event with an exact, primary-sourced bad-debt figure is
on Base.** An Ethereum-only extraction would have left this gate with no
exactly-checkable target — only a total that cannot be independently verified,
which is the condition under which two cancelling errors go unnoticed.

## 2. Target A — Base, exact match

Primary source: Morpho governance forum post-mortem, *Aerodrome cUSDO/USDC AMM
LP Oracle Manipulation on Morpho Lending Market*.

| Field | Value |
|---|---|
| Chain | Base (8453) |
| Market ID | `0x5b347b3dcfed096f09040cd30a174ae354ecc0a35c996493b8fa490d6d3e79d7` |
| Published bad debt | **49,303.14 USDC** |
| Event time | 2025-05-25 23:29 UTC |

**PASS:** the sum of `badDebtAssets` for that market ID, over the pinned range,
rounds to `49303.14` USDC — i.e. lies within `49303135000` and `49303145000`
raw 6dp units inclusive.

**Tolerance rationale, fixed in advance:** the published figure is presented at
2 dp. The on-chain value may carry up to 6 dp. The tolerance is exactly the
width of that presentation rounding (+/- 0.005 USDC) and nothing wider. It is
*not* a fudge factor for decimal-handling mistakes — a 10^6 error is 9 orders of
magnitude outside this band and fails loudly, which is the intent.

## 3. The realized-vs-residual distinction

**The target is bad debt realized on-chain, not economic loss remaining after
compensation.** These are different quantities and conflating them produces a
false failure.

For this event the shortfall *was* realized as `badDebtAssets`, reducing the
market's `totalSupplyAssets`. The curator then compensated depositors of the
Clearstar OpenEden USDC Vault by a **separate transfer**
(`0x9a75859269b437c633e3958b8d6af04942dc53d087f212fa5499edd27bcea02e`), which
did not reverse the on-chain realization.

Public summaries stating "no bad debt remains" are economically correct and
refer to the post-compensation position. A correct extraction returns
49,303.14 against those summaries' implied zero.

**Therefore:** an extracted value of 0 for this market is a **FAIL**, not a
confirmation that the loss was covered.

## 4. Target B — Ethereum, structural (no exact match available)

The Resolv/USR exploit of March 2026 is the dominant Ethereum credit-loss
event. **No exact market-level bad-debt figure is pre-registerable**, and this
is stated now rather than discovered later.

Published figures are scenario-dependent, not settled: approximately $5M of
structural wstUSR bad debt *if* RLP absorbs the loss, versus $10-20M of total
lending-market bad debt if it does not, against roughly $180M of liquidations
across 15 vaults. Writing a single number here would be inventing precision no
source supports.

Pre-registered instead, as falsifiable structural claims:

- **B1.** The largest single concentration of `badDebtAssets` across Ethereum
  USDC-loan markets in the pinned range occurs in markets collateralized by
  USR or wstUSR. *Fail if the dominant concentration is elsewhere.*
- **B2.** That concentration is dated within March 2026. *Fail if the dominant
  Ethereum bad-debt cluster falls in a different month.*
- **B3.** Total Ethereum USDC-loan `badDebtAssets` in range lies between
  **$1M and $50M**. This is a deliberately loose order-of-magnitude bound; it
  cannot confirm the figure, only catch a decimal or unit catastrophe. *Fail
  outside.*

B3 is weak on purpose. A bound presented as a precise test would be worse than
an honest loose one.

## 5. What counts as a FAIL

Fixed now, before any number is seen:

1. **A missing event is a FAIL.** If Target A's market yields no rows, that is
   a failure of extraction, never evidence the event did not happen.
2. **A rounding difference inside the stated tolerance is not a fail.** Only
   the +/- 0.005 USDC band of §2 qualifies. No other tolerance exists.
3. **Anything else is a FAIL until explained.** An explanation must be written
   down, committed, and must not be of the form "the number is close enough."
4. **A total that matches while an itemized target fails is a FAIL.** Public
   analysis holds that nearly all credit loss on each chain traces to a single
   event. A matching total over a failing itemization means two errors
   cancelling, which is worse than an obvious miss because it looks like
   success.
5. **Any post-hoc amendment to this file is itself a finding** and must be
   committed separately, with the pre-amendment version reachable in history.

## 6. Recording the result

When extraction completes, append a results section to this file containing:
the measured value for each target, PASS or FAIL against the conditions above
verbatim, the dataset SHA-256, the pinned block range, and the query timestamp.

Any discrepancy is recorded with its explanation, or recorded as unexplained.
"Unexplained" is an acceptable entry. Quietly adjusting a target is not.
