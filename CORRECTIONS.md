# Corrections, day 9

Two self-caught errors, both found by tests built to be able to fail, both
corrected in the open rather than amended away.

## C1. Trap 14 was misattributed -- retracted

Committed in f1e6ef1 as an API index inconsistency. **It was my pagination
loop.** Retracted in 74f1492. The data source returns the events correctly
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

Fixed in 427bffa, verified output-preserving: the reference path at
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


## C4. Resample count: verified and published are the same artifact

The write-up intervals must be the intervals the machine digest covers, or a
re-runner reproduces something other than what was published.

Interval stability against the 10,000-resample reference:

```
   boot   native   emulated   max interval dev   agree at 1dp
    100    17.7s      37 min         4.211 pp          0 / 60
    500    34.9s      73 min         3.831 pp          2 / 60
   1000    53.5s     111 min         2.315 pp          0 / 60
   2000    95.2s     198 min         1.426 pp          4 / 60
  10000   393.0s    13.6 hours       reference
```

Bootstrap error falls as 1 / sqrt(B), so there is no tractable middle. The
choice is 37 minutes with intervals that differ by up to 4 pp from a
high-resample estimate, or 13.6 hours.

**Decision: boot = 100, published and verified.**

The reason it is not a compromise: **all 60 point estimates are identical at
every resample count.** The surface spread of 5.42% to 99.95%, the 431.5x
conditional-to-unconditional ratio, and the 18.3 bps unconditional rate do not
depend on the bootstrap at all. Only interval widths do.

A 100-resample interval is not a wrong interval. It is a wider, noisier
estimate of the same quantity, and it is published with its resample count in
the payload header so nobody has to guess.

**And the deciding argument is about day 10.** Verification requires a stranger
to run this. A 13.6-hour emulated run is a serious favour to ask; a 37-minute
one is not. The reproducibility claim is worth exactly as much as the number of
people willing to test it, and run length taxes that directly. This is a
deliberate design choice, not a limitation.


## C5. An identity leak in a file whose purpose was to be evidence

The pre-publication identity check found a real local path in
`determinism-log.txt`, line 5 -- a captured command line from the day-1 native
validation run, containing the operating-system username.

It was in the **root commit**. Redacting it in a later commit would not have
removed it; `git log -p` recovers anything ever committed. The history was
therefore rewritten with `git-filter-repo --replace-text` before publication,
replacing the path with `[redacted-local-path]`.

```
  before   command : 'C:\Users\user\...\python.exe' probe.py --sum-n 100000
  after    command : '[redacted-local-path]\python.exe' probe.py --sum-n 100000
```

**What survived, verified after the rewrite:**

```
  authorship           HashHarbour, sole author and committer
  timezone offsets     +0000 throughout
  commit ordering      root commit still the probe and harness, dated first
  hash chain           probe.py 868bb295... still matches the digest recorded
                       inside determinism-log.txt
  dataset hash         54e7610b... unchanged
  full-history scan    zero occurrences of the username or any local path
```

**What changed:** all 34 commit hashes. Five cross-references in
`CORRECTIONS.md`, `DAY9-RESULTS.md` and `determinism-log-machine.txt` were
updated in the same commit that records this.

### Why this one is worth stating in the write-up

The leak was in a file **produced specifically to be evidence**, on the same day
the pseudonymous identity was configured precisely to avoid this. Git config
protects authorship and email. It does nothing about the **contents** of
captured command lines, logs and screenshots -- which is exactly the surface a
verifiable-computation artifact generates most of.

That gap was flagged on day 1 and still produced a leak nine days later. It is
the third self-caught error in this project and the only one with a real-world
consequence attached, and it argues that identity hygiene needs a content scan
over the full history, not just a `git config` check.

The redaction was done at the last moment it was free. After publication, a
rewrite costs every external reference to every hash.
