#!/usr/bin/env bash
# Runs the frozen probe.py inside the built Cartesi machine, captures its
# payload to the host, and compares digests across runs.
#
# Drives cartesi-machine directly rather than via `cartesi shell`, because
# `shell` hard-codes --tty/-it. A TTY would inject carriage returns into the
# payload and corrupt the digest. No TTY = clean bytes.
#
# probe.py writes the payload to stdout and metadata to stderr; inside the
# machine both land on one console. The payload is extracted by its own
# delimiters, which is safe because probe.py flushes stdout before writing
# any metadata.
#
# NOTE: the machine's self-reported elapsed_seconds is EMULATED time, not host
# time -- a deterministic machine has a deterministic clock. Use host wall time
# for any overhead ratio. See trap #10.
set -euo pipefail

CARTESI_DIR="${CARTESI_DIR:-$HOME/probe-test/.cartesi}"
OUT="${OUT:-/tmp/machine-run}"
RUNS="${RUNS:-2}"
SDK="${SDK:-cartesi/sdk:0.12.0-alpha.41}"
PROBE_PATH="${PROBE_PATH:-/opt/cartesi/dapp/probe.py}"
HYGIENE="env PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LC_ALL=C LANG=C TZ=UTC"

mkdir -p "$OUT"
echo "machine dir : $CARTESI_DIR"
echo "runs        : $RUNS"
echo

for i in $(seq 1 "$RUNS"); do
  start=$(date +%s.%N)
  docker run --rm \
    --volume "$CARTESI_DIR:/work" --workdir /work \
    --user "$(id -u):$(id -g)" \
    "$SDK" \
    cartesi-machine \
      --flash-drive=label:root,data_filename:root.ext2 \
      --ram-length=128Mi \
      -- "$HYGIENE python3 $PROBE_PATH" \
    > "$OUT/raw_$i.txt" 2>&1
  end=$(date +%s.%N)
  hostwall=$(awk -v a="$start" -v b="$end" 'BEGIN{printf "%.2f", b-a}')

  sed -n '/^# probe-version/,/^# records/p' "$OUT/raw_$i.txt" > "$OUT/payload_$i.txt"
  d=$(sha256sum "$OUT/payload_$i.txt" | cut -d' ' -f1)
  cyc=$(grep -aoP '^Cycles:\s*\K[0-9]+' "$OUT/raw_$i.txt" | tail -1 || echo "?")
  emul=$(grep -aoP 'elapsed_seconds\s*:\s*\K[0-9.]+' "$OUT/raw_$i.txt" | tail -1 || echo "?")

  printf 'run %d  digest %s\n' "$i" "$d"
  printf '       cycles %-12s  host wall %ss  (emulated clock says %ss)\n' "$cyc" "$hostwall" "$emul"
  echo "$d" > "$OUT/digest_$i"
done

echo
first=$(cat "$OUT/digest_1"); allmatch=yes
for i in $(seq 2 "$RUNS"); do
  [ "$(cat "$OUT/digest_$i")" = "$first" ] || allmatch=no
done
if [ "$allmatch" = yes ]; then
  echo "RESULT: MATCH across $RUNS run(s)"
else
  echo "RESULT: MISMATCH"
  for i in $(seq 2 "$RUNS"); do
    if [ "$(cat "$OUT/digest_$i")" != "$first" ]; then
      diff "$OUT/payload_1.txt" "$OUT/payload_$i.txt" \
        | grep -oP '^[<>] \K[A-Z][0-9]?\.[^\t[]*' | sort | uniq -c | sort -rn | head
    fi
  done
fi
