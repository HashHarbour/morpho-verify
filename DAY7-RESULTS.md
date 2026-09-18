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
