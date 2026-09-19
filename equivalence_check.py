#!/usr/bin/env python3
"""
equivalence_check.py -- proves the fast bootstrap is output-preserving.

Runs the full surface payload twice, once through the reference
implementation (FAST=False) and once through the optimised path (FAST=True),
across several seeds and resample counts, and requires byte-identical output
at every configuration.

One configuration passing is compatible with an indexing bug that happens to
cancel there. Several are not.
"""
import hashlib, importlib, io, sys
import surface as S


def payload(boot, seed, fast):
    S.BOOT = boot; S.SEED = seed; S.FAST = fast
    ev = S.load()
    buf = io.StringIO()
    now = max(e["ts"] for e in ev)
    wins = [("W1", ev), ("W2", [e for e in ev if e["ts"] >= now - 365 * 86400])]
    for wn, wev in wins:
        for ch in (1, 8453):
            sub = [e for e in wev if e["chain"] == ch]
            if not sub:
                continue
            for gr in ("CHAIN", "MARKET", "EVENT"):
                for tr in ("T1", "T2", "T3", "T4", "T5"):
                    p, k, lo, hi = S.cell(sub, gr, tr, chain=ch)
                    buf.write("%s.%d.%s.%s\t%s\t%d\t%s\t%s\n" %
                              (wn, ch, gr, tr, float(p).hex(), k,
                               float(lo).hex(), float(hi).hex()))
    return hashlib.sha256(buf.getvalue().encode()).hexdigest()


def main():
    configs = [(50, 20260918), (100, 20260918), (200, 20260918),
               (100, 1), (100, 424242), (200, 7777777)]
    print(f"  {'boot':>6} {'seed':>10}  {'reference':<18} {'fast':<18} match")
    allok = True
    for boot, seed in configs:
        a = payload(boot, seed, False)
        b = payload(boot, seed, True)
        ok = (a == b); allok &= ok
        print(f"  {boot:>6} {seed:>10}  {a[:16]:<18} {b[:16]:<18} {'YES' if ok else 'NO  <-- FAIL'}")
    print()
    print("EQUIVALENCE: " + ("PROVEN across all configurations" if allok
                             else "FAILED -- do not bake, fall back to --boot 100"))
    return 0 if allok else 1


if __name__ == "__main__":
    sys.exit(main())
