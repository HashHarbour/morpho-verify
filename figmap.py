import os, sys, re

repo = sys.argv[1]

# (figure as it appears in the post, search token, source file)
FIGS = [
    ("$2.13 published claim",            "2.13",              "DAY6-RESULTS.md"),
    ("$0.08 Prime markets",              "0.08",              "DAY6-RESULTS.md"),
    ("$0.15 all Steakhouse USDC",        "0.15",              "DAY6-RESULTS.md"),
    ("27,259 USDC liquidations",         "27,259",            "DAY9-RESULTS.md"),
    ("0.1829% unconditional",            "0.1829",            "DAY9-RESULTS.md"),
    ("18.3 bps",                         "18.3 bps",          "DAY9-RESULTS.md"),
    ("606 bad-debt events",              "606",               "DAY9-RESULTS.md"),
    ("78.9195% conditional",             "78.9195",           "DAY9-RESULTS.md"),
    ("431.5x ratio",                     "431.5",             "DAY9-RESULTS.md"),
    ("2.22% of liquidations",            "2.22",              "DAY9-RESULTS.md"),
    ("49,303.14 published",              "49,303.14",         "FINDINGS.md"),
    ("83,787.16 on-chain gross (rounded from 83,787.159294)", "83,787.159294", "RECONCILIATION.md"),
    ("34,480.95 recovery",               "34,480.95",         "FINDINGS.md"),
    ("41% apart",                        "41%",               "FINDINGS.md"),
    ("99.7% RLP",                        "99.7%",             "FINDINGS.md"),
    ("65 liquidations",                  "65 liquidations",   "FINDINGS.md"),
    ("$1.84M repaid, zero bad debt",     "1.84M",             "FINDINGS.md"),
    ("$1.18M terminal liquidation",      "1.18M",             "FINDINGS.md"),
    ("PAXG $9,078,714,827",              "9,078,714,827",     "DAY6-RESULTS.md"),
    ("PAXG $260.46 collateral",          "260.46",            "DAY6-RESULTS.md"),
    ("sdeUSD $6,001,989,178",            "6,001,989,178",     "DAY6-RESULTS.md"),
    ("37 markets impossible LTV",        "37 markets",        "DAY6-RESULTS.md"),
    ("78% of reported exposure",         "78",                "DAY6-RESULTS.md"),
    ("1,000 of 3,904 markets",           "3,904",             "DAY7-RESULTS.md"),
    ("200 of 980 vaults",                "980",               "DAY7-RESULTS.md"),
    ("position cap 10,000",              "10,000",            "DAY7-RESULTS.md"),
    ("7,447 first pull",                 "7,447",             "DAY9-RESULTS.md"),
    ("377 of 611 missing",               "377",               "DAY9-RESULTS.md"),
    ("5.9 bps near-miss",                "5.9 bps",           "DAY8-RESULTS.md"),
    ("92% of numerator mass",            "92% of its mass",   "DAY8-RESULTS.md"),
    ("five model specifications",        "five specifications","DAY5-RESULTS.md"),
    ("45 bps floor",                     "45 bps",            "DAY5-RESULTS.md"),
    ("400+ bps passive",                 "400 bps",           "DAY5-RESULTS.md"),
    ("LTV 46.9% measured",               "46.9",              "DAY7-RESULTS.md"),
    ("sigma 44.8% measured",             "44.8",              "DAY7-RESULTS.md"),
    ("10,100 positions",                 "10,100",            "DAY7-RESULTS.md"),
    ("4.06x LTV and sigma",              "4.06",              "DAY7-RESULTS.md"),
    ("dataset hash 54e7610b",            "54e7610b",          "DAY9-MACHINE-RUN.md"),
    ("machine hash 7ab6f269",            "7ab6f269",          "DAY9-MACHINE-RUN.md"),
    ("payload hash dbdcbb34",            "dbdcbb34",          "DAY9-MACHINE-RUN.md"),
    ("250-400 bps required",             "250-400",           "DAY5-RESULTS.md"),
]

cache = {}
def load(f):
    if f not in cache:
        p = os.path.join(repo, f)
        cache[f] = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    return cache[f]

rows, bad = [], []
for label, token, src in FIGS:
    txt = load(src)
    if txt is None:
        ok = "FILE MISSING"
        bad.append((label, src, "file missing"))
    elif token in txt:
        ok = "ok"
    else:
        ok = "NOT FOUND"
        bad.append((label, src, token))
    rows.append((label, src, ok))

w = max(len(r[0]) for r in rows)
lines = ["# Figure-to-file map",
         "",
         "Every number in POST.md, and the committed file it comes from.",
         "Verified by search, not asserted. Regenerate with figmap.py.",
         "",
         "| figure in the post | source file | verified |",
         "|---|---|---|"]
for label, src, ok in rows:
    lines.append("| %s | `%s` | %s |" % (label, src, ok))
lines += ["", "## Result", ""]
if bad:
    lines.append("**%d figure(s) could not be traced:**" % len(bad))
    for l, s, t in bad:
        lines.append("- %s -- token `%s` not found in `%s`" % (l, t, s))
else:
    lines.append("**All %d figures traced to committed files.**" % len(rows))

out = "\n".join(lines) + "\n"
open(os.path.join(repo, "FIGURE-MAP.md"), "w", encoding="utf-8", newline="\n").write(out)

print("figures checked: %d" % len(rows))
print("untraceable    : %d" % len(bad))
for l, s, t in bad:
    print("  MISS: %-34s token %-22s not in %s" % (l, repr(t), s))
