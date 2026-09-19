#!/usr/bin/env python3
"""
surface_payload.py -- emits the full LGD surface as a canonical, byte-stable
payload, using the same discipline as probe.py.

Every float via float.hex(). Payload bounded by the same delimiters the
machine runner extracts on. Metadata to stderr only, never into the payload.

The bootstrap seed and resample count are BOTH in the payload header, so the
digest covers them and a reader recomputing intervals knows exactly what to
reproduce. Generator: Python stdlib random.Random (Mersenne Twister), seeded
explicitly. Reproducibility here rests on determinism, not on generator
quality.
"""
import argparse, sys, time, platform
import surface as S

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=10000)
    ap.add_argument("--data", default="dataset-baddebt-usdc.tsv")
    a = ap.parse_args()
    S.BOOT = a.boot

    t0 = time.perf_counter()
    out = sys.stdout.buffer
    def raw(s): out.write(s.encode("ascii")); out.write(b"\n")

    ev = S.load(a.data)
    raw("# surface-version\t1")
    raw("# boot-resamples\t%d" % a.boot)
    raw("# boot-seed\t%d" % S.SEED)
    raw("# boot-generator\tpython-random-MersenneTwister")
    raw("# threshold-raw\t%d" % S.THRESHOLD)
    raw("# prior-lgd\t%s" % float(S.PRIOR_LGD).hex())
    raw("# pseudo-n\t%d" % S.PSEUDO_N)
    raw("# events\t%d" % len(ev))

    now = max(e["ts"] for e in ev)
    wins = [("W1", ev), ("W2", [e for e in ev if e["ts"] >= now - 365 * 86400])]
    n = 0
    for wn, wev in wins:
        for ch in (1, 8453):
            sub = [e for e in wev if e["chain"] == ch]
            if not sub:
                continue
            for gr in ("CHAIN", "MARKET", "EVENT"):
                for tr in ("T1", "T2", "T3", "T4", "T5"):
                    p, k, lo, hi = S.cell(sub, gr, tr, chain=ch)
                    lbl = "%s.%d.%s.%s" % (wn, ch, gr, tr)
                    raw("%s.point\tF\t%s" % (lbl, float(p).hex()))
                    raw("%s.n\tI\t%d" % (lbl, k))
                    raw("%s.lo\tF\t%s" % (lbl, float(lo).hex()))
                    raw("%s.hi\tF\t%s" % (lbl, float(hi).hex()))
                    n += 4
    raw("# records\t%d" % n)
    out.flush()

    el = time.perf_counter() - t0
    w = sys.stderr.write
    w("surface_payload metadata -- NOT part of the digest\n")
    w("python   : %s\n" % sys.version.replace("\n", " "))
    w("machine  : %s\n" % platform.machine())
    w("records  : %d\n" % n)
    w("elapsed  : %.6f\n" % el)

if __name__ == "__main__":
    main()
