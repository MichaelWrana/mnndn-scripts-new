#!/usr/bin/env bash
# run_series.sh — usage: ./run_series.sh <x:int> <y:int>

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <x:int> <y:int>" >&2
  exit 1
fi

x="$1"
y="$2"

# minimal sanity checks
[[ "$x" =~ ^-?[0-9]+$ ]] || { echo "x must be an integer" >&2; exit 1; }
[[ "$y" =~ ^[0-9]+$   ]] || { echo "y must be a non-negative integer" >&2; exit 1; }

PYTHON="${PYTHON:-$(command -v python3 || command -v python || true)}"
[[ -n "$PYTHON" ]] || { echo "python not found in PATH" >&2; exit 1; }

for (( i=0; i<y; i++ )); do
  base=$(( x + i + 2 ))
  pages_scraper=$(( base * 110 ))
  pages_verify=$(( base * 100 ))

  echo "Iter $((i+1))/$y  base=$base  scraper: $pages_scraper  verify: $pages_verify"

  "$PYTHON" scraper.py      --maxpages "$pages_scraper"
  "$PYTHON" verifyreplay.py --maxpages "$pages_verify"
  "$PYTHON" recordtraces.py --dns --bgtraffic --maxreplay 1
  bash ow-clean.sh
done
