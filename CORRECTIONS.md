# Corrections, day 9

Two self-caught errors, both found by tests built to be able to fail, both
corrected in the open rather than amended away.

## C1. Trap 14 was misattributed -- retracted

Committed in 350af38 as an API index inconsistency. **It was my pagination
loop.** Retracted in d940903. The data source returns the events correctly
under hash, timestamp and badDebt filters.

## C2. A payload header that misstated its own artifact

`n=BOOT` and `seed=SEED` were default arguments bound at import. Every run used
**10,000 resamples and seed 20260918**, whatever was passed.

**Three published numbers were mislabelled:**

```
  day-8 surface            labelled as computed at the default; was 10,000
  timing "boot 1000: 205s" was 10,000 resamples, not 1,000
  digest 6126a09b...       header said boot-resamples 1000; body used 10,000
```

The third is the sharpest. **A payload header that misstates the artifact it
heads is the exact failure this project exists to document, occurring in my own
serializer.** The header is now read back from the module global after it is
set, so it reports what was used rather than what was requested.

Fixed in e15eec7, verified output-preserving: the reference path at
10,000/20260918 reproduces the prior body byte for byte,
`2bf17029140628704edbcdf8b25522a98ff1ef112beaaae19522cf3f806fccfc`.

## C3. The fast bootstrap is NOT output-preserving -- disabled, not deleted

With working plumbing, `equivalence_check.py` compared the optimised and
reference paths across six configurations -- three resample counts at the
committed seed, three additional seeds:

```
    boot       seed   reference           fast                match
      50   20260918   eb50463af8483208    8457d99aa6632bcb    NO
     100   20260918   a3a0cd246c855add    76f932358e042a60    NO
     200   20260918   c36bca701fc0a84f    700bd12dbe13d81e    NO
     100          1   e691bfabd602fea1    e77a313d529cc061    NO
     100     424242   819434c8ac25b68b    587d918d78d2d4ec    NO
     200    7777777   c24264ed552464ea    6831b5a9670cb923    NO
```

**Six for six.** `FAST` is set to `False` and the optimisation is unused.

**The cause was not investigated.** Diagnosing a mismatch against a known-good
target is debugging toward a digest, which is the one move the pre-committed
stop-rule forbids. The code is retained so the failure stays reproducible by
anyone who wants to find the cause under conditions where a target output is
not already in hand.

**Consequence:** the in-machine run uses the reference path at a reduced
resample count. Published intervals come from higher-resample native runs; the
verified digest covers point estimates and coarser intervals, and the header
states which.
