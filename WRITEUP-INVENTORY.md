# Write-up inventory

One line per finding, with evidence and location. Ordering is deliberate and
pre-committed: the control comes first.

## 1. CONTROL -- a published figure that checks out

| # | Finding | Evidence | Where |
|---|---|---|---|
| 1.1 | Steakhouse Prime bad debt is essentially zero, confirming the counter-argument empirical foundation | $0.08 across currently-allocated Prime markets, $0.15 across 41 Steakhouse USDC markets, against a published $2.13 | `DAY6-RESULTS.md` s6 |

**This section leads.** A reader who meets five divergences before any
confirmation will suspect the method manufactures disagreement. One who meets
the control first reads the rest as findings.

## 2. Published figures vs chain state -- four axes

| # | Axis | Finding | Where |
|---|---|---|---|
| 2.1 | Amount | Published 49,303.14 USDC is net of a 34,480.95 recovery; on-chain gross is 83,787.16. 41% apart, both correct, neither source says which | `FINDINGS.md` s1 |
| 2.2 | Identity | Dominant Ethereum concentration is RLP-collateralized (99.7%), not the USR or wstUSR named in reporting | `FINDINGS.md` s2 |
| 2.3 | Time | Loss realizes at liquidation, not impairment. 65 liquidations repaid 1.84M with zero bad debt across the exploit month and three after; the entire 1.18M landed in one terminal liquidation that repaid nothing | `FINDINGS.md` s3 |
| 2.4 | Exposure | 78% of reported borrow exposure sits in markets with impossible LTV. PAXG reports 9.08bn against 260.46 collateral | `DAY6-RESULTS.md` s2, s7 |

## 3. The data source itself

| # | Finding | Where |
|---|---|---|
| 3.1 | Four distinct pagination hazards, all silent: markets 1,000 of 3,904; vaults 200 of 980; positions skip capped at 10,000; skip requires explicit orderBy | `DAY7-RESULTS.md` s4 |
| 3.2 | Ordering by size descending is what recovered 95.79% position coverage. Any other ordering returns an arbitrary slice with no indication it is partial | `DAY7-RESULTS.md` s2 |

## 4. The dispute, decomposed

| # | Finding | Where |
|---|---|---|
| 4.1 | Source A is five model specifications spanning 45 to 400-plus bps, a factor of 9 within one side | `DAY5-RESULTS.md` |
| 4.2 | Specification 1 reproduces: 423.5 bps against a published figure above 400 bps | `DAY5-RESULTS.md` |
| 4.3 | Required spread is linear in LGD, so the quantitative dispute reduces analytically to one multiplicative parameter neither side can measure, at Source A parameters | `DAY5-RESULTS.md` corrections s1 |
| 4.4 | sigma leverage is regime-dependent: 1.33x at LTV 70%, 248x at LTV 20% | `MODEL-SPEC.md` amendment |
| 4.5 | Both parameter choices sit in regimes favouring their own conclusions. Stated as checkability, not intent | `DAY6-RESULTS.md` s4 |
| 4.6 | LTV and sigma together carry 4.06x between Source A parameters and the dominant real market, before LGD is touched. Both measured | `DAY7-RESULTS.md` s5 |
| 4.7 | The structural layer, put sale versus repo, is settleable by no harness | `MODEL-SPEC.md` s9 |

## 5. Methodology, the section that makes the rest credible

| # | Finding | Where |
|---|---|---|
| 5.1 | Thirteen traps, each a number that reads as a measurement and is not | `METHODOLOGY-TRAPS.md` |
| 5.2 | A deterministic machine has a deterministic clock: in-machine elapsed is emulated time, understating overhead 8x | traps s10 |
| 5.3 | Determinism gate passed: four runs, one digest, across a full teardown; machine hash reproduced from zero images | `determinism-log-machine.txt` |
| 5.4 | Pre-registration produced three target failures, each traced to a narrative figure registered against a differently-defined on-chain quantity | `RECONCILIATION.md` |
| 5.5 | Convexity: aggregate LTV understates PD by 6.8%, measured on 95.79% coverage | `DAY7-RESULTS.md` s1 |

## Ordering note

Cartesi appears in paragraph four, as the mechanism. The dispute leads.

## Open before publication

- LST volatility series is anomalous, 107.7% against ETH at 64.3%; needs a cleaner source.
- RWA and PT sigma remains an assumption with no measurement path.
- Target C, the independent cross-check against prior art, unevaluated; needs Dune access.
- Vault-level attribution out of scope; market-level only.
