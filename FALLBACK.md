# Fallback design: numpy unavailable, or floats diverge

Written before day 2 so the ladder has somewhere to go. Nothing here is
speculative about the model — it is about which arithmetic substrate carries it.

## Level 0 — stdlib `math` (the default, and almost certainly the answer)

**numpy is a convenience here, not a dependency.** The Black-Cox closed form
needs exactly five primitives, and every one is in the standard library:

| Model needs | stdlib |
|---|---|
| standard normal CDF `N(·)` | `math.erf` / `math.erfc` |
| `exp`, `log` | `math.exp`, `math.log` |
| `sqrt` | `math.sqrt` |
| powers | `**` |
| exact summation | `math.fsum` |

`math.erf` and `math.erfc` are C99 and have been in CPython since 3.2. They are
not an optional extension and they do not depend on any third-party library.

The normal CDF. **Use the `erfc` form throughout the model. This is not a
style preference and it is not optional.**

The naive `0.5*(1+erf(x/√2))` suffers catastrophic cancellation below roughly
x = −5. These markets are overwhelmingly well-collateralized — the prior art
found the largest ones recorded under one cent of bad debt — so default
probability sits deep in the left tail, exactly where the naive form has
already discarded its precision.

**The decisive point: that error would have passed the determinism gate.**
Bit-identical across every run, three for three, and numerically wrong. The
probe certifies that the same inputs produce the same outputs. It cannot
certify that the outputs mean what you claim. Reproducibility and correctness
are orthogonal.

```python
import math

_SQRT2 = math.sqrt(2.0)

def norm_cdf(x):
    """Standard normal CDF.

    Uses erfc in the left tail. The naive 0.5*(1+erf(x/sqrt2)) form suffers
    catastrophic cancellation for x below about -5: erf approaches -1 and the
    1+erf subtraction throws away most of the significant digits. Since this
    model's whole point is default probability, the left tail is exactly where
    precision must not be given away.
    """
    if x < 0.0:
        return 0.5 * math.erfc(-x / _SQRT2)
    return 0.5 * (1.0 + math.erf(x / _SQRT2))
```

(Section B of `probe.py` emits both forms side by side — `B.tail_naive[*]` vs
`B.tail_erfc[*]` — so you can see the cancellation with your own eyes before
you commit to a formulation.)

**What losing numpy actually costs:** vectorisation. At 3,900 markets × 20 LGD
points = 78,000 closed-form evaluations, that is a sub-second workload in pure
Python. Even at a 100× emulation ratio it is a couple of minutes. The cost is
not material at this scale.

**What losing numpy actually buys:** one fewer source of nondeterminism. BLAS
reductions are multithreaded and the summation order varies with thread count
and scheduling. If numpy is absent you never have to think about
`OMP_NUM_THREADS` again. Treat its absence as a mild simplification, not a
setback.

> If numpy *is* present and you use it, `OMP_NUM_THREADS=1` and
> `OPENBLAS_NUM_THREADS=1` stop being hygiene and become load-bearing.

## Level 1 — floats diverge between runs

Do not reach for a different numeric type yet. First find the unstable
operation. The probe is built to tell you which one.

Read the harness diff's `sections affected` line:

| Sections that moved | Diagnosis | Fix |
|---|---|---|
| only `D3` | `PYTHONHASHSEED` was not `0` | set it; not a float problem |
| only `C.*` | unordered or threaded reduction | `math.fsum`, or sort before summing |
| `C.sum_fsum` stable, others moved | confirms it is accumulation order | switch the model to `fsum` |
| `A.*` or `B.*` | libm disagreement | serious — see Level 2 |
| `E.*` only | matrix accumulation order | fix the loop order, or `fsum` the inner product |

The common case is a reduction. The fix is mechanical: replace every `sum()`
over floats in the model with `math.fsum`, which is exactly rounded and
therefore order-independent by construction. `probe.py` already emits
`C.sum_fsum` and `E.frob_fsum` so you can confirm the fsum path is stable
before you rewrite anything.

## Level 2 — `A.*` or `B.*` diverge (libm disagreement)

This means `exp`/`log`/`erf` themselves return different bits in the machine
than natively, or between two machine runs. Between two *machine* runs this
would be alarming and would point at the emulator; between machine and native
it is unsurprising and **not actually a problem for your claim**.

Be precise about what you need to assert. The claim is *"the same computation
inside the Cartesi machine reproduces bit-identically"*, not *"the machine
agrees with my laptop"*. Only the former is what a verifiable-compute argument
requires. If machine-to-machine is stable and machine-to-native differs, you
have a working result — just state the scope correctly in the write-up.

If machine-to-machine genuinely diverges in `A`/`B`, go to Level 3.

## Level 3 — fixed-point integers, or `decimal` with an explicit context

Deterministic by construction. Slower, more code. Two routes.

### 3a. Fixed-point integers

Scale everything to integers and do arithmetic in Python's arbitrary-precision
ints, which are exact and have no platform-dependent behaviour at all.

```python
SCALE = 10 ** 12        # 12 decimal places

def to_fx(x):  return int(round(x * SCALE))
def fx_mul(a, b): return (a * b) // SCALE
def fx_div(a, b): return (a * SCALE) // b
```

Works cleanly for the linear parts of the model. Does **not** give you `exp`,
`log`, or `erf` — you would implement those yourself against a fixed-point
series. Significant work.

### 3b. `decimal` with a pinned context

```python
from decimal import Decimal, getcontext, ROUND_HALF_EVEN, localcontext

# Must be set explicitly, in every process. The decimal context is
# thread-local and its default precision (28) is not a promise you should
# rely on across interpreter versions.
getcontext().prec = 34
getcontext().rounding = ROUND_HALF_EVEN
getcontext().Emin, getcontext().Emax = -999999, 999999
```

`Decimal` gives you `exp()`, `ln()`, `log10()`, and `sqrt()` as correctly
rounded operations within the set context — genuinely deterministic.

**The landmine: `decimal` has no `erf`.** This is the hidden cost of Level 3
and the reason it is the last rung. You would implement `erf` yourself:

```python
def erf_decimal(x):
    """Maclaurin series. Converges well for |x| <~ 3; for larger |x| use the
    asymptotic erfc expansion or the continued fraction, because the
    alternating series loses too much to cancellation out there."""
    with localcontext() as ctx:
        ctx.prec += 10                  # guard digits, dropped on return
        total, term, n = Decimal(0), x, 0
        x2 = x * x
        while True:
            contrib = term / (2 * n + 1)
            if n % 2:
                total -= contrib
            else:
                total += contrib
            if abs(contrib) < Decimal(10) ** (-ctx.prec):
                break
            n += 1
            term = term * x2 / n
        result = total * 2 / Decimal(math.pi).sqrt()
    return +result                      # unary plus applies the outer context
```

The redeeming feature: **you can validate it against `math.erf` natively to ~15
digits before you ever trust it.** Write it, check it against stdlib on the
laptop across the same range `probe.py` section B covers, and only then move it
into the machine. That makes Level 3 tedious rather than risky.

Budget realistically: a correct, tail-accurate `erf` in `decimal` is a day of
work, not an hour. That is the real argument for not needing Level 3.

## Decision order

```
numpy missing?              -> Level 0. Proceed, lose nothing.
digests differ?             -> read `sections affected` first, never guess
  only D3                   -> set PYTHONHASHSEED=0, rerun
  C.* / E.*                 -> Level 1: math.fsum everywhere
  A.* / B.* machine-to-machine -> Level 3
  A.* / B.* machine-vs-native  -> not a defect; narrow the claim's scope
```
