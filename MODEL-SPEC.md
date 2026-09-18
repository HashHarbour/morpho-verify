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

## 8. Parameters, sourced from primary sources (resolved)

Taken from the primary publications, not from secondary coverage. Secondary
coverage is what produced three failed targets on days 3-4.

### Source A: dirtroads DR #68, "The Physics of On-Chain Lending"

**Five distinct model specifications, not one.** Reproducing "the" headline
requires naming which.

| # | Specification | Output |
|---|---|---|
| 1 | Passive borrower, no rebalancing | PD 70-80%, spread > 400 bps |
| 2 | Continuous rebalancing, infinite capital | 45 bps, described as irreducible floor |
| 3 | Limited rebalancing, 20% extra capital | 350 bps (via Monte Carlo) |
| 4 | Limited rebalancing, 100% extra capital | 130 bps |
| 5 | Discrete daily rebalancing | 250-400 bps |

Shared parameters (Scenario 1, carried through):

```
collateral       ETH
LTV              70%
LLTV             86%
sigma            75%
r                4.25%
T                1 year
LGD              5%          "approximated by the liquidation incentive"
lambda           1.5 / year  jump intensity
mean jump        -8.3%
```

**Two structural points the day-5 spec did not anticipate:**

1. **Scenario 1 is jump-diffusion, not pure Black-Cox.** Section 1 of this spec
   assumes geometric Brownian motion. That covers Scenario 2 at best. Any claim
   to reproduce Scenario 1 requires the jump component (lambda, mean jump size).
2. **Scenarios 3 and 4 were produced by Monte Carlo.** Reproducing them requires
   MC natively. This does not breach the day-1 guard, which is about the
   production workload inside the machine, but it does mean two of the five
   targets are not closed-form reproducible by construction.

### Source B: adcv.xyz, "Onchain lending is repo (not a put sale)"

```
LLTV                     86%
collateral at barrier    1 / 0.86 = 1.163x debt
after liquidator cut     1.105x debt
buffer                   14 percentage points, LLTV to insolvency
proposed LGD             0.3-0.5%   (vs 5%)
output with that LGD     3-30 bps, "in line with observed rates"
```

Empirical claim, directly checkable against the day-3/4 dataset:

> Across all Steakhouse-curated Prime Morpho vaults, on all chains, across all
> LTVs, since January 2024: **19,228 liquidation events. Half a billion dollars
> in repaid debt. Two dollars and thirteen cents of bad debt.**

## 9. The acceptance test was mis-specified. The disagreement has two layers.

The day-5 plan assumed both sides run the same model with different LGD, so
reproducing both would locate the entire disagreement in parameters. **That is
wrong**, and the reason is itself a finding.

Source B does not accept the mapping in section 1 of this spec. It argues
on-chain lending is structurally a **repurchase agreement**, that what repo
lenders price is **gap risk**, and that the Merton decomposition, while
mathematically valid, is "somewhat unfalsifiable" because it "ignores the margin
call mechanism that truncates the exposure continuously":

> "By this logic, every repo lender on Wall Street is selling puts on
> Treasuries and every mortgage lender is selling puts on housing."

That is a rejection of the model mapping, not a parameter choice.

**Restructured test.** Decompose the gap:

- **Parametric layer.** Same model, LGD 5% versus 0.3-0.5%. **Settleable by
  this harness.** Report how much of the spread gap closes on LGD alone.
- **Structural layer.** Put-sale versus repo. **Not settleable by any harness.**
  No verifiable computation adjudicates whether a CDP is a short put or a repo.
  Report what survives at **any** parameterization.

This is a sharper result than "both sides reproduced," and it is honest about
what verifiable computation can and cannot settle. Report both numbers.

## 10. An arithmetic discrepancy in the headline, recorded not resolved

Source A states observed depositor rates of **0-20 bps** against a required
**250-400 bps**, and characterises the gap as **5-10x**.

That pair does not yield 5-10x:

```
250 / 20 = 12.5x        400 / 20 = 20x        250 / 0 = undefined
```

A 5-10x multiple against 250-400 bps implies an observed rate near **40 bps**,
not 0-20 bps. Either the multiple is computed against a different observed
figure, or against a different specification of the five.

**Recorded as a discrepancy, not resolved, and not assumed away.** Before any
claim to have reproduced the headline, the specification and observed rate that
actually produce 5-10x must be identified. Same discipline as Target A on day 3:
the published figure and the arithmetic behind it are different quantities until
shown otherwise.

## 11. Fallback if a parameter is undisclosed

Do **not** infer a missing parameter backwards from the target output. Instead
**map the region of parameter space consistent with the published result**.

That characterises a preimage rather than fitting a point, stays honest whether
or not disclosure is complete, and produces a stronger statement: not "their
number is reproducible" but "their number is consistent with this region and no
other."


---

# AMENDMENT (day 5, after the sigma sweep): the section 3 decision is regime-conditional

Section 3 fixed sigma rather than making it a third axis. **That decision is
valid only in the high-LTV saturated regime, and the day-6 markets will not all
be in it.**

Measured leverage of sigma across LTV (LLTV 86%, r 4.25%, T 1 year):

```
   LTV    PD @ sigma 40%   PD @ sigma 75%   ratio      regime
   20%          0.000373         0.092671  248.67x     LOW-PD
   30%          0.010798         0.242645   22.47x     LOW-PD
   40%          0.066386         0.414173    6.24x     mid
   50%          0.198355         0.578682    2.92x     mid
   60%          0.399661         0.724019    1.81x     mid
   70%          0.635889         0.846976    1.33x     saturated
   80%          0.870656         0.948439    1.09x     saturated
```

**At LTV 70%, sigma moves PD by 1.33x. At LTV 30%, by 22.5x. At LTV 20%, by
249x.**

LGD contributes exactly proportionally at every LTV -- it is a multiplier on the
outcome, not an input to the diffusion. sigma contributes almost nothing in the
saturated regime and **dominates LGD outright** below roughly LTV 50%.

## Consequence 1: the reduces-to-one-parameter claim is conditional

The day-5 result -- that the quantitative dispute reduces analytically to a
single multiplicative parameter -- **holds at LTV 70%, which is the LTV Source A
chose.** It does not hold generally.

At typical lower LTVs, sigma carries more leverage than LGD, and a disagreement
about volatility would matter more than a disagreement about loss given default.
Any statement of the day-5 conclusion must carry the LTV condition with it.

**This is not a claim that the LTV was chosen to produce that property.** It is
a statement that the property is a consequence of the choice, and that readers
of either argument cannot tell the difference without running the model.

## Consequence 2: day 6 must check regime per market, before anything else

**Required day-6 gate, added here:** for every market in
`dataset-baddebt-usdc.tsv`, compute PD at the market LTV and classify the
regime. Then:

- **Saturated markets (PD > ~0.75):** the two-axis surface stands. sigma stays
  fixed with sensitivity reported separately.
- **Low-PD markets (PD < ~0.25):** sigma dominates. The decomposition needs a
  **second row**, and the surface design in section 3 does not survive contact
  with these markets.

If a material share of markets falls in the low-PD regime, the section 3
decision must be revisited **before** the surface is built, not after.

## Consequence 3: guard on the combined figure

The combination sigma 40% with LGD 0.3% giving **19.08 bps**, inside the
observed 0-20 bps band, is the most attackable result in the project. It is
recorded with the following constraints, which must travel with it everywhere:

- Those values were **selected as defensible, not derived.** Nothing in this
  work measures either of them.
- **The same model at sigma 75% and LGD 5% gives 423.5 bps.** Both figures come
  from one implementation and one set of equations.
- **Nothing here establishes which parameter set is correct.**
- The claim is that **the observed band is reachable under defensible inputs**.
  It is **not** that observed rates are justified, adequate, or correct.

The distinction matters because the moment this reads as advocacy, the work
stops being a referee and becomes a participant. The scope lock in section 4
exists for the same reason.
