# REPRODUCE.md

Reproduce the verified computation in about twenty minutes. No context about
this project is needed to run it.

## What you are checking

That the machine image built from pinned inputs, on **your** hardware, produces
the same machine hash and the same payload digest as it did on mine.

```
  dataset sha256   54e7610b891365ea28d000f7c9521ad7251c2e51b9c194115c548f7230da5028
  machine hash     7ab6f269e574d84588b9175991d5f6d2e0531b46e8103d696e4d0831a7c4ac79
  payload sha256   dbdcbb34b4eca122b621c5f802c8526221013add7ed2439ca606b395c53833de
```

## Prerequisites

```
  Docker            running, with RISC-V support (buildx)
  Cartesi CLI       2.0.0-alpha.35   <-- MUST be pinned, see below
  disk              ~6 GB free for the build
  time              ~2 min build, ~19 min run
```

**The CLI version is load-bearing.** Installing with no tag resolves to
`latest`, which is **1.5.0** -- a V1 release from October 2024. The CLI builds
the machine, so an unpinned install guarantees a mismatch that tells you
nothing. Install exactly:

```bash
npm i -g @cartesi/cli@2.0.0-alpha.35
cartesi --version        # must print 2.0.0-alpha.35
```

Verify Docker is ready:

```bash
cartesi doctor           # must report RISC-V support linux/riscv64
```

## Steps

```bash
git clone <REPO_URL> && cd morpho-verify
sha256sum dataset-baddebt-usdc.tsv
```

Expect `54e7610b...`. **If this differs, stop** -- your checkout is not the
same input and nothing downstream is comparable.

Build the machine. The base image is pinned by digest in the Dockerfile, so
this fetches exactly the same rootfs I used:

```bash
cartesi build
```

The build prints the machine hash on its final line, as `<cycles>: <hash>`.
Expect `7ab6f269...`.

Run the surface inside the machine:

```bash
docker run --rm --volume "$PWD/.cartesi:/work" --workdir /work   --user "$(id -u):$(id -g)" cartesi/sdk:0.12.0-alpha.41   cartesi-machine --flash-drive=label:root,data_filename:root.ext2     --ram-length=128Mi   -- "cd /opt/cartesi/dapp && env PYTHONHASHSEED=0 OMP_NUM_THREADS=1       OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LC_ALL=C LANG=C TZ=UTC       python3 surface_payload.py --boot 100" > run.txt 2>&1
```

Extract the payload and hash it. The payload is bounded by its own delimiters,
because stdout and stderr share one console inside the machine:

```bash
sed -n '/^# surface-version/,/^# records/p' run.txt > payload.txt
sha256sum payload.txt
```

Expect `dbdcbb34...`.

**Do not use `cartesi shell`.** It forces a TTY, which injects carriage returns
into the payload and changes the digest.

## Run parameters that are part of the claim

```
  --boot 100          bootstrap resamples
  seed 20260918       fixed in surface.py
  generator           python stdlib random.Random (Mersenne Twister)
```

Changing any of these changes the payload digest legitimately. The resample
count is deliberately low so this run takes twenty minutes rather than thirteen
hours. Point estimates are identical at every resample count tested; only
interval widths change.

## Triage -- what your result means

| Symptom | Meaning |
|---|---|
| Dataset hash differs | Checkout differs. Stop; nothing downstream is comparable. |
| Machine hash differs, payload matches | The build is host-sensitive, the computation is not. A weaker claim, and one this project pre-registered as publishable rather than a failure. |
| Machine hash matches, payload differs | Execution non-determinism. **This is the serious one** and would contradict the central claim. |
| Both match | The claim holds on your hardware. |

## Please report either way

Send **all three hashes**, plus:

```
  host OS and version
  host architecture   (x86-64, arm64 / Apple Silicon, ...)
  docker --version
  cartesi --version
```

**A failed reproduction with good diagnostics is worth more to this work than a
successful one with none.** Apple Silicon results are especially wanted: a
different host architecture reproducing a riscv64 machine hash is a far harder
test than another x86-64 Linux box.
