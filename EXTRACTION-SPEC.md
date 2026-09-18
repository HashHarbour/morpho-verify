# Extraction specification

**Committed before the first query. Any amendment after data exists must be a
separate commit with a stated reason.**

Days 1-2 had a property this phase does not: a digest either matches or it does
not. A dataset looks plausible whether or not it is right, and there is a
hypothesis about what it should show. Committing this document before pulling
anything is what replaces self-checking.

---

## 1. Chains and range

**Both Ethereum mainnet and Base are in scope.** This is a change from the
initial plan and the reason is in `RECONCILIATION.md`: the only event whose
bad debt is published as an exact, primary-sourced figure is on Base. An
Ethereum-only extraction would leave the day-4 gate with no exactly-checkable
target.

| Field | Value |
|---|---|
| Chains | Ethereum mainnet (chainId 1), Base (chainId 8453) |
| Contract | Morpho Blue, per chain |
| Start block | **TO BE PINNED** — Morpho Blue deployment block, per chain |
| End block | **TO BE PINNED** — chosen before first query |
| Query timestamp | recorded per extraction run, UTC |

> **Open item, must be closed before the first query.** Start and end block
> numbers are not written here because they are not known to this document's
> author with confidence, and inventing them would defeat the purpose. Resolve
> from a block explorer, commit the filled values as an amendment, *then*
> extract. A wrong-but-confident block number is worse than a blank.

The query timestamp is recorded because the indexer can be reindexed or
backfilled. Two extractions of the same block range at different wall-clock
times are not guaranteed to agree, and if they disagree that is a finding.

## 2. Market selection

Markets where **loan asset = USDC**, per chain:

- Ethereum USDC: `0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` (6 dp)
- Base USDC: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` (6 dp)

**Never aggregate across LLTVs.** A Morpho Blue market is identified by a
params hash over `(loanToken, collateralToken, oracle, irm, lltv)`. The same
asset pair therefore exists as several distinct markets at different LLTVs.
LLTV is the barrier in the model — collapsing it destroys the quantity being
measured.

Every row carries its full `marketId` and the five params unpacked. Any
aggregation performed downstream must be explicit about which dimensions it
collapses, and must never collapse `lltv`.

Markets with zero activity in range are retained with explicit zeros, not
dropped. A dropped row and a zero row are different facts.

## 3. Events and fields

Source: `Liquidate` events on Morpho Blue.

Fields captured per event: `marketId`, `caller`, `borrower`, `repaidAssets`,
`repaidShares`, `seizedAssets`, `badDebtAssets`, `badDebtShares`,
`blockNumber`, `logIndex`, `transactionHash`, `blockTimestamp`.

Both the assets and shares forms are captured so the conversion is never
inferred. The assets figure is authoritative for reconciliation.

### Market attribution is read, not computed

```solidity
event Liquidate(
    Id indexed id, address indexed caller, address indexed borrower,
    uint256 repaidAssets, uint256 repaidShares, uint256 seizedAssets,
    uint256 badDebtAssets, uint256 badDebtShares
);
event CreateMarket(Id indexed id, MarketParams marketParams);
```

The market `id` is the first parameter of the event. Per-market attribution is
therefore **read off the event, not inferred** — misattributing a liquidation to
the wrong market is structurally impossible, not merely unlikely.

The decomposition risk collapses to a single question: **is the `id` -> LLTV
mapping correct?** That has two independent external checks:

1. **`idToMarketParams(Id)`** — an external view on Morpho Blue returning
   `(loanToken, collateralToken, oracle, irm, lltv)`. Resolve every market id
   against chain state **over an RPC endpoint**, independent of whatever API
   the events were extracted through.
2. **`CreateMarket`** emits the full `MarketParams` at creation, giving a
   second derivation from event data.

Plus one known-answer case: the Aerodrome market's LLTV is stated in its
post-mortem and must match what the getter returns.

**REQUIRED.** Every market id in the dataset is resolved via
`idToMarketParams` over RPC, and the returned params stored alongside. Any id
whose RPC-resolved `lltv` disagrees with the extraction source is a **FAIL**.

> Corrects an earlier claim in `RECONCILIATION.md` that the per-LLTV
> decomposition was "verified by nothing." That was an overstatement made
> before the event shape was checked. It is verifiable, cheaply, against chain
> state — and since LLTV is the barrier in the model, this is the layer that
> most needed a check.

### Semantics check — required before bulk extraction

Two properties are **assumptions, not settled facts**, and must be verified
against the ABI and against real events before anything is extracted in bulk:

1. **Per-event or cumulative.** `badDebtAssets` is believed to be the amount
   realized *by that liquidation*, not a running total.
2. **Assets or shares.** Morpho accounts internally in shares.

**This check must run against TWO markets, and the reason is that one is
useless.** An earlier draft specified the Aerodrome market alone, on the
grounds that its expected value is already known. But that market very likely
carries a single bad-debt event — and on a single event the per-event and
cumulative hypotheses produce **identical output**. The check would have passed
and told us nothing about the property it was designed to test. A test that
cannot distinguish its two hypotheses is not a test.

Required:

| Market | Role |
|---|---|
| Aerodrome cUSDO/USDC, Base (`0x5b347b3d…`) | known expected value; validates magnitude and decimals |
| Any Ethereum USDC market with **≥2 bad-debt liquidations** | discriminates per-event vs cumulative |

The second market must be identified *before* the check, by counting
`Liquidate` events with non-zero `badDebtAssets` per market. If no such market
exists in range, that is itself a finding and must be recorded — it would mean
the discriminating test is unavailable and the assumption stays open.

**Discriminator:** on a market with successive bad-debt liquidations, a
per-event field yields independent amounts; a cumulative field yields a
monotonically non-decreasing sequence where each value contains its
predecessors. Record which was observed.

Realized bad debt reduces the market's `totalSupplyAssets` at the moment of the
liquidation. It is realized on-chain and is not reversed by any off-protocol
compensation. See `RECONCILIATION.md` §3.

## 4. Decimals and numeric storage

**The stored dataset holds raw integer units, exactly as emitted on-chain.**
No division is performed at extraction time.

USDC is 6 dp on both chains. A silent factor of 10^6 is the single most likely
error in this phase, so the dataset never carries a converted number. Any
human-readable figure is produced at presentation time, from raw units, by code
that states the decimal count it applied.

Every amount column is stored as a **decimal string**, never a float and never
a bare JSON number.

**The reason is shares, not assets.** An earlier draft of this spec justified
decimal strings by claiming raw USDC amounts exceed 2^53. That is false at any
realistic size: 2^53 is about 9.007e15, which at 6 dp is roughly **$9 billion
in a single liquidation**. The justification was wrong even though the decision
was right, and a falsifiable reason for a correct decision is worse than none —
it invites a reader to discard the decision along with the argument.

What actually forces decimal strings is Morpho's virtual-shares accounting.
`SharesMathLib` uses `VIRTUAL_SHARES = 1e6` against `VIRTUAL_ASSETS = 1`, a
1:1,000,000 baseline, so share quantities run roughly 1e6 times asset
quantities. A position of raw USDC `A` carries shares on the order of `A * 1e6`,
which crosses 2^53 at:

```
9.007e15 / 1e6 / 1e6  =  ~9,007 USDC
```

**Any position above roughly $9,000 has share values outside float-safe range.**
Since `badDebtShares` and `repaidShares` are captured (§3), and since most
positions of interest are far above $9,000, IEEE-754 would lose precision
silently on the share columns — the exact class of error this project exists to
avoid, arriving through the serializer rather than the arithmetic.

Applied uniformly to asset columns too, so no column's type depends on a
size assumption that could change.

## 5. Canonical ordering

GraphQL pagination does not guarantee stable ordering. Two people extracting an
identical range can produce different bytes, and therefore different hashes,
from identical data.

**Sort key, applied before serialization, ascending:**

```
(blockNumber, logIndex, transactionHash)
```

`blockNumber` and `logIndex` are compared as integers, not strings — string
comparison puts block 100 before block 99. `transactionHash` is the tiebreaker
and should never be needed; if it ever is, that means two events share a block
and log index, which is itself a finding and must be investigated, not sorted
away.

Serialization is newline-delimited, UTF-8, LF endings, no trailing whitespace,
fields in a fixed declared column order. The SHA-256 of that file is the
dataset identity and is committed.

## 6. Edge cases

| Case | Treatment |
|---|---|
| Partial liquidation | Ordinary event. No special handling. `badDebtAssets` is 0 for a healthy partial liquidation. |
| Repeated liquidations, one position | Each event is a separate row. Never deduplicated by borrower. Summing is a downstream decision. |
| Market created mid-range | Included from its creation block. Its absence before creation is not a zero. |
| Market with zero activity | Retained with explicit zeros. |
| Reorged blocks | Extraction is against finalized blocks only. The end block must be final at query time. |
| Events with `badDebtAssets = 0` | Retained. The liquidation happened; the absence of bad debt is data. |

## 7. Scope discipline

**Market-level bad debt only.**

Vault attribution is days 5-7. MetaMorpho vaults allocate across markets, so
attributing market-level loss up to vault-level exposure is a real modelling
step with its own assumptions. It does not belong in the dataset phase, and
letting it in is the most likely way two days become four.

This dataset answers: *how much bad debt was realized, in which market, when.*
It does not answer who bore it.

## 8. What this phase cannot claim

The Cartesi machine has no network. Extraction therefore happens outside it,
and the dataset enters the verified computation as a committed input.

**The dataset is a commitment, not a proof.** Its execution is not verified the
way the model's is. What a re-runner can do is re-extract the same pinned block
range and compare the SHA-256. That is a meaningful check and it is weaker than
the determinism guarantee on the model, and the write-up must say so plainly
rather than let a reader assume the verification covers more than it does.
