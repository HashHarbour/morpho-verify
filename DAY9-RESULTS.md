# Day 9 results: correction, recovery, and the quantified headline

## 1. CORRECTION -- trap 14 as committed in 350af38 was WRONG

Day 8 recorded that the API index is inconsistent across filter paths. **That
attribution is false and is retracted here rather than quietly amended.**

The discriminating diagnostic, run on the largest missing event
(blk 25259134, chain 1, $1,181,253.93):

```
  A) by transaction hash filter        1 item   returned
  B) narrow timestamp window, +-60s    1 item   returned
  C) same window + badDebtAssets_gte   1 item   returned
```

**The timestamp filter returns the event correctly.** The 377 omissions were
caused by my extraction, not by the data source.

Two further hypotheses were raised and both disconfirmed:

- **Unstable sort under offset pagination.** Would produce duplicates alongside
  omissions. The pull had 7,447 rows and 7,447 distinct keys -- zero duplicates.
- **Chunk boundary gaps.** All 377 missing events fell inside the extraction
  window.

## 2. The actual cause, and it invalidates an assertion used since day 3

The extraction loop ended a chunk on a short page:

```python
  if len(it) < PAGE: break      # assumes short page == last page
```

Re-running with the loop ending only on an **empty** page:

```
                      old pull      new pull    ratio
  distinct events        7,447        36,619
  USDC-loan              7,447        27,259     3.7x
  total repaid        $175.2M       $705.2M      4.0x
  total bad debt      $103,939    $1,292,191    12.4x
  missing of 611 known     377             5
```

**Breaking on a short page lost 73% of the rows.** The recovered pull now
accounts for 606 of the 611 known bad-debt events and $1,292,191 of the
$1,296,112 known bad debt.

### The consequence, stated plainly

**Trap 12 asserted that a short final page proves pagination is exhausted. That
assertion is unsound and was used on three earlier extractions:**

```
  day 3  market population      3,904 markets
  day 6  vault list               980 vaults
  day 7  position census      10,100 positions
```

All three may be undercounts. The assertion is necessary but not sufficient:
only an empty page proves exhaustion. **These three must be re-verified before
publication**, and until they are, every figure derived from them carries this
caveat. Recorded as an open item, not silently corrected.

## 3. The headline, quantified

Same formula, two event sets: `badDebt / (badDebt + repaid)`.

```
  UNCONDITIONAL   all 27,259 USDC liquidations
                  $1,292,191 / $706,496,711  =  0.1829%  =  18.3 bps

  CONDITIONAL     the 606 that produced bad debt
                  $1,292,191 / $1,637,353    =  78.9195%

  RATIO           431.5x
  share of liquidations producing bad debt: 2.22%
```

**The two definitions differ by 431.5x. The published disagreement spans 12.5x
(5% against 0.4%). The definitional gap is 34.5 times the disagreement gap.**

That is the sentence the artifact has been building toward, and it is now a
number rather than an order of magnitude.

### Where each side lands

```
  Source A LGD ~5%          a conditional severity -- but the measured
                            conditional figure is 78.9%, not 5%
  Source B LGD 0.3-0.5%     compare to measured unconditional 0.1829%
                            -- Source B is CONSERVATIVE against the record
  observed spreads 0-20bps  measured unconditional rate 18.3 bps
```

**The measured unconditional loss rate, 18.3 bps, sits at the top of the
observed depositor band of 0 to 20 bps.** Depositors are receiving
approximately the realized unconditional loss rate. Neither publication states
this, and it follows from neither published figure taken alone.

## 4. What this does NOT establish

- **The denominator completeness is not independently verifiable.** Missing
  bad-debt events are detectable because a second, differently-filtered
  extraction of exactly those exists. **There is no second filter for
  zero-bad-debt liquidations.** The union recovers the numerator; it does not
  prove the denominator whole.
- 5 bad-debt events totalling $3,921 remain absent from the recovered pull.
- The three day-3/6/7 extractions are unverified under the corrected assertion.
- Conditional severity of 78.9% is pooled across both chains and is dominated
  by one event; the day-8 surface shows it ranges 5.42% to 99.95% across
  defensible choices.
