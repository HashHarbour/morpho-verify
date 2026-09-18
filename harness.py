#!/usr/bin/env python3
"""
harness.py -- runs probe.py N times, digests each payload, compares.

The execution target is pluggable. "native" is preconfigured and needs nothing
but a Python interpreter, so the whole harness -- serializer, comparison, and
SHA-256 logic -- can be debugged before Docker or Cartesi exist. Porting to the
machine is then a matter of swapping the command, not debugging two things at
once.

Usage:

    # validate the harness itself, natively
    python3 harness.py --runs 2 --label "native baseline"

    # same thing with timing you intend to quote as the native side of the ratio
    python3 harness.py --runs 5 --label "native baseline"

    # once the CLI works, point it at the machine
    python3 harness.py --target cmd --cmd "<machine invocation>" \\
        --runs 2 --label "in-machine"

    # day 2, run 3: after a full container teardown and rebuild
    python3 harness.py --target cmd --cmd "<machine invocation>" \\
        --runs 1 --label "post-teardown"

Writes per-run payloads, a plain-text log with the digests visible, and a
summary.json for scripted ratio computation.
"""

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time

# Environment hygiene. Each of these closes off a specific source of false
# non-determinism; see README for what each one prevents. They are applied to
# the child process, not to this harness.
HYGIENE = {
    # Set iteration order is randomised per process without this.
    "PYTHONHASHSEED": "0",
    # If numpy (or anything BLAS-backed) is present, multithreaded reductions
    # sum in a nondeterministic order and change the last bits.
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    # Locale can affect string collation and number formatting.
    "LC_ALL": "C",
    "LANG": "C",
    # Defensive: nothing in the payload reads the clock, but this removes a
    # whole class of surprise if that ever changes.
    "TZ": "UTC",
    # Keeps stray .pyc writes out of the working tree.
    "PYTHONDONTWRITEBYTECODE": "1",
}


def build_env():
    env = dict(os.environ)
    env.update(HYGIENE)
    return env


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_once(cmd, env, timeout):
    """Execute the target once. Captures stdout as raw bytes -- never text --
    so no newline translation or decoding can alter the digest."""
    started = time.perf_counter()
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - started
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def decode_record(line):
    """Render a payload line for human reading, expanding float hex to decimal.

    Only used when reporting a mismatch. The payload itself stays hex-only.
    """
    text = line.decode("ascii", "replace")
    parts = text.split("\t")
    if len(parts) == 3 and parts[1] == "F":
        try:
            return "%s = %s  (%r)" % (parts[0], parts[2], float.fromhex(parts[2]))
        except ValueError:
            pass
    return text


def diff_payloads(ref, other, limit=25):
    """Report which named operations diverged.

    A mismatch is informative: the label on the differing line tells you which
    operation is unstable. Look for the pattern --
      only C.* moved            -> unordered/threaded reduction; use fsum
      only D3.hash_order_canary -> PYTHONHASHSEED was not 0
      B.* moved                 -> libm disagreement; the serious case
    """
    ref_lines = ref.split(b"\n")
    other_lines = other.split(b"\n")
    out = []

    if len(ref_lines) != len(other_lines):
        out.append("line count differs: %d vs %d"
                   % (len(ref_lines), len(other_lines)))

    shown = 0
    total = 0
    for i in range(min(len(ref_lines), len(other_lines))):
        if ref_lines[i] != other_lines[i]:
            total += 1
            if shown < limit:
                out.append("  line %d:" % (i + 1))
                out.append("    run1: %s" % decode_record(ref_lines[i]))
                out.append("    runN: %s" % decode_record(other_lines[i]))
                shown += 1
    if total > shown:
        out.append("  ... and %d more differing lines" % (total - shown))
    if total == 0 and not out:
        out.append("  (payloads differ only in trailing bytes)")
    else:
        out.insert(0, "  %d differing line(s)" % total)
    return "\n".join(out)


def summarise_labels(ref, other):
    """Collapse differing lines to their section prefixes, for a fast read."""
    ref_lines = ref.split(b"\n")
    other_lines = other.split(b"\n")
    sections = {}
    for i in range(min(len(ref_lines), len(other_lines))):
        if ref_lines[i] != other_lines[i]:
            label = ref_lines[i].split(b"\t")[0].decode("ascii", "replace")
            key = label.split(".")[0] if "." in label else label
            sections[key] = sections.get(key, 0) + 1
    return sections


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", choices=["native", "cmd"], default="native",
                    help="native runs probe.py with this interpreter; "
                         "cmd runs an arbitrary --cmd string")
    ap.add_argument("--cmd",
                    help="command to run when --target cmd. Must emit the "
                         "probe payload on stdout and nothing else.")
    ap.add_argument("--probe", default="probe.py",
                    help="path to probe.py (default: probe.py)")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the native target")
    ap.add_argument("--runs", type=int, default=2)
    ap.add_argument("--sum-n", type=int, default=100000)
    ap.add_argument("--with-numpy", action="store_true")
    ap.add_argument("--label", default="",
                    help="free text recorded in the log, e.g. 'post-teardown'")
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--log", default="determinism-log.txt")
    ap.add_argument("--timeout", type=float, default=3600.0)
    args = ap.parse_args(argv)

    if args.target == "cmd":
        if not args.cmd:
            ap.error("--target cmd requires --cmd")
        cmd = shlex.split(args.cmd)
        probe_digest = "n/a (external command)"
    else:
        if not os.path.exists(args.probe):
            ap.error("probe not found: %s" % args.probe)
        cmd = [args.python, args.probe, "--sum-n", str(args.sum_n)]
        if args.with_numpy:
            cmd.append("--with-numpy")
        # Provenance: proves every run executed the same script.
        probe_digest = sha256_file(args.probe)

    os.makedirs(args.outdir, exist_ok=True)
    env = build_env()

    print("target   : %s" % args.target)
    print("command  : %s" % " ".join(shlex.quote(c) for c in cmd))
    print("runs     : %d" % args.runs)
    print("probe    : sha256 %s" % probe_digest)
    print()

    results = []
    for n in range(1, args.runs + 1):
        try:
            code, stdout, stderr, elapsed = run_once(cmd, env, args.timeout)
        except subprocess.TimeoutExpired:
            print("run %d: TIMEOUT after %.0fs" % (n, args.timeout))
            results.append({"run": n, "error": "timeout"})
            continue
        except (OSError, FileNotFoundError) as exc:
            print("run %d: FAILED to execute: %s" % (n, exc))
            results.append({"run": n, "error": str(exc)})
            continue

        digest = sha256_bytes(stdout)
        base = os.path.join(args.outdir, "run_%03d" % n)
        with open(base + ".stdout", "wb") as fh:
            fh.write(stdout)
        with open(base + ".stderr", "wb") as fh:
            fh.write(stderr)

        results.append({
            "run": n,
            "digest": digest,
            "bytes": len(stdout),
            "wall_seconds": elapsed,
            "exit_code": code,
            "stdout_path": base + ".stdout",
        })
        print("run %d: digest %s  bytes %d  wall %.3fs  exit %d"
              % (n, digest, len(stdout), elapsed, code))
        if code != 0:
            print("       !! non-zero exit; stderr tail:")
            for line in stderr.decode("utf-8", "replace").splitlines()[-10:]:
                print("       | %s" % line)

    ok = [r for r in results if "digest" in r and r["exit_code"] == 0]
    digests = set(r["digest"] for r in ok)
    matched = len(digests) == 1 and len(ok) == args.runs
    verdict = "MATCH" if matched else "MISMATCH"
    if not ok:
        verdict = "NO SUCCESSFUL RUNS"

    print()
    print("RESULT: %s  (%d/%d successful runs, %d distinct digest(s))"
          % (verdict, len(ok), args.runs, len(digests)))

    diff_text = ""
    if len(digests) > 1:
        ref = open(ok[0]["stdout_path"], "rb").read()
        for r in ok[1:]:
            if r["digest"] != ok[0]["digest"]:
                other = open(r["stdout_path"], "rb").read()
                sections = summarise_labels(ref, other)
                diff_text = ("run 1 vs run %d\n" % r["run"]
                             + "  sections affected: %s\n"
                               % (", ".join("%s (%d)" % (k, v)
                                            for k, v in sorted(sections.items()))
                                  or "none")
                             + diff_payloads(ref, other))
                print()
                print(diff_text)
                break

    walls = sorted(r["wall_seconds"] for r in ok)
    median = walls[len(walls) // 2] if walls else None

    # Plain-text log with the digests visible -- this is the day-13 screenshot.
    with open(args.log, "a", encoding="utf-8") as fh:
        fh.write("=" * 68 + "\n")
        fh.write("Cartesi determinism probe -- run record\n")
        fh.write("label        : %s\n" % (args.label or "(none)"))
        fh.write("target       : %s\n" % args.target)
        fh.write("command      : %s\n" % " ".join(shlex.quote(c) for c in cmd))
        fh.write("runs         : %d\n" % args.runs)
        fh.write("probe sha256 : %s\n" % probe_digest)
        fh.write("hygiene      : %s\n"
                 % " ".join("%s=%s" % kv for kv in sorted(HYGIENE.items())))
        fh.write("-" * 68 + "\n")
        for r in results:
            if "digest" in r:
                fh.write("run %-3d digest %s  bytes %-8d wall %8.3fs  exit %d\n"
                         % (r["run"], r["digest"], r["bytes"],
                            r["wall_seconds"], r["exit_code"]))
            else:
                fh.write("run %-3d ERROR %s\n" % (r["run"], r.get("error")))
        fh.write("-" * 68 + "\n")
        fh.write("RESULT: %s  (%d/%d successful, %d distinct digest(s))\n"
                 % (verdict, len(ok), args.runs, len(digests)))
        if median is not None:
            fh.write("median wall  : %.3fs\n" % median)
        if diff_text:
            fh.write("\n" + diff_text + "\n")
        fh.write("=" * 68 + "\n\n")

    with open(os.path.join(args.outdir, "summary.json"), "w",
              encoding="utf-8") as fh:
        json.dump({
            "label": args.label,
            "target": args.target,
            "command": cmd,
            "probe_sha256": probe_digest,
            "hygiene": HYGIENE,
            "runs": results,
            "distinct_digests": sorted(digests),
            "verdict": verdict,
            "median_wall_seconds": median,
        }, fh, indent=2)

    print("log      : %s" % args.log)
    print("summary  : %s" % os.path.join(args.outdir, "summary.json"))
    return 0 if matched else 1


if __name__ == "__main__":
    sys.exit(main())
