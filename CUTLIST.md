# Post structure and cut list

Committed **before** the draft, for the same reason every other spec in this
repo was: deciding what to include after seeing how good the prose is, is how a
post doubles in length and stops being read.

Target: **1,500 to 2,500 words.** There is roughly five times that in material.

---

## Structure, fixed

1. **The tension.** Two careful people disagreed by 12.5x and both were
   arithmetically correct. Lead there, not with what was built.
2. **The control.** The $2.13 confirmation. First substantive item, because a
   reader who meets divergences before any confirmation suspects the method
   manufactures disagreement.
3. **The headline.** Conditional 78.9% against unconditional 18.3 bps. A 431.5x
   definitional gap against a 12.5x published disagreement. Backward-looking
   guard in the same paragraph, never below it.
4. **Four divergence axes.** Amount, identity, time, exposure. The
   $9.08bn-against-$260.46 figure gets room; it is the one that makes a reader
   sit up.
5. **Data-source behaviour.** Mid-stream truncation and the near-miss it
   produced.
6. **Methodology, led by my own error.** C7 as centrepiece.
7. **Reproduce it in twenty minutes.** Three hashes, link, invitation to
   falsify.

Cartesi appears no earlier than section 4, as the mechanism. The dispute leads.

---

## CUT to the repo entirely

These are good work. None of them is the argument.

```
  days 1-2 determinism gate        infrastructure, not a finding
  the probe design and negative test   PROBE.md, determinism-log*.txt
  sigma measurement methodology    DAY7-RESULTS.md section 3
  convexity +6.8%                  DAY7-RESULTS.md section 1
  full regime table by LTV         MODEL-SPEC.md amendment
  the 60-cell surface in full      DAY8-RESULTS.md
  parameter arithmetic             DAY5-RESULTS.md
  the equivalence-check failure    CORRECTIONS.md C3
  resample-count decision          CORRECTIONS.md C4
  eleven of the fourteen traps     METHODOLOGY-TRAPS.md
```

**Test for every paragraph: if its job is to show how much work was done, cut
it.** The commit history does that better and nobody doubts it.

## KEEP -- three traps only, each earning a specific point

```
  the emulated clock (trap 10)     a number that reads as a measurement
                                   and is not
  mid-stream truncation (trap 12,  a complete-looking result that silently
  corrected day 9)                 omits, plus the 5.9 bps near-miss
  C7                               a test that could not fail, and what
                                   "verified" actually has to mean
```

Not enumerated. Each one illustrates a claim the post is already making.

## KEEP -- the numbers that carry argument

```
  $2.13 against $0.08 / $0.15       the control
  78.9% conditional vs 18.3 bps     the headline
  431.5x against 12.5x              the definitional gap
  2.22% of liquidations             where the factor comes from
  49,303.14 vs 83,787.16            amount axis, 41% apart
  99.7% RLP                         identity axis
  65 liquidations, $1.84M, zero     time axis
  $9.08bn against $260.46           exposure axis
  five specifications, 45-400+ bps  spread within one side
  4.06x from LTV and sigma          before LGD is touched
  three hashes                      the reproduction
```

---

## The three framing rules

**Never adjudicate.** Every finding is what was measured, never what someone got
wrong. The regime finding is the most attackable sentence in the piece: it is a
statement about what a reader cannot check without re-executing, not about
anyone intent, and it must be written so no reasonable reader can take it the
other way. The reciprocal observation about the other side goes in the same
breath, not a later paragraph.

**Every number carries its scope inline.** 18.3 bps never appears without
measured unconditional rate over the window, backward-looking. A figure quoted
without its qualifier is a figure that gets dismantled.

**Lead methodology with my own error.** C7 generalises past this project: a test
run from inside working state cannot distinguish a reproducible artifact from
one that merely works locally.

## Explicit non-claims

```
  host independence         NOT claimed. Clean-room ran on my own machine.
  adjudication              NOT claimed. The structural layer is settleable
                            by no harness.
  forward-looking adequacy  NOT claimed. 18.3 bps is realized and backward
                            looking.
  denominator completeness  NOT claimed. Unverifiable by the method that
                            validated the numerator.
```

## What not to do

- No @-mentions of participants. Reference and link by name. Public tagging
  reads as calling someone out; day-14 outreach is a different act and works
  better cold.
- No teasers before publication.
- One plain sentence on AI assistance. It is in the README and the commit
  history; burying it invites a reader to discover it.
