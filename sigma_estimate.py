#!/usr/bin/env python3
"""
sigma_estimate.py -- realized annualised volatility per collateral class.

Converts the assigned sigma values in DAY7-RESULTS.md section 3 from
assumptions into measurements, using an independent public price source
rather than the Morpho indexer whose USD prices were found defective for
78% of reported exposure (DAY6-RESULTS.md section 2).

Method: daily closes, log returns, sample standard deviation, annualised by
sqrt(365). Window and source are stated in the output so the number can be
reproduced or disputed.

Pure stdlib apart from curl.
"""
import json, math, subprocess, sys, time

SOURCE = "CoinGecko /coins/{id}/market_chart, vs_currency=usd, interval=daily"
DAYS = 365

CLASSES = {
    "BTC-like":   "bitcoin",
    "ETH-like":   "ethereum",
    "LST / LRT":  "wrapped-steth",
    "stablecoin": "ethena-usde",
}


def daily_closes(coin_id, days=DAYS, tries=3):
    url = (f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
           f"?vs_currency=usd&days={days}&interval=daily")
    for i in range(tries):
        out = subprocess.run(["curl", "-s", "--max-time", "45", url],
                             capture_output=True, text=True).stdout
        try:
            d = json.loads(out)
        except Exception:
            time.sleep(3 * (i + 1)); continue
        if "prices" in d:
            return [p[1] for p in d["prices"] if p[1] and p[1] > 0]
        time.sleep(3 * (i + 1))
    raise RuntimeError(f"no price series for {coin_id}")


def realized_vol(prices):
    rets = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / (n - 1)
    return math.sqrt(var) * math.sqrt(365.0), n


def main():
    print(f"source : {SOURCE}")
    print(f"window : trailing {DAYS} days of daily closes")
    print(f"method : sample stdev of daily log returns, annualised by sqrt(365)")
    print()
    print(f"  {'class':<12} {'proxy asset':<16} {'obs':>5} {'realized sigma':>15} {'assigned':>10}")
    assigned = {"BTC-like": 0.45, "ETH-like": 0.60, "LST / LRT": 0.65, "stablecoin": 0.10}
    out = {}
    for cls, cid in CLASSES.items():
        try:
            px = daily_closes(cid)
            s, n = realized_vol(px)
            out[cls] = s
            print(f"  {cls:<12} {cid:<16} {n:>5} {s*100:>14.1f}% {assigned[cls]*100:>9.0f}%")
        except Exception as e:
            print(f"  {cls:<12} {cid:<16}  FAILED: {e}")
        time.sleep(2)
    print()
    print("  RWA / PT     -- NOT MEASURABLE this way. PT tokens and tokenised")
    print("                  credit have no liquid continuous price series.")
    print("                  Remains an assumption; stated as such.")
    json.dump(out, open("/tmp/sigma_measured.json", "w"))


if __name__ == "__main__":
    sys.exit(main())
