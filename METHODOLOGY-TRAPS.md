# Methodology traps caught

A running list. Each entry: what the trap was, what it would have done to a
published number, and how it was caught. This is a section of the day-13
write-up — the argument rests on measurement honesty, and a list of confounds
caught before they shipped is more persuasive than the headline result.

Kept in commit order. Append, do not rewrite.

---

## 1. Windows-native vs WSL-native baseline

**Day 1.** The plan said "run the same script natively on your laptop." The
Cartesi machine runs inside WSL2, so the native side of the ratio has to be
measured in WSL2 Ubuntu as well.

**What it would have done:** folded a WSL filesystem and syscall penalty into a
figure published as *emulation* overhead. The sign is not knowable in advance —
that is the problem with it. An uncontrolled confound inside a headline number
is not rescued by happening to point the convenient way.

**Caught by:** noticing the Cartesi docs require Windows work to happen inside
WSL2 Ubuntu, which means "my laptop" and "the host running the emulator" are
two different environments.

**Resolution:** native side measured in WSL2 Ubuntu. Non-negotiable.

---

## 2. Harness wall time vs probe internal elapsed

**Day 1.** Measured on this laptop, Windows native, `--sum-n 100000`:

```
probe.py internal elapsed : 0.43 s
harness measured wall     : 2.63 s
```

**83% of wall time was interpreter startup and process spawn**, not
computation. Inside the machine the equivalent fixed cost is a full RISC-V
Linux kernel boot, which is far larger.

**What it would have done:** *inflated* the reported emulation overhead, and
badly. Boot time would have been attributed to arithmetic. The direction is
known and it is the flattering one — it would have made the emulator look
slower and the scope budget look tighter than reality, which in turn would have
justified shrinking the model for no real reason.

**Caught by:** the harness wall time (2.6 s) not matching the intuition that
100k float ops should take well under a second, then checking the probe's own
stderr timing line.

**Resolution:** two numbers, separately labelled.
- **compute ratio** = emulated ÷ native `elapsed_seconds`
- **fixed startup cost** = wall − `elapsed_seconds`

Only the compute ratio informs model scope.

---

## 3. Reproducibility is not correctness

**Day 1.** The naive standard normal CDF, `0.5*(1+erf(x/√2))`, suffers
catastrophic cancellation below roughly x = −5: `erf` approaches −1 and the
`1 + erf` subtraction discards most of the significant digits.

**What it would have done:** nothing to any performance number — and that is
exactly the point. **It would have passed the determinism gate.** Bit-identical
across every run, three for three, and numerically wrong in the left tail.
The probe would have certified a wrong answer as verified.

This matters more here than in a generic model, because the markets are
overwhelmingly well-collateralized — the prior art found the largest markets
recorded under one cent of bad debt. Default probability therefore sits deep in
the left tail, precisely where the naive form has already thrown its precision
away.

**Caught by:** writing section B to emit `B.tail_naive[*]` and `B.tail_erfc[*]`
side by side rather than picking one formulation and trusting it.

**Resolution:** `0.5*erfc(-x/√2)` throughout the model. Non-negotiable. See
`FALLBACK.md`.

**Generalisation, and the reason day 8 outputs a sensitivity surface rather
than a number:** reproducibility and correctness are orthogonal. A verifiable
computation pipeline certifies *that the same inputs produced the same
outputs*, never *that the outputs mean what you claim*. Any attestation
architecture that conflates the two is making an unearned claim — the same
objection raised against the imaging attestation and the risk-curator pitch. It
applies to this project's own tooling with no discount.

---

## 4. Claim scope: three runs on one laptop is not a determinism finding

**Day 1, expectation set before day 2 so the result is not misread.**

Native and emulated digests will very likely **not** match. glibc's `erf` is not
correctly rounded, and x86-64 and riscv64 libm implementations can differ in
the last bits. **This is expected and is not a failure.**

**What it would have done:** treating a native ≠ emulated mismatch as a defect
would have triggered a retreat down the fallback ladder — plausibly all the way
to Level 3, `decimal` with a hand-written `erf`, budgeted at a day of work — to
fix a problem that does not exist.

**The claim actually being made is emulated-to-emulated, across different
hosts.** Three identical runs on one laptop validates the harness. It is not
yet a determinism finding. The finding exists only once the same image produces
the same digest on hardware that is not mine.

**Consequence:** day 10's independent re-run is not a formality. It is the first
time the central claim is tested at all. Everything before it is setup.

---

## 5. A gate that cannot fail is not a gate

**Day 1.** Not a confound in a number, but the same species of error: trusting
an instrument that was never shown capable of reporting bad news.

**Caught by:** deliberately re-randomising `PYTHONHASHSEED` and confirming the
harness reported `MISMATCH`, localized it to one line, named the section
(`D3 (1)`), and exited non-zero — while section C's summations stayed
bit-identical, correctly distinguishing a hash-order problem from a
floating-point one.

**Resolution:** both the positive and negative paths are recorded in
`determinism-log.txt` and `negative-test-log.txt`. Any future change to the
probe or harness re-runs both.

---

## 6. Line-ending conversion silently breaking the evidence-to-artifact hash chain

**Day 1.** `determinism-log.txt` records `probe sha256 : 868bb295926daf4da115...`
— the digest of the exact `probe.py` that produced the logged results. That
recorded digest is what links the evidence to the artifact, and it is the first
thing a skeptical reader checks.

The staged `probe.py` hashes to `868bb295926daf4d...`. It matches. But it
matches **only because `probe.py` happens to be LF-only** (`CR=0`). Had it been
CRLF — as the two log files were, because `harness.py` opens them in text mode
and Windows translated — copying the repo from Windows into WSL would have
rewritten every line ending and changed the file's hash.

**What it would have done:** silently severed the link between the committed
probe and the digest recorded in its own evidence log. No error, no warning. The
log would claim provenance for a file that no longer existed in that form, and
the discrepancy would surface months later, in front of exactly the reader it
would most damage the argument with.

**Caught by:** hashing every staged file and comparing against the digest
already recorded inside the log, rather than assuming the copy was lossless.

**Resolution:** `.gitattributes` pins `* text=auto eol=lf` so the repo
normalises on commit. Verify after any cross-platform move that the staged
`probe.py` still hashes to the value recorded in `determinism-log.txt`. It is a
one-line check and it is the check a skeptic runs first.

**Related decision:** `harness.py` was **not** patched to write LF logs before
the first commit, despite that being a one-line fix. The committed harness must
be byte-identical to the one that produced the logs. Matching what actually ran
beats a cosmetic improvement — for this artifact that is not a tradeoff, it is
the correct answer. The fix lands in a later commit whose message says what
changed and why, so the history shows the harness was frozen before the logs
existed.

---

## 7. Platform config travelling with the repo

**Day 1.** Provenance rather than measurement, but the same failure shape:
silent, no error, discovered too late.

`git init` was run on the Windows side, so Git for Windows wrote its own
defaults into `.git/config` — the file that travels with the repository:

```
core.filemode  = false     # wrong on ext4; exec bit stops being tracked
core.symlinks  = false     # Windows limitation, meaningless on Linux
core.ignorecase = true     # actively dangerous: WSL ext4 is case-sensitive
```

Separately, Git for Windows sets `credential.helper = manager` in its **system**
config. That one does not travel with the repo — but it is live on the Windows
machine, and an HTTPS push from there would invoke Windows Credential Manager,
where a real, non-pseudonymous GitHub session may already be stored.

**What it would have done:** `core.ignorecase=true` on a case-sensitive
filesystem lets git conflate or miss paths differing only in case. The
credential helper is the worse one — it would have quietly authenticated as the
wrong identity on an artifact whose entire point is a clean, separable
provenance story.

**Caught by:** reading the raw `.git/config` before the copy instead of trusting
`git init` to have written something platform-neutral.

**Resolution:** the three `core.*` entries unset; an empty
`credential.helper` added locally, which resets the inherited helper list so
none runs for this repo. Push only from WSL, over SSH, with a key dedicated to
this account. Re-run `git config --local --list` after any move to a new
machine.

---

## 8. The native baseline and the machine run different Python versions

**Day 1.** The plan said to baseline against "python3 on your laptop." Once the
machine image was inspected, that turned out to mean **3.12.3** (Ubuntu's)
against **3.13.2** (the machine's, from
`cartesi/python:3.13.2-slim-noble`). Two interpreter versions, compared as
though the only difference were emulation.

**What it would have done:** folded interpreter-version differences into a
number published as architecture/emulation overhead. Same species as traps #1
and #2.

**The clean fix was unavailable.** Running the baseline in the same image on
`linux/amd64` would have made architecture the sole variable, but
`docker buildx imagetools inspect` shows the tag carries exactly one real
platform:

```
linux/riscv64     sha256:9778378f56b33d29e1a4fb9ffac1b9da0a9d2829f47d22d6f0c73c17ab00e04f
unknown/unknown   (attestation-manifest, not a platform)
```

There is no amd64 variant. So **architecture is not isolated as the sole
variable**, and that limitation is stated rather than papered over. "We could
not fully isolate architecture" is more credible than pretending otherwise.

**Measured instead of declared.** Three interpreters, same probe, hygiene vars
set, three runs each — all bit-identical:

```
uv  3.12.3   4d0229b16d20b98cca2f17de661f7353625efc23be8379ec99f952363e197419
uv  3.13.2   4d0229b16d20b98cca2f17de661f7353625efc23be8379ec99f952363e197419
sys 3.12.3   4d0229b16d20b98cca2f17de661f7353625efc23be8379ec99f952363e197419
```

Both uv builds come from the same toolchain (`python-build-standalone`), so the
uv-vs-uv comparison isolates version and the uv-vs-system comparison isolates
build toolchain.

**Result: the numerical confound is bounded at zero, measured.** Interpreter
version contributes nothing to the payload; neither does build toolchain. The
remaining native-vs-emulated difference is attributable to architecture and
libm. That converts a caveat into a measurement.

**Residual, unquantifiable:** the machine's Python is a *third* build, compiled
into Cartesi's image with its own flags, which cannot be replicated natively.
The ratio carries an unquantified build-flag component. Say so.

---

## 9. Interpreter build flags change timing without changing the digest

**Day 1.** The trap #8 experiment was designed to bound a numerical confound. It
bounded that at zero and surfaced a larger one in the timings:

```
uv  3.12.3   best 0.576 s
uv  3.13.2   best 0.568 s
sys 3.12.3   best 0.845 s     <- 1.47x slower, identical digest
```

Identical work, identical output bytes, 47% slower. Ubuntu's stock distro build
against uv's PGO/LTO-optimised `python-build-standalone`.

**What it would have done, and the direction matters:** Ubuntu's `python3` as
the baseline inflates the denominator, which **deflates** the emulation
overhead ratio by roughly 32%. Against a 30 s emulated run: **35.5x** using
system Python versus **52.1x** using uv's.

**The lazy choice produces the flattering number.** That is the dangerous
direction — confounds that flatter you are the ones a hostile reader finds
first and the ones that cost most when found. A digest-based determinism check
cannot catch this at all, because the digest is identical either way. Only the
timing moves.

**Resolution:** baseline on **uv 3.13.2** — matches the machine's interpreter
version, documented reproducible build. Record which interpreter build produced
every published timing. State the residual build-flag component (trap #8).

---

## Appendix: tooling traps (not measurement confounds)

**A1. Cartesi CLI version.** The live docs give `npm i -g @cartesi/cli` with no
version tag, but the npm registry's `latest` tag resolves to **1.5.0**, the V1
CLI, while the surrounding 2.0 documentation describes V2 behaviour (port 6751,
machine-hash line). The 2.0 installation page is a stub reading "TODO: This is
blank."

Would have cost days of debugging a version mismatch that presents as
inexplicable command failures. Resolve empirically with
`npm view @cartesi/cli dist-tags`, and treat the port in `cartesi run` output as
ground truth: 6751 = V2, 8080 = V1.

Not a blocker for the determinism gate either way — the probe is pure stdlib and
CLI-version-agnostic.
