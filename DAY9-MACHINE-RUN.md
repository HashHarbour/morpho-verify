# Day 9 close: the surface, verified in-machine

## Artifact identity

```
machine hash     7ab6f269e574d84588b9175991d5f6d2e0531b46e8103d696e4d0831a7c4ac79
payload sha256   dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
dataset sha256   54e7610b891365ea28d000f7c9521ad7251c2e51b9c194115c548f7230da5028
bake wall        96.4 s
run wall         1138 s host   (49,587,668,657 cycles)
resamples        100, seed 20260918, python random.Random
```

The dataset inside the machine image hashes to the value committed in the
repository. The input is verifiable independently of the output.

## Native and machine payloads are IDENTICAL

```
  native   dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
  machine  dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
  differing records: 0 of 240
```

**This was predicted to differ, and the prediction was wrong.** The stated
expectation was 1-ULP divergence in the erf family, per the day-2
characterisation.

The error was a conflation. `blackcox.py` computes required spreads through
`erfc` and does live in the divergent region. **The surface payload does not
import it.** Empirical LGD is integer sums, exact divisions, index resampling
and sorting -- precisely the operations day 2 found **bit-identical** across
amd64 and riscv64 (probe sections A, C and E). Only section B, the erf family,
diverged.

So the correct statement is narrower than the one in `MODEL-SPEC.md` section 5:
**the spread computation lives in the divergent region; the empirical-LGD
surface does not.** Corrected here rather than left as a mis-set expectation
for a day-10 re-runner, who would otherwise treat an exact match as suspicious.

## Overhead is workload-dependent, as flagged on day 2

```
  probe   (float-heavy)   ~125x compute overhead
  surface (integer-heavy)   ~64x  (1138 s against 17.7 s native)
```

The day-2 caveat that 125x is "not transferable to the model without
re-measuring" holds. The surface is roughly twice as cheap to emulate, because
integer arithmetic and sorting emulate better than transcendentals.

Run length also came in under estimate: **19 minutes, not 37.** A reproduction
a stranger can do over coffee, which was the argument for boot 100.

## What day 10 tests

Emulated-to-emulated across hosts. A re-runner builds from the pinned base
image digest, bakes the committed dataset, runs at boot 100 seed 20260918, and
must obtain payload `dbdcbb34...` and machine hash `7ab6f269...`.

That the native result happens to match as well is a bonus, not the claim.
