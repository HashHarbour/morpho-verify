# Environment provenance

Everything a day-10 re-runner needs, and the source for the write-up's
reproduction section. Recorded 2026-09-18.

Values here are pinned facts, not descriptions. If any of them change, the
experiment changed.

## Toolchain

| Component | Version | Notes |
|---|---|---|
| Cartesi CLI | `2.0.0-alpha.35` | the **V2** line — see "CLI version" below |
| Docker Engine | 29.8.0 | |
| Docker Compose | 5.5.1 | |
| Docker Buildx | 0.37.0 | |
| RISC-V support | `linux/riscv64` | confirmed by `cartesi doctor` |
| Node | v24.21.0 | via nvm 0.40.7, `lts/*` |
| npm | 11.19.0 | |
| uv | 0.12.17 | supplies the native baseline interpreter |

## CLI version — why alpha, not latest

The published docs give `npm i -g @cartesi/cli` with no tag. That resolves to
the **V1** CLI. Settled empirically from registry publish dates:

```
latest -> 1.5.0             published 2024-10-17
alpha  -> 2.0.0-alpha.35    published 2026-06-24
```

`latest` is not merely behind; it is abandoned in place. All eight most recent
publishes are on the 2.0 alpha line. Install with:

```
npm i -g @cartesi/cli@alpha
```

Ground truth for which line you are on is the port in `cartesi run` output:
**6751 = V2**, 8080 = V1.

## Base image — pinned by digest

The stock template pins apt by snapshot date and guest tools by SHA-256, then
leaves the base image on a **mutable tag**. A routine security rebuild would
repoint it, and a re-runner would silently build a different machine — no
error, just a quiet failure to be the same experiment.

Pinned in the Dockerfile as:

```dockerfile
FROM --platform=linux/riscv64 cartesi/python:3.13.2-slim-noble@sha256:85a4ea4c3b3f0159b4ffce8ead19a0426d061f12693c1226795fbb67ce50b436 AS base
```

| Ref | Digest |
|---|---|
| index (pinned) | `sha256:85a4ea4c3b3f0159b4ffce8ead19a0426d061f12693c1226795fbb67ce50b436` |
| linux/riscv64 manifest | `sha256:9778378f56b33d29e1a4fb9ffac1b9da0a9d2829f47d22d6f0c73c17ab00e04f` |

The tag carries exactly one real platform (riscv64) plus an attestation
manifest. **There is no amd64 variant** — see trap #8.

Template pins carried through unchanged:

```
APT_UPDATE_SNAPSHOT            20260907T030400Z
MACHINE_GUEST_TOOLS_VERSION    0.18.0
MACHINE_GUEST_TOOLS_SHA256SUM  204d4260defd68e11b957ae1f1b511b6c2c74345c918748be06f592733b72dcd
```

## Built machine — stock template, unmodified

```
machine hash   6601f55ec3e35ff64381f12a23f9bbe8785d0a8613256b12dd09e5a62ae32d4d
boot cycles    4,104,636,362        (stock dapp, boot to first yield)
root.ext2      139,259,904 bytes
build wall     726.52 s  (12:06.52)
```

The machine hash should reproduce on a re-run from the same pinned inputs. It
is not yet confirmed stable across a teardown and rebuild — that is day 2.

### Boot cost — corrected on day 2

The 4.1 billion figure above is the **stock rollups dapp**: boot plus standing
up the HTTP dispatcher and the dapp lifecycle. A plain compute invocation that
boots, runs a command and halts is far cheaper:

```
stock rollups dapp     4,104,636,362 cycles
one-shot command         164,253,529 cycles     <- 25x cheaper
```

**Design decision, unchanged but downgraded from constraint to optimisation:**
the parameter sweep computes the whole surface inside a **single machine
invocation** producing **one output payload**. One digest covering one complete
experiment beats N digests a re-runner has to reassemble. But at 164 M cycles
the penalty for getting it wrong is 25x smaller than first estimated.

## Day 2 — determinism gate

```
machine under test   3ba23c13384c31bcd2c931a130f8423ca87ebe2649a9dffa3957482fe74e2c61
                     (stock template + probe.py baked in, base pinned by digest)
payload digest       ee1eb51724efe4371b96ce19bd99a388710ed924a55db6353d9cbafe54a52321
                     4 runs, spanning a full teardown -- all identical
cold rebuild         882.90 s, from 0 docker images, base re-pulled by digest
                     machine hash reproduced EXACTLY
```

The build is reproducible, not merely the execution. Full evidence in
[determinism-log-machine.txt](determinism-log-machine.txt).

### Overhead, measured

```
native amd64 (uv 3.13.2)   0.568 s    host real
machine                   75-89 s     host wall
machine emulated clock     8.859712 s  <- NOT host time; trap #10
compute overhead          ~125x
end-to-end                ~132x
```

**Not transferable to the model.** Measured on a probe deliberately built to be
arithmetic-heavy — a 100k-element summation and three full sorts. The model is
78,000 independent closed-form evaluations with no large reductions. Re-measure
against the real workload before quoting an overhead figure for it.

### Native vs machine

5 records differ out of 834, all exactly 1 ULP, all in the erf family
(4x `B.erfc`, 1x `B.ncdf`). Sections A, C and E — transcendental chains, every
summation ordering, matrix reduction — are bit-identical across architectures.
Expected behaviour, not a defect: glibc's erf is not correctly rounded.

## Native baseline interpreter

Baseline on **uv's CPython 3.13.2** (`python-build-standalone`), matching the
machine's interpreter version.

Do **not** baseline on Ubuntu's system `python3`. It produces an identical
digest but runs 1.47x slower, which deflates the overhead ratio by ~32% — in
the flattering direction. See trap #9.

```
probe.py payload digest, amd64 / glibc, --sum-n 100000, no numpy:
4d0229b16d20b98cca2f17de661f7353625efc23be8379ec99f952363e197419

identical across: uv 3.12.3, uv 3.13.2, Ubuntu system 3.12.3
best internal elapsed: uv 3.13.2  0.568 s
```

Residual, unquantifiable: the machine's Python is a third build with its own
compile flags, not replicable natively. The ratio carries an unquantified
build-flag component.

## Host

```
CPU        Intel Core i7-1065G7, 4 cores / 8 threads
OS         Windows 11 Home 26200, WSL2 Ubuntu 24.04.5 LTS
kernel     6.18.33.2-microsoft-standard-WSL2
```

## Disk

```
session start   47.1 GB free
after build     33.0 GB free      (14.1 GB total; ~6 GB the build itself)
```

**Floor: 20 GB.** Below that, `docker system prune` and compact the WSL2 vhdx
before running anything else. Deleting inside WSL does not shrink the vhdx on
the Windows side.

## Status

Days 1 and 2 complete. All four exit criteria met:

1. Two independent in-machine runs, identical digests.
2. Third and fourth runs after full teardown and rebuild, identical — and the
   machine hash itself reproduced from zero images.
3. Emulation overhead measured: ~125x compute, ~132x end-to-end.
4. Working numeric path confirmed in-machine (`math.erf`, subnormals intact).
   numpy not attempted by design — zero riscv64 wheels published.

**What is established:** the same machine image produces the same payload
digest across independent runs and across a full teardown and rebuild, on this
host.

**What is not:** reproduction on hardware that is not this laptop. Three
matching runs on one machine validates the harness. The determinism *finding*
does not exist until day 10, when someone else's hardware reproduces it. That
is the first real test of the central claim; everything before it is setup.
