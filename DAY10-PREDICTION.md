# Day 10 prediction -- pre-registered before any third party runs this

Committed before a single reproduction attempt. Same discipline as every other
gate in this project.

## The claim under test

The same machine image, built from the same pinned inputs **on hardware that is
not mine**, produces:

```
  machine hash     7ab6f269e574d84588b9175991d5f6d2e0531b46e8103d696e4d0831a7c4ac79
  payload sha256   dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
```

Nine days of agreement so far are **one laptop agreeing with itself**. This is
the first test of the central claim.

## What I expect, stated in advance

**Payload digest: expected to reproduce exactly.**
The surface is integer sums, exact divisions, index resampling and sorting. Day
2 found those operations bit-identical between amd64 and riscv64 (probe
sections A, C, E); only the erf family diverged, and the surface does not use
it. Day 9 confirmed native and in-machine payloads match exactly. Confidence:
high.

**Machine hash: genuinely untested.**
This depends on the build being reproducible across hosts, not just across
runs. A different BuildKit version, a different host architecture, or any
toolchain difference could alter the rootfs even with byte-identical file
contents. My own day-2 cold rebuild reproduced it, but on the same machine.
Confidence: moderate, and this is the one I would not be shocked to see fail.

## What each outcome means -- fixed before seeing any result

```
  dataset hash differs        checkout differs; nothing downstream is
                              comparable. Stop and resolve first.

  machine hash differs,       THE BUILD IS HOST-SENSITIVE, THE COMPUTATION
  payload matches             IS NOT. A weaker claim, still publishable, and
                              arguably the more interesting finding: it would
                              say reproducible computation does not require
                              reproducible builds.

  machine hash matches,       EXECUTION NON-DETERMINISM. This is the serious
  payload differs             one. It would contradict days 2 and 9 and
                              invalidate the central claim.

  both match                  The claim holds on foreign hardware.
```

**The second row is pre-registered as a publishable result, not a failure.** It
is recorded here so that if it happens, the framing cannot be accused of having
been chosen after the fact.

## The strongest available test

**Apple Silicon.** A completely different host architecture reproducing a
riscv64 machine hash tests this far harder than another x86-64 Linux box does.
If exactly one reproduction is obtained, that is the one worth having.

## What reporters are asked to send

All three hashes, plus OS, host architecture and Docker version -- **whatever
the outcome**. A failed reproduction with good diagnostics is worth more to this
artifact than a successful one with none.
