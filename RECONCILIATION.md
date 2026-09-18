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

## 4. Target B — Ethereum, structural

The Resolv/USR exploit of March 2026 is the dominant Ethereum credit-loss
event. **No exact market-level bad-debt figure is pre-registerable**, and this
is stated now rather than discovered later.

Published figures are scenario-dependent, not settled: approximately $5M of
structural wstUSR bad debt *if* RLP absorbs the loss, versus $10-20M of total
lending-market bad debt if it does not, against roughly $180M of liquidations
across 15 vaults. Writing a single number here would invent precision no source
supports.

Pre-registered instead as falsifiable structural claims:

- **B1.** The largest single concentration of `badDebtAssets` across Ethereum
  USDC-loan markets in the pinned range occurs in markets collateralized by
  USR or wstUSR. *Fail if the dominant concentration is elsewhere.*
- **B2.** That concentration is dated within March 2026. *Fail if the dominant
  Ethereum bad-debt cluster falls in a different month.*

## 5. Target C — independent-implementation cross-check

Replaces an earlier order-of-magnitude bound of $1M-$50M. That bound was
nearly vacuous: it would not have discriminated between any two numbers a
correct extraction might plausibly return, and a test that cannot fail against
realistic wrong answers is not a test.

**Prior art:** `badin-feio/morpho-usdc-yield-research`, which computes Morpho
USDC credit loss from Morpho's own data — Dune SQL over liquidation and bad
debt events, with `sql/usdc_liquidations_by_chain.sql` producing the bad-debt
numerator. It covers **Ethereum and Base, April 2024 to September 2026** — the
same two chains this extraction now targets.

**Pre-registered conditions**, per chain:

- **C1.** The **count** of `Liquidate` events with non-zero `badDebtAssets`
  matches exactly. Both derive from the same on-chain events; the event set
  should be identical, and a count mismatch localises the problem immediately.
- **C2.** The **summed** `badDebtAssets` agrees within **0.5%**. Exact
  agreement is the expectation; the band exists only for block-boundary and
  indexer differences. A gap above 0.5% means a methodology difference that
  must be located, not averaged away.

**Compare the numerator, not the headline.** The prior art's published figures
are rates — 7.1 bps/yr Ethereum, 0.7 bps/yr Base — which depend on a borrowing
denominator computed by `scripts/denominator.py`. That denominator methodology
is not being replicated here, so comparing bps would conflate this extraction
with someone else's denominator. The comparison is on the bad-debt numerator in
raw USDC units only.

**Align the range.** The pinned block range (`EXTRACTION-SPEC.md` §1) should be
chosen to match the prior art's April 2024 - September 2026 window, or the
comparison performed over the intersection with the actual window stated. A
range mismatch would surface as a C1 count difference and be misread as an
extraction fault.

**The LLTV mismatch is deliberate and one-directional.** The prior art
aggregates across all USDC markets **by loan-token address**, discarding the
LLTV decomposition that `EXTRACTION-SPEC.md` §2 requires this dataset to
retain. The cross-check is therefore valid **only at the aggregate level**:
this dataset is summed up to the prior art's granularity for comparison, never
the reverse. The per-LLTV decomposition is this project's own and is **not
verified by this target** — no external check on it exists, and the write-up
must not imply otherwise.

**Data paths are genuinely independent — stronger than first stated.** The
prior art queries Dune decoded event tables
(`morpho_blue_multichain.morphoblue_evt_liquidate`,
`...evt_createmarket`). If this extraction runs through Morpho's GraphQL API,
the two paths use **different indexers and different decoding**, with different
failure modes. An earlier draft of this file warned of "overlapping tooling";
that caveat was written before the source was checked and was too pessimistic.

It still is not ground truth — both read the same chain, and a defect in the
chain data or in a shared understanding of the event semantics would pass
through both. Agreement raises confidence substantially; it does not establish
correctness. Citing the prior art is structural, not courtesy.

> **Note:** this independence depends on the extraction path chosen. Pulling
> directly from chain logs via RPC would sit much closer to Dune's own path and
> weaken Target C accordingly. Record which path was used.

**Incidental confirmation from their SQL:** it computes `badDebtAssets / 1e6`
as USD, confirming the field is denominated in raw 6 dp USDC asset units — and
it groups by chain only, confirming the LLTV aggregation noted above.

## 6. What counts as a FAIL

Fixed now, before any number is seen.

1. **A missing event is a FAIL.** If Target A's market yields no rows, that is
   a failure of extraction, never evidence the event did not happen.
2. **An extracted `0` for Target A's market is a FAIL**, not confirmation that
   the loss was covered. See §3.
3. **A rounding difference inside a stated tolerance is not a fail.** Only two
   tolerances exist: Target A's +/- 0.005 USDC presentation band (§2), and
   Target C2's 0.5% cross-implementation band (§5). No others may be invented.
4. **A C1 event-count mismatch is a FAIL** even if C2's summed amount agrees.
   Matching totals over a differing event set means offsetting errors.
5. **Anything else is a FAIL until explained.** An explanation must be written
   down, committed, and must not be of the form "the number is close enough."
6. **A total that matches while an itemized target fails is a FAIL.** Public
   analysis holds that nearly all credit loss on each chain traces to a single
   event. A matching total over a failing itemization means two errors
   cancelling — worse than an obvious miss, because it looks like success.
7. **Any post-hoc amendment to this file is itself a finding** and must be
   committed separately, with the pre-amendment version reachable in history.

### Failure modes this gate deliberately cannot catch

Stated so the write-up does not overclaim:

- **A shared error with the prior art.** Target C compares two implementations
  reading the same chain through partly overlapping tooling. A mistake common
  to both passes silently.
- ~~**The per-LLTV decomposition.**~~ **Withdrawn.** This claimed no external
  check existed. It was wrong, and was written before the event shape was
  checked. The `Liquidate` event carries the market `id` directly, so
  attribution is read rather than computed, and the `id` -> LLTV mapping is
  verifiable against chain state via `idToMarketParams` over RPC. See
  `EXTRACTION-SPEC.md` §3. Targets A and C still operate at or above aggregate
  granularity, but the decomposition is not unverified.
- **Anything outside the pinned range.** The range is a choice, and a
  bad-debt event outside it is invisible rather than absent.

## 7. Recording the result

When extraction completes, append a results section to this file containing:
the measured value for each target, PASS or FAIL against the conditions above
verbatim, the dataset SHA-256, the pinned block range, and the query timestamp.

Any discrepancy is recorded with its explanation, or recorded as unexplained.
"Unexplained" is an acceptable entry. Quietly adjusting a target is not.
