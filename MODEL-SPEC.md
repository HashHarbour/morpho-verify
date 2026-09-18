# Model specification

**Committed before implementation.** Same discipline as `EXTRACTION-SPEC.md`
and the same reason: deciding parameters after seeing results is how a surface
gets tuned to a conclusion.

Day 5 builds the model and proves the implementation is correct against answers
that already exist. **It does not touch the dataset.** Applying it to real
markets is day 6. Keeping these apart is what lets a day-5 failure mean "the
code is wrong" rather than "something is wrong somewhere."

---

## 1. The mapping, an assumption rather than a derivation

Black-Cox is a first-passage structural credit model. Mapped onto a Morpho
lending position:

| Black-Cox | Morpho |
|---|---|
| Firm asset value V | Collateral value, diffusing |
| Debt / bond | The USDC debt D owed by the borrower |
| Default barrier | The LLTV liquidation threshold |
| Bondholder | The lender (depositor) |

The depositor position is **a risk-free bond plus a short put**: interest and
principal are received unless the barrier is breached, in which case loss is
absorbed.

**This mapping is the first thing a critic should attack, and it is stated here
so the attack has a clear target.** It assumes the barrier is absorbing
(liquidation at first touch), that collateral follows geometric Brownian
motion, and that liquidation is frictionless apart from the LGD term. Real
liquidation is discrete, gas-constrained, and, as days 3-4 showed, can lag
impairment by months. See section 6.

## 2. Inputs

| Input | Symbol | Status | Source |
|---|---|---|---|
| Initial collateral value | V0 | **measured** | normalised to LTV; on-chain per market on day 6 |
| Debt | D | **measured** | on-chain per market on day 6 |
| Barrier | B | **measured** | LLTV, exact from `idToMarketParams` |
| Volatility | sigma | **assumed, fixed** | see section 3 |
| Risk-free rate | r | **assumed** | stated constant, sensitivity reported |
| Horizon | T | **assumed** | stated constant, sensitivity reported |
| Loss given default | LGD | **FREE AXIS** | the locus of the dispute |
| Tail-treatment granularity | -- | **FREE AXIS** | chain / market / event, from `FINDINGS.md` |

## 3. Decision: sigma is FIXED, not a third axis

**The problem.** The dataset holds liquidations and bad debt, not price series.
There is no measured volatility in it. sigma must therefore be sourced
externally or treated as free.

**Two axes are already committed**: LGD (the dispute itself) and tail-treatment
granularity (the days 3-4 finding). A third makes the surface unreadable.

**Decision: sigma is fixed at stated values, with sensitivity reported
separately as a 1-D sweep.** It is not a surface axis.

Rationale, recorded now:
- **LGD cannot give way.** It is where the disagreement lives and the whole
  point of the exercise.
- **Granularity cannot give way.** It is a novel finding from days 3-4, and the
  evidence says concentration is granularity-dependent rather than uniform.
- **sigma is a nuisance parameter here.** Neither published argument is framed
  in terms of it. Fixing it and reporting sensitivity separately is honest and
  keeps the surface two-dimensional.

**Consequence to state plainly:** results are conditional on the stated sigma.
If the two sides assumed materially different volatilities, then part of the
disagreement lives there and not in LGD, and the sensitivity sweep is what
would reveal it. That possibility is not assumed away; it is measured on one
axis rather than three.

## 4. Decision: MARKET level, not vault level

The dispute concerns **vault depositors**. This dataset is **market level**.

Full vault attribution requires MetaMorpho allocation history over time: a
second dataset with its own extraction spec, reconciliation and failure modes.
**It is the largest remaining threat to the fourteen days.**

**Decision: stay at market level.** Vault-level results are a weighted
combination of market-level ones, computable by a reader given allocations.

This is a scoping choice, not a claim that vault level does not matter. It is
recorded on day 5 rather than discovered on day 7, and the write-up must state
that the surface answers a market-level question while the dispute was posed at
vault level.

## 5. Numerical requirements carried from days 1-2

**Normal CDF.** `0.5 * erfc(-x / sqrt(2))`, never `0.5 * (1 + erf(x / sqrt(2)))`.
Non-negotiable, and it matters more here than in the probe: default probability
for well-collateralized markets sits deep in the left tail, exactly where the
naive form has already discarded its significant digits.

**The erf family is the divergent region.** The day-2 gate found native-vs-riscv64
divergence of exactly 1 ULP on 5 of 834 records, **all in `B.erfc` and
`B.ncdf`**. Sections A (exp/log/sqrt chains), C (all summation orderings) and E
(matrix reduction) were bit-identical.

**This model lives entirely inside the divergent region.** That is bounded and
acceptable, and stated here rather than discovered on day 10. The
machine-to-machine claim is unaffected; only native-vs-machine comparison is.

**Closed form only in the production workload.** Monte Carlo at 78,000
evaluations by 10,000 paths is infeasible under emulation. Drift back toward
simulation is the specific failure mode to watch today.

**Native Monte Carlo for validation is encouraged.** A small MC run, natively,
once, to cross-check the closed form. It never enters the machine. The day-1
guard is about the production workload, not about how the closed form is
verified.

## 6. Reuse the probe machinery

- `float.hex()` serialization; no rounded decimals.
- Same hygiene variables; same delimiter-based payload extraction.
- **One invocation producing the whole surface.** The 164M-cycle boot is cheap,
  but paying it once is still correct, and one digest covering one complete
  experiment is cleaner for a re-runner than twenty partial ones.

## 7. Exit criteria

1. This file committed **before** the implementation.
2. **Both published figures reproduced from their stated parameters.** Run this
   first. It is the only day-5 test that can actually fail.
3. Degenerate cases: barrier to 0 gives PD to 0; sigma to 0 gives the
   deterministic outcome; T to 0 gives PD to 0.
4. Native Monte Carlo agrees with the closed form within its own sampling error.
5. The vault-versus-market scope decision recorded in writing. (Section 4, done.)

## 8. Open before the acceptance test can run

**The full parameter sets are not yet in hand.** Known targets are output and
input pairs only:

- Undercompensation of **5-10x** at a stated **LGD around 5%**.
- Counter-argument: **LGD of a few basis points** brings output in line with
  observed **3-30 bps**.

Reproducing either requires the complete set, V0/D or LTV, sigma, r, T, as each
side stated them. **These must be sourced from the published arguments before
the acceptance test is meaningful, and must not be inferred backwards from the
target outputs.** Fitting parameters until the published answer appears would
invert the test: it would prove only that the model has enough freedom to hit
any number.

If a side did not state a parameter, that is itself a finding and is recorded
as such. An argument whose inputs cannot be fully reconstructed is an argument
that cannot be independently checked.
