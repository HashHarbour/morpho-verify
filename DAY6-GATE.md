# Day 6 regime gate -- threshold fixed BEFORE classification

Committed before the market population is extracted or classified. Deciding
what counts as material after seeing the distribution is how a decision gets
made by its own answer.

## Classification rule

For each USDC-loan market, compute PD at its own LTV and its own LLTV, using:

```
sigma = 0.75     Source A reference value
r     = 0.0425   Source A
T     = 1 year   Source A convention, an assumption not a measurement
```

Regimes, from the day-5 saturation measurement:

```
  PD < 0.25    LOW-PD      sigma dominates LGD
  0.25 - 0.75  MID
  PD > 0.75    SATURATED   sigma damped, LGD dominates
```

## The threshold

**MATERIAL = at least 20% of total USDC borrow exposure sits in LOW-PD
markets.**

Exposure-weighted, not count-weighted. A thousand dust markets at low PD do not
change what the model is for; a few large ones do.

## The consequence, fixed in advance

- **If MATERIAL:** the `MODEL-SPEC.md` section 3 decision to fix sigma is
  **VOID**. The decomposition grows a second row and the surface design must be
  revisited before it is built.
- **If NOT MATERIAL:** the sigma decision is **CONFIRMED**, conditional on the
  book staying in the saturated and mid regimes, and that conditionality is
  stated in the write-up.

Either outcome is recorded. Neither is adjusted.

## Secondary reporting, no threshold attached

Also report the same classification count-weighted, and the exposure share in
each of the three regimes. These are descriptive. Only the 20% exposure figure
in LOW-PD triggers the consequence above.

## Known bias in this gate, stated now

PD is computed at **aggregate market LTV**. PD is convex in LTV over this
region -- the day-5 table spans 248x across it -- so
`PD(mean LTV) < mean(PD(LTV))`. Classification at aggregate LTV therefore
**understates** PD, which biases markets **toward the LOW-PD bucket**.

Direction: this makes MATERIAL **more** likely, not less. The gate is
conservative in the direction that would void the sigma decision, which is the
safe direction for it to err.

The convexity bias is treated fully in the LTV decision recorded separately.
