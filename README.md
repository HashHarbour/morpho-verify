# morpho-verify

A reproducible re-execution of both sides of a public disagreement about whether
Morpho depositors are compensated for the credit risk they bear.

Everything below can be re-derived from a committed dataset and a machine image
that anyone can rebuild in about twenty minutes.

---

## A published figure that checks out

Starting here on purpose. A reader who meets several divergences before seeing a
single confirmation will reasonably suspect the method manufactures
disagreement.

The counter-argument rests on an empirical claim: across Steakhouse-curated
Prime Morpho vaults, all chains, since January 2024, **two dollars and thirteen
cents** of bad debt.

Measured against the committed dataset:

```
  bad debt across markets Steakhouse Prime currently allocates to   $0.08
  bad debt across all 41 markets Steakhouse USDC vaults allocate to $0.15
  published claim                                                   $2.13
```

**The substantive claim holds.** Bad debt in that book is essentially zero.
The cent-level figure does not reproduce exactly, and the reason is scope rather
than error: this check uses *current* allocations against a since-January-2024
claim, and sums *market-level* rather than vault-attributed bad debt. Resolving
it would need MetaMorpho allocation history, which is out of scope here.

---

## The headline: the two sides are measuring different quantities

The public dispute is conducted as a disagreement about one number, loss given
default. One side uses roughly 5%; the other argues for a few basis points.

Computing both from the realized record, **same formula, two event sets**:

```
  UNCONDITIONAL   across all 27,259 USDC liquidations     0.1829%  =  18.3 bps
  CONDITIONAL     across the 606 that produced bad debt  78.9195%
  RATIO                                                    431.5x
```

**The two definitions differ by 431.5x. The published disagreement spans 12.5x.
The definitional gap is about 34 times the size of the argument.** Only 2.22% of
liquidations produce any bad debt at all, which is roughly where that factor
comes from.

Both sides may be internally correct about different quantities. Neither
publication states which it is using.

**Measured over this window, the realized unconditional loss rate of 18.3 bps
sits at the top of the observed 0 to 20 bps depositor band.** That is a realized
rate, not a forward-looking risk premium. A book can be
paid exactly its realized losses for years and still be underpaid for the risk
it carries, and this measurement cannot distinguish those states, especially
given that one chain carries 99.7% of its bad debt in a single event, so the
distribution has almost no information about its own tail. Whether the
compensation is adequate is not a question this answers.

---

## Reproduce it in twenty minutes

```
  dataset sha256   54e7610b891365ea28d000f7c9521ad7251c2e51b9c194115c548f7230da5028
  machine hash     7ab6f269e574d84588b9175991d5f6d2e0531b46e8103d696e4d0831a7c4ac79
  payload sha256   dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
```

The computation runs inside a Cartesi RISC-V machine, so execution is
deterministic and the image is rebuildable from pinned inputs. Full
instructions, prerequisites and a failure-triage table are in
**[REPRODUCE.md](REPRODUCE.md)**.

**Results wanted either way.** A failed reproduction with good diagnostics is
worth more here than a successful one with none. Apple Silicon results are
especially wanted: a different host architecture reproducing a riscv64 machine
hash is a far harder test than another x86-64 Linux box.

The prediction was registered before anyone ran it, including what a mismatch
would mean, in [DAY10-PREDICTION.md](DAY10-PREDICTION.md).

---

## Other findings

Detail and evidence in **[FINDINGS.md](FINDINGS.md)**. In brief, published
figures and chain state diverge on four independent axes:

- **Amount.** A post-mortem reports 49,303.14 USDC; the on-chain gross figure
  for the same event is 83,787.16. Both correct, one being net of a 34,480.95
  recovery. 41% apart, and neither source says which it is.
- **Identity.** 99.7% of Ethereum USDC bad debt sits in a market collateralized
  by RLP, not the tokens named in incident reporting.
- **Time.** Loss is realized at liquidation, not at impairment. Across the
  exploit month and the three after it, 65 liquidations repaid $1.84M with
  **zero** bad debt; the entire $1.18M then landed in one terminal liquidation
  that repaid nothing, three months later.
- **Exposure.** 78% of reported borrow exposure sits in markets whose stated
  LTV exceeds 100%, which is impossible. Any exposure-weighted figure taken from
  that source without a validity filter is wrong by roughly 5x.

On the model itself:

- One side presents **five model specifications** spanning 45 to over 400 bps,
  a factor of 9 *within one side of the argument*.
- **LTV and volatility together carry 4.06x** between the stated parameters of
  that side and the market that actually holds the exposure, before LGD is
  touched. Both measured.
- Required spread is **linear in LGD**, so at those parameters the quantitative
  dispute reduces to one multiplicative parameter that neither side measures.
- The structural disagreement, whether on-chain lending is a put sale or a
  repurchase agreement, is **settleable by no harness**, and that boundary is
  stated rather than blurred.

---

## Corrections and what is still open

Three errors were caught and corrected during the work, each by a check built so
it could fail. They are recorded in **[CORRECTIONS.md](CORRECTIONS.md)** rather
than quietly amended, including a retracted claim that a data source was at
fault when the defect was mine.

This work was done with AI assistance; the commit history records it. Every
claim here is independently checkable, which is the point -- the specifications
were committed before the work they govern, the failed gates are recorded
alongside the passing ones, and the whole computation reproduces in twenty
minutes on hardware other than mine.

Known-open items are listed at the end of
[WRITEUP-INVENTORY.md](WRITEUP-INVENTORY.md). The most material: denominator
completeness cannot be verified by the method that validated the numerator, one
volatility series is anomalous and not adopted, and vault-level attribution is
out of scope.

---

## Prior art

- `badin-feio/morpho-usdc-yield-research` computes Morpho USDC credit loss from
  the same chains over an overlapping window, via Dune. An independent
  cross-check against it is specified but **not yet run**.
- dirtroads, *The Physics of On-Chain Lending* (DR #68), the undercompensation
  argument.
- adcv.xyz, *Onchain lending is repo (not a put sale)*, the counter-argument and
  the $2.13 claim.

---

## Repository layout

This is a working notebook kept in commit order, because the ordering is itself
evidence: the harness and probe were committed before any data existed.
**[FINDINGS.md](FINDINGS.md)** is the substance and
**[REPRODUCE.md](REPRODUCE.md)** is the check. The `DAY*.md` files are the
record of how each result was arrived at, including the ones that failed.

Specifications were committed before the work they govern:
[EXTRACTION-SPEC.md](EXTRACTION-SPEC.md),
[MODEL-SPEC.md](MODEL-SPEC.md),
[SURFACE-SPEC.md](SURFACE-SPEC.md),
[RECONCILIATION.md](RECONCILIATION.md).
[METHODOLOGY-TRAPS.md](METHODOLOGY-TRAPS.md) catalogues fourteen measurement
traps found along the way. [PROBE.md](PROBE.md) documents the determinism probe
that the whole thing rests on.
