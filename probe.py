#!/usr/bin/env python3
"""
probe.py -- determinism probe for the Cartesi RISC-V machine.

Emits a canonical, byte-stable payload on STDOUT. Every float is written via
float.hex(), so comparison is exact at the bit level. Rounded decimal output
can hide a divergence in the last few ulps, which is exactly the divergence
that matters here.

Diagnostic metadata (interpreter version, platform, timing) goes to STDERR on
purpose. It must never enter the stdout payload: if it did, a native run and an
emulated run could never produce the same digest, and we would lose the ability
to compare across execution targets.

The payload is pure stdlib. The numpy section is opt-in via --with-numpy and is
OFF by default, so the default payload is comparable between any two
environments regardless of whether numpy is installed in either.

Exercises the operations the Black-Cox closed form actually uses:
  A  exp / log / sqrt chains
  B  erf across a range including saturated tails and subnormals
  C  large float summation where accumulation order is observable
  D  sorts with tied keys, plus a hash-order canary
  E  small matrix-style reduction
"""

import argparse
import math
import platform
import sys
import time

PROBE_VERSION = "1"


# --------------------------------------------------------------------------
# deterministic input generation
# --------------------------------------------------------------------------

class LCG:
    """Numerical Recipes LCG.

    Pure integer arithmetic, so the generator itself is bit-exact on any
    platform. We do not use `random`: seeding it is one more thing to get
    wrong, and its float conversion is an extra source of doubt.
    """

    __slots__ = ("state",)

    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF

    def next_u32(self):
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state

    def unit(self):
        # Divide by 2**32 -- an exact power-of-two scaling, so the only
        # rounding in the whole pipeline happens in the arithmetic we are
        # actually trying to measure.
        return self.next_u32() / 4294967296.0

    def signed_unit(self):
        return self.unit() * 2.0 - 1.0


# --------------------------------------------------------------------------
# serializer
# --------------------------------------------------------------------------

class Emitter:
    """Writes the canonical payload as bytes.

    Bytes, not text: on Windows a text-mode stream would translate "\\n" into
    "\\r\\n" and change the digest for reasons that have nothing to do with
    floating point. Writing bytes with an explicit b"\\n" makes the payload
    byte-identical regardless of host line-ending convention.

    Line format is  label \\t TYPE \\t value  so a mismatch can be localised to
    a single named operation rather than just "the digests differ".
    """

    __slots__ = ("_w", "count")

    def __init__(self, stream):
        self._w = stream
        self.count = 0

    def raw(self, line):
        """Write a line without counting it (headers, comments)."""
        self._w.write(line.encode("ascii"))
        self._w.write(b"\n")

    def f(self, label, value):
        # float.hex() is exact and round-trippable. It also renders inf/nan
        # without special-casing, and keeps -0.0 distinct from 0.0 -- which is
        # a real signal, not noise.
        self.count += 1
        self.raw("%s\tF\t%s" % (label, float(value).hex()))

    def i(self, label, value):
        self.count += 1
        self.raw("%s\tI\t%d" % (label, int(value)))

    def s(self, label, value):
        self.count += 1
        self.raw("%s\tS\t%s" % (label, value))


# --------------------------------------------------------------------------
# summation helpers -- deliberately different association orders
# --------------------------------------------------------------------------

def _naive_sum(vals):
    total = 0.0
    for v in vals:
        total += v
    return total


def _pairwise_sum(vals, lo=0, hi=None):
    """Recursive halving. Index-based to avoid copying 100k-element slices,
    which matters when this runs under emulation."""
    if hi is None:
        hi = len(vals)
    n = hi - lo
    if n <= 8:
        total = 0.0
        for i in range(lo, hi):
            total += vals[i]
        return total
    mid = lo + n // 2
    return _pairwise_sum(vals, lo, mid) + _pairwise_sum(vals, mid, hi)


# --------------------------------------------------------------------------
# A -- exp / log / sqrt chains
# --------------------------------------------------------------------------

def section_a(em):
    """Compounds rounding through the three transcendentals the model leans
    on. The chain is contracting, so it cannot overflow into a uniform inf
    that would mask a divergence."""
    rng = LCG(0x5EEDA001)
    finals = []

    for i in range(64):
        x = rng.signed_unit() * 2.0
        for _ in range(50):
            t = math.exp(-abs(x))   # (0, 1]
            t = math.log1p(t)       # (0, ln 2]
            t = math.sqrt(t)
            x = 0.5 * x + t
        em.f("A.chain[%02d]" % i, x)
        finals.append(x)

    em.f("A.acc_naive", _naive_sum(finals))
    em.f("A.acc_fsum", math.fsum(finals))

    # Round-trip stress: exp(log(v)) and sqrt(v)**2 should be near-identity but
    # are not exactly so. The residual is a fingerprint of the libm.
    for j, v in enumerate([1e-300, 1e-8, 0.5, 1.0, 2.0, 7.0, 1e8, 1e300]):
        em.f("A.explog[%d]" % j, math.exp(math.log(v)) - v)
        em.f("A.sqrtsq[%d]" % j, math.sqrt(v) * math.sqrt(v) - v)
        em.f("A.pow_half[%d]" % j, v ** 0.5 - math.sqrt(v))


# --------------------------------------------------------------------------
# B -- erf across the range, including tails and subnormals
# --------------------------------------------------------------------------

def section_b(em):
    """erf is where a divergent libm would show up first.

    Includes the saturated tails (where erf -> +/-1 and erfc carries all the
    remaining information), and subnormals, because flush-to-zero behaviour is
    a genuine source of platform disagreement and RISC-V is exactly the sort of
    target where it might bite.
    """
    sqrt2 = math.sqrt(2.0)

    xs = [i / 10.0 for i in range(-65, 66)]
    xs.extend([-40.0, -20.0, -10.0, -8.0, -6.5, -6.0, -5.5,
               5.5, 6.0, 6.5, 8.0, 10.0, 20.0, 40.0])
    xs.extend([0.0, -0.0, 1e-8, -1e-8, 1e-300, -1e-300,
               5e-324, -5e-324])  # 5e-324 is the smallest subnormal

    for i, x in enumerate(xs):
        em.f("B.erf[%03d]" % i, math.erf(x))
        em.f("B.erfc[%03d]" % i, math.erfc(x))
        # The form the model actually calls: standard normal CDF.
        em.f("B.ncdf[%03d]" % i, 0.5 * (1.0 + math.erf(x / sqrt2)))

    # Tail agreement: 1-erf(x) loses precision where erfc(x) does not. If these
    # two ever agree exactly in the deep tail, something has been flushed.
    for j, x in enumerate([3.0, 4.0, 5.0, 6.0, 7.0, 8.0]):
        em.f("B.tail_naive[%d]" % j, 1.0 - math.erf(x))
        em.f("B.tail_erfc[%d]" % j, math.erfc(x))


# --------------------------------------------------------------------------
# C -- large summation where accumulation order is observable
# --------------------------------------------------------------------------

def section_c(em, n):
    """Values span 80 binary orders of magnitude, so the sum is severely
    cancellation-sensitive and the association order is visible in the result.

    Scaling is by powers of two, which is exact -- that isolates the effect we
    want (accumulation order) from any rounding in input generation.

    These six results SHOULD differ from each other. What must not differ is
    any one of them between runs. If C is the only section that moves, the
    diagnosis is an unordered or threaded reduction, and the fix is fsum or a
    sort before summing.
    """
    rng = LCG(0xC0FFEE01)
    vals = []
    for i in range(n):
        vals.append(rng.signed_unit() * (2.0 ** ((i % 81) - 40)))

    em.i("C.n", n)
    em.f("C.sum_generated_order", _naive_sum(vals))
    em.f("C.sum_ascending", _naive_sum(sorted(vals)))
    em.f("C.sum_descending", _naive_sum(sorted(vals, reverse=True)))
    em.f("C.sum_abs_ascending", _naive_sum(sorted(vals, key=abs)))
    em.f("C.sum_pairwise", _pairwise_sum(vals))
    em.f("C.sum_fsum", math.fsum(vals))

    # A compensated (Kahan) sum, for reference against fsum.
    total = 0.0
    comp = 0.0
    for v in vals:
        y = v - comp
        t = total + y
        comp = (t - total) - y
        total = t
    em.f("C.sum_kahan", total)


# --------------------------------------------------------------------------
# D -- sorts with tied keys, and a hash-order canary
# --------------------------------------------------------------------------

def section_d(em):
    rng = LCG(0xD00D1234)

    # Heavy tying: 256 records over 16 distinct keys. Python's sort is stable,
    # so insertion order must be preserved among ties. Emitted as one line to
    # keep the payload compact.
    recs = [(rng.next_u32() % 16, i) for i in range(256)]
    order = ",".join(str(idx) for _key, idx in sorted(recs, key=lambda r: r[0]))
    em.s("D1.stable_order", order)

    # Ties between floats that are equal but were computed differently.
    a = 0.1 + 0.2                 # 0.30000000000000004
    b = 0.30000000000000004
    tagged = [(a, "a"), (b, "b"), (0.3, "c"), (a, "d"), (b, "e")]
    em.s("D2.float_tie_order",
         ",".join(tag for _k, tag in sorted(tagged, key=lambda p: p[0])))
    em.i("D2.a_eq_b", int(a == b))

    # Hash-order canary. Set iteration order depends on string hashing, which
    # is randomised per process unless PYTHONHASHSEED is fixed. Dicts are NOT a
    # canary here -- they have preserved insertion order since 3.7.
    #
    # This is IN the payload deliberately. If the hygiene env vars are missing,
    # the probe should fail loudly rather than pass quietly. When this is the
    # only differing line, the diagnosis is "PYTHONHASHSEED was not set to 0",
    # not a floating-point problem.
    names = set("mkt_%04d" % i for i in range(64))
    em.s("D3.hash_order_canary", ",".join(names))


# --------------------------------------------------------------------------
# E -- small matrix-style reduction
# --------------------------------------------------------------------------

def section_e(em, n=16):
    rng = LCG(0xE1E10042)
    a = [[rng.signed_unit() for _ in range(n)] for _ in range(n)]
    b = [[rng.signed_unit() for _ in range(n)] for _ in range(n)]

    c = []
    for i in range(n):
        row = []
        for j in range(n):
            acc = 0.0
            for k in range(n):
                acc += a[i][k] * b[k][j]
            row.append(acc)
        c.append(row)

    for i in range(n):
        for j in range(n):
            em.f("E.c[%02d][%02d]" % (i, j), c[i][j])

    em.f("E.trace", _naive_sum([c[i][i] for i in range(n)]))
    em.f("E.frob_naive", math.sqrt(_naive_sum([v * v for row in c for v in row])))
    em.f("E.frob_fsum", math.sqrt(math.fsum([v * v for row in c for v in row])))

    # Same dot product, two association orders.
    col = [a[i][0] for i in range(n)]
    row0 = [b[0][j] for j in range(n)]
    em.f("E.dot_fwd", _naive_sum([col[i] * row0[i] for i in range(n)]))
    em.f("E.dot_rev", _naive_sum([col[i] * row0[i] for i in range(n - 1, -1, -1)]))


# --------------------------------------------------------------------------
# N -- optional numpy section (opt-in; changes the digest by design)
# --------------------------------------------------------------------------

def section_n(em):
    import numpy as np

    em.s("N.numpy_version", np.__version__)
    rng = LCG(0x9A9A0001)
    arr = np.array([rng.signed_unit() * (2.0 ** ((i % 81) - 40))
                    for i in range(20000)], dtype=np.float64)

    em.f("N.np_sum", float(arr.sum()))
    em.f("N.np_sum_sorted", float(np.sort(arr).sum()))
    em.f("N.py_fsum", math.fsum(arr.tolist()))
    em.f("N.np_dot", float(arr.dot(arr)))
    em.f("N.np_mean", float(arr.mean()))

    m = arr[:256].reshape(16, 16)
    em.f("N.np_matmul_trace", float(np.trace(m @ m)))


# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sum-n", type=int, default=100000,
                    help="element count for section C (default: 100000). "
                         "Recorded in the payload header, so runs with "
                         "different values cannot be compared by accident.")
    ap.add_argument("--with-numpy", action="store_true",
                    help="include the numpy section. Off by default so the "
                         "payload stays comparable across environments.")
    args = ap.parse_args(argv)

    started = time.perf_counter()

    out = sys.stdout.buffer
    em = Emitter(out)

    # Header is part of the payload: it makes a workload mismatch show up as a
    # digest mismatch instead of silently comparing two different experiments.
    em.raw("# probe-version\t%s" % PROBE_VERSION)
    em.raw("# sum-n\t%d" % args.sum_n)
    em.raw("# with-numpy\t%d" % int(args.with_numpy))

    section_a(em)
    section_b(em)
    section_c(em, args.sum_n)
    section_d(em)
    section_e(em)
    if args.with_numpy:
        section_n(em)

    em.raw("# records\t%d" % em.count)
    out.flush()

    elapsed = time.perf_counter() - started

    # STDERR only. The no-wall-clock rule protects the payload; reading the
    # clock for a timing report that never touches the payload is fine.
    w = sys.stderr.write
    w("probe.py metadata -- NOT part of the digest\n")
    w("python_version   : %s\n" % sys.version.replace("\n", " "))
    w("implementation   : %s\n" % platform.python_implementation())
    w("platform         : %s\n" % platform.platform())
    w("machine          : %s\n" % platform.machine())
    w("maxsize          : %d\n" % sys.maxsize)
    w("float_repr_style : %s\n" % sys.float_repr_style)
    w("float_mant_dig   : %d\n" % sys.float_info.mant_dig)
    w("records_emitted  : %d\n" % em.count)
    w("elapsed_seconds  : %.6f\n" % elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
