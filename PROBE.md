# Determinism probe

Tests whether Python float arithmetic is bit-reproducible inside the Cartesi
RISC-V machine. Independent of the CLI major version — V1 and V2 make no
difference to this question.

| File | What it is |
|---|---|
| `probe.py` | The probe and its serializer. Pure stdlib, single file. |
| `harness.py` | Runs the probe N times, digests each payload, diagnoses mismatches. |
| `FALLBACK.md` | What to do when numpy is missing or digests diverge. |

## Running it

Natively, to validate the harness before Docker exists:

```bash
python3 harness.py --runs 3 --label "native baseline"
```

Against the machine, once the CLI works — only the command changes:

```bash
python3 harness.py --target cmd --cmd "<machine invocation>" --runs 2 --label "in-machine"
```

Day 2 run 3, after a full container teardown and rebuild:

```bash
python3 harness.py --target cmd --cmd "<machine invocation>" --runs 1 --label "post-teardown"
```

Each invocation appends to `determinism-log.txt` with digests visible in plain
text, and writes `results/summary.json` for scripted comparison. Exit status is
0 on match, 1 on mismatch, so it can gate a build.

## Design decisions worth knowing

**Floats are emitted via `float.hex()`, never rounded decimals.** A rounded
decimal can print identically for two values that differ in the last few ulps —
which is precisely the divergence being hunted. `float.hex()` is exact and
round-trippable, renders `inf`/`nan` without special-casing, and keeps `-0.0`
distinct from `0.0`.

**The payload is written as bytes with an explicit `b"\n"`.** A text-mode
stream on Windows would translate `\n` to `\r\n` and change the digest for
reasons unrelated to arithmetic.

**Metadata goes to stderr, never stdout.** Interpreter version, platform, and
timing must stay out of the payload. If they were in it, a native run and an
emulated run could never produce the same digest and you would lose the ability
to compare across targets.

**The workload parameters are in the payload header.** `sum-n` and the numpy
flag are hashed, so two runs with different settings produce a loud mismatch
rather than a silent comparison of two different experiments.

**The numpy section is opt-in and off by default.** The default payload is
therefore comparable between any two environments regardless of whether numpy
is installed in either.

**Mismatches are localized, not just detected.** The harness prints which
sections moved and the specific differing lines, with float hex decoded back to
decimal for reading. A harness that only says "the digests differ" tells you
nothing about what to fix.

## Environment hygiene, and what each setting prevents

`harness.py` applies these to the child process automatically (`HYGIENE` dict).
If you run `probe.py` by hand, set them yourself.

| Variable | What it prevents |
|---|---|
| `PYTHONHASHSEED=0` | String hashing is randomised per process. Set iteration order then varies between runs. Dicts are *not* affected — they have preserved insertion order since 3.7 — so a set is the canary, not a dict. |
| `OMP_NUM_THREADS=1` | Multithreaded reductions sum in an order that depends on thread scheduling, changing the last bits. Only bites if numpy or another BLAS-backed library is present, but costs nothing when it is not. |
| `OPENBLAS_NUM_THREADS=1` | Same, for OpenBLAS specifically, which numpy wheels usually bundle. |
| `MKL_NUM_THREADS=1`, `NUMEXPR_NUM_THREADS=1`, `VECLIB_MAXIMUM_THREADS=1` | Same, for the other backends a numpy wheel might carry. |
| `LC_ALL=C`, `LANG=C` | Locale can alter string collation and number formatting. |
| `TZ=UTC` | Defensive. Nothing in the payload reads the clock, but this closes the class. |
| `PYTHONDONTWRITEBYTECODE=1` | Keeps stray `.pyc` writes out of the tree. |

Beyond env vars, the probe itself observes the rules:

- **No wall-clock in the payload.** `time.perf_counter` is read once for the
  timing line, which goes to stderr only.
- **No unseeded randomness.** Inputs come from an explicit integer LCG, not
  `random`. Pure integer arithmetic, so the generator is bit-exact anywhere.
  Conversion to float divides by `2**32` — an exact power-of-two scaling, so
  the only rounding happens in the arithmetic being measured.
- **No filesystem iteration.** The probe reads no files and lists no
  directories.
- **Pin every dependency, including the base image digest.** The probe has no
  dependencies; the Dockerfile will. Pin by digest (`FROM image@sha256:...`),
  not by tag — tags are mutable and a silently moved tag is an unreproducible
  build.

## Benchmark methodology — four traps

**1. Compare WSL-native against emulated, not Windows-native against emulated.**
The machine runs inside WSL2. Timing against Windows Python would fold a
filesystem and syscall penalty into a number you would then publish as
emulation overhead.

**2. Quote the probe's self-reported `elapsed_seconds`, not the harness wall
time.** Measured on this laptop, Windows native, `--sum-n 100000`:

```
probe.py internal elapsed : 0.43 s
harness measured wall     : 2.63 s
```

About 83% of the wall time is interpreter startup and process spawn. Inside the
machine the equivalent fixed cost is a full Linux kernel boot in RISC-V, which
is far larger. A ratio built from wall times would mostly measure boot time, not
computation.

Record both, and label them as two different things:

- **compute ratio** = emulated `elapsed_seconds` ÷ native `elapsed_seconds`
- **fixed startup cost** = wall − `elapsed_seconds`, reported separately

The compute ratio is the number that determines model scope. The startup cost
is a one-off per invocation and matters only for how the harness is driven.

Measured scaling of the probe's internal time on this laptop:

| `--sum-n` | internal elapsed |
|---|---|
| 2,000 | 0.064 s |
| 50,000 | 0.222 s |
| 100,000 | 0.433 s |
| 400,000 | 2.09 s |

Fixed sections (A, B, D, E) account for roughly 0.05 s; the rest is section C.
For the day-2 measurement use a `--sum-n` large enough that computation
dominates measurement noise — 100,000 is a reasonable default and is what has
been validated.

> **Correction — item 2 applies to native runs only.** Inside the Cartesi
> Machine the guest clock is derived from cycle count, so `elapsed_seconds` is
> *emulated* time, identical across runs regardless of how long the host
> actually took. Using it there understates emulation overhead roughly
> eightfold. **Native side: probe self-reported elapsed. Machine side: host wall
> time.** Never mix them. See trap #10.

**3. Baseline on uv's CPython 3.13.2, not Ubuntu's system `python3`.**
The machine ships Python 3.13.2. Ubuntu ships 3.12.3. Measured across three
interpreters, the probe payload is bit-identical — interpreter version and
build toolchain contribute exactly nothing to the digest:

```
uv 3.12.3 / uv 3.13.2 / Ubuntu 3.12.3
  -> 4d0229b16d20b98cca2f17de661f7353625efc23be8379ec99f952363e197419
```

**4. But build flags move the timing without moving the digest.**

| interpreter | best internal elapsed |
|---|---|
| uv 3.13.2 | 0.568 s |
| uv 3.12.3 | 0.576 s |
| Ubuntu system 3.12.3 | **0.845 s** — 1.47x slower |

Identical work, identical output bytes, 47% slower. Baselining on Ubuntu's
build inflates the denominator and **deflates** the overhead ratio by ~32%
(35.5x vs 52.1x against a 30 s emulated run) — the flattering direction, which
is the dangerous one. A digest check cannot catch this; only the timing moves.

Record which interpreter build produced every published timing. Full provenance
is in [ENVIRONMENT.md](ENVIRONMENT.md).

## Harness design — one invocation, one payload

The machine costs **4.1 billion cycles to boot**, paid on every invocation
regardless of what is computed. A parameter sweep run as N separate machine
invocations pays that N times and boot dominates the budget.

The sweep therefore computes the **whole surface inside a single machine
invocation**, emitting **one payload**. Cheaper, and cleaner for the claim: one
digest covering one complete experiment, rather than N digests a re-runner has
to reassemble.

## Running it inside the machine

`machine-run.sh` drives `cartesi-machine` directly rather than going through
`cartesi shell`, which hard-codes `--tty`/`-it`. That matters: a TTY injects
carriage returns into the payload and corrupts the digest. No TTY, clean bytes.

```bash
RUNS=2 OUT=/tmp/machine-run ./machine-run.sh
```

Inside the machine stdout and stderr merge onto one console, so the payload is
extracted by its own `# probe-version` / `# records` delimiters. That is safe
because `probe.py` flushes stdout before writing any metadata.

## numpy: not attempted, by design

PyPI publishes **zero riscv64 files for numpy** out of 4,232. pip would compile
from source under emulation at ~125x, plausibly for hours.

It was never needed. `math.erf` is confirmed working in-machine on Python
3.13.2, subnormals are not flushed, and the model is 78,000 closed-form
evaluations — roughly 150 s emulated — with nothing to vectorise. See
[FALLBACK.md](FALLBACK.md) Level 0.

This is a decision, not a gap.

## Validation status

Both paths were exercised natively before any Cartesi tooling existed:

- **Positive:** 3 runs, 3 identical SHA-256 digests, `RESULT: MATCH`.
- **Negative:** hash seed deliberately re-randomised → `RESULT: MISMATCH`,
  localized to one line, `sections affected: D3 (1)`, exit code 1. Section C's
  summations stayed bit-identical throughout, which is the diagnosis working —
  a hash-order problem correctly distinguished from a floating-point one.

Both digests and the diff are recorded in `determinism-log.txt`.
