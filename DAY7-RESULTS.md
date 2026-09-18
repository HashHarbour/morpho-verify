# Day 7 results

## 1. Convexity magnitude: aggregate LTV understates PD by 6.8%

Measured on cbBTC/USDC (Base), the largest genuine market by exposure.

```
positions fetched              10,100  (skip ceiling reached)
coverage of market borrow      95.79%  ($1.364bn of $1.424bn)
aggregate LTV                  46.91%
PD at aggregate LTV            0.529493
borrow-weighted mean PD        0.565357
UNDERSTATEMENT                 1.0677x   (+6.8%)
```

**The caveat is now a number.** Modelling this market at its aggregate LTV
understates default probability by 6.8%, in the direction that flatters the
result -- consistent with every other confound found in this project.

Why it is modest rather than dramatic: the position distribution is tight.
93% of borrow sits between LTV 30% and 70%, where PD is only mildly convex.
The 248x figure from day 5 spans LTV 20-70%, a range this market does not
populate.

```
  borrow exposure by position LTV
    30-40%   13.7%      50-60%   31.6%
    40-50%   34.2%      60-70%   13.0%
```

**Scope:** one market, 95.8% covered. Not generalised to the other 388. A
market with a wider LTV spread would show a larger bias.

## 2. FINDING: the API cannot enumerate more than 10,100 positions

The endpoint rejects a skip above 10,000, with the constraint stated as
"skip must not be greater than 10000".

**A complete position census of any market with more than about 10,100
positions is impossible through this endpoint.** Ordering by borrow size
descending captures the largest positions first, which is what recovered 95.79%
coverage here -- but an unordered or differently-ordered query would silently
return an arbitrary 10,100.

This is the fourth distinct pagination hazard found in this API. See section 4.

## 3. sigma by collateral class -- ASSIGNED, not measured

Five classes with stated values. These are **assumptions with reasoning, not
measurements**, and they are labelled as such because a full per-asset
volatility pipeline is a second dataset.

```
  class            sigma    representative assets
  BTC-like          45%     cbBTC, WBTC
  ETH-like          60%     WETH, cbETH
  LST / LRT         65%     wstETH, weETH  (ETH vol plus basis risk)
  stablecoin        10%     USDe, USDC-adjacent
  RWA / PT          15%     PT tokens, tokenised credit
```

**Provenance is incomplete and that is stated rather than papered over.** These
values are chosen as plausible annualised realised volatilities for each class.
**No citation is attached because none was verified**, and inventing one would
be worse than admitting the gap. Before publication each value needs a
documented source or a computed estimate.

Day 6 established these do real work: at cbBTC/USDC LTV 46.9%, sigma leverage
runs 2.9-6.2x. **The day-5 reference value of 75% is far above the 45% assigned
to BTC-like collateral here**, and the largest market in the book is BTC-like.
The sensitivity sweep already built is what carries this.

## 4. The pagination behaviour is a property of the data source

Four distinct hazards, all silent:

```
  markets           returned exactly 1,000 of 3,904     (day 3)
  vaults            returned exactly   200 of   980     (day 6)
  marketPositions   skip hard-capped at 10,000          (day 7)
  marketPositions   skip requires an explicit orderBy   (day 7)
```

The last is the sharpest: without an explicit orderBy, paginating fails
validation rather than working -- while a caller who never paginates gets a
full page and no indication it is partial.

**Three endpoints returning a full page and stopping is not three accidents. It
is how the API behaves.** Any analysis built on a single unpaginated query is
working from an arbitrary subset, and nothing in the response says so.

Given that both sides of this dispute presumably queried this API, this belongs
with the exposure finding: a thing no reader can verify from the outside.


---

## 5. sigma measured, not assigned -- and the gap is 4.06x

`sigma_estimate.py`, committed. Daily closes from CoinGecko, log returns,
sample stdev annualised by sqrt(365), trailing 365 days. **An independent price
source deliberately, not the Morpho indexer whose USD prices were found
defective for 78% of reported exposure.**

```
  class        proxy            obs   realized   assigned
  BTC-like     bitcoin          365      44.8%        45%   CONFIRMED
  ETH-like     ethereum         365      64.3%        60%   close, adopt measured
  LST / LRT    wrapped-steth    365     107.7%        65%   ANOMALOUS, see below
  stablecoin   ethena-usde      365       1.7%        10%   assumption was 6x high
  RWA / PT     --                --          --       15%   not measurable this way
```

**The LST figure is not adopted.** wstETH should track ETH closely, so 107.7%
against ETH at 64.3% is implausible and most likely reflects bad points or gaps
in that series rather than real volatility. It is reported rather than hidden,
and the assigned 65% is retained on the reasoning that LST volatility is ETH
volatility plus a small basis. **This needs a cleaner series before publication.**

RWA and PT tokens have no liquid continuous price series and remain an
assumption, stated as such.

### The consequence: LGD is not the only mis-set parameter

Source A runs its headline at **LTV 70% and sigma 75%**. The dominant real
market -- cbBTC/USDC, 92% of the Steakhouse Prime vault and the largest genuine
market in the book -- sits at **LTV 46.9% (measured from 10,100 positions) and
sigma 44.8% (measured from 365 daily closes)**.

```
  Source A    LTV 70.0%  sigma 75.0%   PD 0.8470   423.5 bps at LGD 5%
  cbBTC/USDC  LTV 46.9%  sigma 44.8%   PD 0.2086   104.3 bps at LGD 5%
                                                   ratio 4.06x
```

Decomposed, the two inputs interact rather than add:

```
  LTV 70 -> 46.9 alone (sigma held 75)      1.60x
  sigma 75 -> 44.8 alone (LTV held 70)      1.24x
  both together                             4.06x
```

**A factor of 4.06x sits in LTV and volatility alone, before LGD is touched.**
Both are now measured rather than assumed. The day-5 conclusion that the dispute
reduces to a single multiplicative parameter was correct at Source A parameters;
at the parameters of the market that actually carries the exposure, two further
inputs carry 4x between them.

And with measured sigma plus the Source B LGD:

```
  cbBTC parameters, LGD 0.30%     6.26 bps
  cbBTC parameters, LGD 0.05%     1.04 bps
  observed depositor spreads      0-20 bps
```

**The same four guards from `MODEL-SPEC.md` apply to these figures.** LTV and
sigma here are measured; LGD is still selected, not derived. Nothing here
establishes which LGD is correct, and the claim remains that the observed band
is reachable under measured inputs -- not that observed rates are justified.
