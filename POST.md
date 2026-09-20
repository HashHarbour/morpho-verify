# Two people disagreed by 12.5×. Both were right.

In 2026, two careful analyses of Morpho reached opposite conclusions about whether depositors are paid enough for the credit risk they carry.

One, working from a Black-Cox structural credit model, concluded depositors are undercompensated — required spreads of 250–400 basis points against observed rates near zero. The other argued the model's loss-given-default parameter was set roughly an order of magnitude too high, and that correcting it brings the model into line with what depositors actually receive.

The disagreement was framed as being about one number. I re-executed both arguments from chain data to find out where it actually lives.

It isn't in the number. It's in what the number measures.

## First, a figure that checks out

The counter-argument rests on an empirical claim, stated to the cent: across Steakhouse-curated Prime Morpho vaults, all chains, since January 2024 — **two dollars and thirteen cents** of bad debt.

Measured against my extraction:

```
bad debt in markets Steakhouse Prime currently allocates to    $0.08
bad debt across all 41 markets Steakhouse USDC vaults hold     $0.15
published claim                                                $2.13
```

The substantive claim holds. Bad debt in that book is essentially zero.

The cent-level figure doesn't reproduce exactly, and the reason is scope rather than error: I used *current* allocations against a since-January-2024 claim, and summed *market-level* rather than vault-attributed bad debt. Resolving that needs MetaMorpho allocation history, which I didn't extract.

I'm leading with this deliberately. Everything below is a divergence between published figures and chain state, and a reader who meets five of those before seeing a single confirmation would reasonably suspect the method manufactures disagreement. It doesn't. When a figure is right, it comes out right.

## The disagreement is definitional

Loss given default is the parameter both sides argue about. One uses roughly 5%; the other argues for a few basis points.

So I computed it from the realized record — same formula, two event sets:

```
UNCONDITIONAL   across all 27,259 USDC liquidations      0.1829%  =  18.3 bps
CONDITIONAL     across the 606 that produced bad debt   78.9195%
                                                         ratio     431.5×
```

**The two definitions differ by 431.5×. The published disagreement spans 12.5×.** The definitional gap is about thirty-four times the size of the argument.

The reason is in the middle row: only **2.22%** of liquidations produce any bad debt at all. Loss *given default* — conditional on a liquidation having gone bad — is severe, tens of percent. Loss across *all* liquidation flow, including the overwhelming majority that recover fully, is single-digit basis points. Same underlying events, two legitimate questions, answers two orders of magnitude apart.

Both sides may be internally correct about different quantities. Neither publication states which it is using, and I don't think either author would disagree that they're different measurements — it's simply that nothing in the exchange required anyone to say so.

One more figure, with its limits attached. **The measured unconditional loss rate of 18.3 bps sits at the top of the observed 0–20 bps depositor band.** That is a *backward-looking realized rate over the measured window*, not a forward-looking risk premium. A book can be paid exactly its realized losses for years and still be underpaid for the risk it carries, and this measurement cannot distinguish those two states. One chain carries 99.7% of its bad debt in a single event, so the distribution has almost no information about its own tail. Whether the compensation is adequate is not a question this answers, and I want to be clear that I'm not claiming it does.

## Published figures and chain state diverge on four axes

Reconciling my extraction against the public record was supposed to be a validation step. It produced most of the findings instead.

**Amount.** A post-mortem reports 49,303.14 USDC of bad debt for a specific oracle-manipulation event. The on-chain gross figure for the same event is 83,787.16. Both are correct — the published number is net of a 34,480.95 recovery. They're 41% apart, and neither source says which quantity it is. My reconciliation target failed against chain data purely because I'd registered a net figure as though it were a gross one.

**Identity.** 99.7% of Ethereum USDC bad debt sits in a market collateralized by RLP — not the tokens named in incident reporting for the same protocol. An analysis filtered on the names that appear in the coverage would miss essentially all of the loss.

**Time.** Bad debt is realized when a position is liquidated, not when its collateral becomes impaired. Across the exploit month and the three months following, 65 liquidations repaid **$1.84M with zero bad debt** — liquidators seizing collateral while it still covered the debt. The entire $1.18M then landed in a single terminal liquidation that repaid nothing, three months after the event that caused it. Any loss rate computed over calendar windows keyed to incident dates puts the loss in the wrong period.

**Exposure.** This is the one that made me stop and re-check my own code:

```
PAXG market     $9,078,714,827 borrowed    against $260.46 collateral
sdeUSD market   $6,001,989,178 borrowed    against   $0.10 collateral
```

Loan-to-value above 100% is impossible in a functioning market — above the liquidation threshold the position is liquidatable by construction. 37 markets report it, and they carry **78% of total reported borrow exposure**. The collateral is simply unpriced in the API. Any exposure-weighted figure drawn from that source without a validity filter is wrong by roughly 5×.

I can't establish whether any published analysis applied such a filter. What I can say is that one is necessary, no methodology I've read documents applying one, and the correction is a factor of five.

## The data source has its own behaviour

The extraction runs against a public GraphQL API. Three separate endpoints return a full page and stop: a market query returned exactly 1,000 of 3,904; a vault query returned exactly 200 of 980; position queries cap at 10,000 rows regardless. Nothing in the response says the result is partial.

That nearly cost me the headline. My first attempt at the denominator ran cleanly — monthly chunks, short final pages, no errors — and produced 7,447 liquidations. It was missing 377 of 611 known bad-debt events, including the largest. A naive loss rate from that data gives **5.9 bps**, which lands squarely inside one side's stated range and is wrong, because the numerator was missing 92% of its mass.

I caught it only because I held a second, independently-filtered extraction of exactly the events that went missing. There is no equivalent second filter for the liquidations that *didn't* produce bad debt, so I can verify the numerator and not the denominator. That asymmetry is in the repo, stated as a limitation rather than smoothed over.

I initially attributed the omission to the API. That was wrong — it was my pagination loop breaking on a short page. The retraction is in the commit history.

## What I got wrong, and what it means

The most useful error in this project wasn't a number.

I built the verified computation in one directory and kept the repository in another. Every check I ran for nine days — the determinism gate, the cold rebuild, the run that produced the published digests — executed against my working directory. The repository was where results got written, never a thing that was exercised.

The Dockerfile that builds the machine was never committed. Someone looking at the repo found it in about a minute. A stranger following my own reproduction instructions wouldn't have gotten a wrong answer; they'd have hit a build error on the first step.

Every check had passed. Every check was testing local state rather than the claim.

That generalises well past this project: **a test run from inside working state cannot distinguish a reproducible artifact from a directory that merely happens to work.** The fix was a clean-room run — fresh clone, published instructions followed exactly — which now passes. It should have been running since day two.

An artifact arguing that published figures ought to be independently checkable is worth more when its author shows what happened the one time theirs was checked. Six other corrections are logged in the repo, including a payload header that misstated the resample count of the artifact it headed — the same class of error I'm documenting in other people's work, in my own serializer.

## On the model itself

Two observations, and I want to be careful how I put them.

The undercompensation analysis presents **five model specifications**, spanning 45 bps to over 400 bps — a factor of nine *within one side of the argument*. The public exchange proceeded as though a single number were on the table.

And parameter choices matter more than the disputed one. At the stated parameters (70% LTV, 75% volatility), the model's sensitivity to volatility is almost entirely damped out — default probability is already near certainty, so volatility can't move it much, and the result reduces cleanly to the disputed LGD term. At the parameters of the market that actually carries the exposure — 46.9% LTV measured across 10,100 positions, 44.8% realized volatility measured from a year of daily closes — **LTV and volatility together account for 4.06× before LGD is touched at all.**

Meanwhile the near-zero LGD from the other side is derived from a book concentrated in exactly that mid-range market, where volatility does more work than an LGD-only framing credits.

I'm not suggesting either choice was made to produce a result. I have no basis for that and don't believe it. The point is narrower and, I think, more interesting: **each argument's parameters sit in a regime where that argument's conclusion is robust, and a reader cannot tell that from either piece without re-running the model.** That's a property of the dispute, not of the participants.

The deeper disagreement — whether on-chain lending is a put sale or a repurchase agreement — isn't a parameter, and no amount of computation settles it. I've stated that boundary rather than blurred it.

## Check it yourself in twenty minutes

The computation runs inside a Cartesi RISC-V machine, which is the mechanism rather than the point: it makes execution deterministic and the image rebuildable from pinned inputs, so the result is a hash rather than a claim.

```
dataset sha256   54e7610b891365ea28d000f7c9521ad7251c2e51b9c194115c548f7230da5028
machine hash     7ab6f269e574d84588b9175991d5f6d2e0531b46e8103d696e4d0831a7c4ac79
payload sha256   dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
```

Fresh clone, one build, one run, about twenty minutes. Instructions and a failure-triage table are in the repo.

**What I have not established: host independence.** The clean-room ran on my own machine — same Docker, same architecture. Whether the build reproduces on different hardware is untested, and an Apple Silicon result would be the single most useful thing anyone could contribute. A failed reproduction with good diagnostics is worth more to me than a successful one without.

Every specification in that repo was committed before the work it governs, including the reconciliation targets — three of which failed, which is how the definitional finding surfaced at all. The failures are in the history alongside the passes.

This work was done with AI assistance; the commit history records it. Every claim is independently checkable, which is rather the point.

---

*Repository: [morpho-verify](https://github.com/HashHarbour/morpho-verify). Prior art: the undercompensation analysis in dirtroads DR #68, the counter-argument at adcv.xyz, and `badin-feio/morpho-usdc-yield-research`, which computes credit loss over an overlapping window via Dune — an independent cross-check against it is specified but not yet run.*
