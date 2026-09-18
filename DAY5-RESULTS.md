# Day 5 results: model implementation and validation

Native only. The model has not entered the machine; that is day 6.

## Implementation

`blackcox.py`. Closed-form first-passage probability under geometric Brownian
motion with an absorbing barrier at LLTV. Pure stdlib. Normal CDF computed as
`0.5*erfc(-x/sqrt(2))` throughout, per MODEL-SPEC.md section 5.

## Baseline against Source A shared parameters

```
LTV 70%   LLTV 86%   sigma 75%   r 4.25%   T 1 year   LGD 5%
b = log(0.86/0.70) = 0.205852
PD  = 0.846976   (84.70%)     hex 0x1.b1a6d09bec742p-1
required spread @ LGD 5% = 423.5 bps
```

Source A Scenario 1 states PD 70-80% and required spread "> 400 bps".
**The spread reproduces.** The PD sits above the stated band; Scenario 1 also
carries a jump component (lambda 1.5/yr, mean jump -8.3%) outside this GBM
mapping, so the two PD figures are not strictly comparable.

## Exit criterion 3 -- degenerate cases: PASS

```
ltv -> 0   (barrier infinitely far)   PD = 7.1e-162   PASS
sigma -> 0 (deterministic, r > 0)     PD = 0.0        PASS
T -> 0                                PD = 0.0        PASS
ltv > lltv (already breached)         PD = 1.0        PASS
```

## Exit criterion 4 -- Monte Carlo cross-check: NOT MET as written

```
closed form (continuous)              0.846976

  steps          MC     1 s.e.      gap    gap / sqrt(dt)
     63    0.807250   0.004410   0.039726        0.3153
    252    0.822250   0.004274   0.024726        0.3925
   1008    0.830375   0.004196   0.016601        0.5271
   4032    0.835875   0.004141   0.011101        0.7049
```

**What is right:** the gap shrinks monotonically and MC approaches the closed
form from below, the required direction. Discrete monitoring cannot see barrier
crossings between observation times, so it must understate continuous first
passage.

**What is wrong:** the convergence rate does not match theory. Discrete-barrier
bias is O(sqrt(dt)) (Broadie-Glasserman-Kou), which would hold gap/sqrt(dt)
constant. It rises from 0.315 to 0.705. The fitted decay exponent is near
**0.29**, not 0.5.

**Most likely cause, not established:** the MC draws Box-Muller pairs from a
32-bit linear congruential generator. LCGs have known lattice structure and
consecutive-draw Box-Muller is a classic way to expose it. The generator was
chosen for reproducibility, not quality.

**Status: criterion 4 is NOT MET.** The cross-check shows the closed form is
not grossly wrong -- 0.836 against 0.847 at the finest grid, correct sign --
but it does not validate to sampling error and the rate discrepancy is
unexplained. This is not reported as a passed validation. Fixing it needs a
better generator or an analytic Brownian-bridge correction. Neither is required
for day 6; recorded as open.

## The parametric layer -- how much closes on LGD alone

PD held fixed at 84.70%. Only LGD varies.

```
     LGD   required spread    source
   5.00%        423.5 bps     Source A, from the liquidation incentive
   0.50%         42.3 bps     Source B upper bound
   0.30%         25.4 bps     Source B lower bound
   0.05%          4.2 bps     Source B, a few bps over zero

Source A required     250-400 bps   (specifications 3-5)
Source B predicted      3-30 bps    (at LGD 0.3-0.5%)
observed depositor       0-20 bps
```

**Moving LGD from 5% to 0.3% moves the required spread from 423.5 to 25.4 bps
-- a factor of 16.7, on one parameter, model and all other inputs held fixed.**

That single substitution carries the result from an order of magnitude above
observed to the edge of observed. At LGD 0.05% the output is 4.2 bps, inside
the observed 0-20 bps band.

**The parametric layer accounts for essentially the whole quantitative
disagreement.** Source B predicted this; this is an independent reproduction
from a separately written implementation.

## Specification layer

Source A is five specifications, not one, spanning 45 bps to over 400 bps:

| # | Specification | Output | Reproducible here |
|---|---|---|---|
| 1 | Passive, no rebalancing | > 400 bps | **Yes** (423.5 bps), minus jumps |
| 2 | Continuous rebalancing, infinite capital | 45 bps | No -- purely jump-driven |
| 3 | 20% extra capital | 350 bps | No -- Monte Carlo by construction |
| 4 | 100% extra capital | 130 bps | No -- Monte Carlo by construction |
| 5 | Discrete daily rebalancing | 250-400 bps | No -- needs discrete-monitoring adjustment |

**Correction to an earlier claim in this project.** Scenarios 2 and 5 were
described as the two closed-form tractable specifications. That was wrong.
Scenario 2 is purely jump-driven, because continuous rebalancing removes
diffusion as a default channel. Scenario 5 needs a discrete-monitoring
correction. **Scenario 1 minus its jumps is the pure Black-Cox case**, and it is
the one that reproduces.

Jump-diffusion stays out of scope. Extending the mapping to cover Scenario 1 in
full is a day-12 problem and would consume days 6 and 7.

## Structural layer

Not settleable by any harness. Source B rejects the mapping itself, arguing
on-chain lending is a repurchase agreement rather than a put sale, and that the
Merton decomposition is somewhat unfalsifiable because it ignores the margin
call mechanism that truncates exposure continuously.

No verifiable computation adjudicates whether a CDP is a short put or a repo.
This layer survives at any parameterization.

## Decomposition, stated

- **Parametric:** ~16.7x of the gap closes on LGD alone. Settled here.
- **Specification:** Source A spans 45 to 400+ bps across its own five variants,
  a factor of ~9 **within one side of the argument**. The public dispute has
  been conducted as though a single number were on the table.
- **Structural:** put versus repo. Survives any parameterization. Not settleable
  by verifiable computation.
