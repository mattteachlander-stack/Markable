#!/usr/bin/env bash
# Build the self-contained distribution hub → dist/markable.html
#
#   scripts/build_dist.sh                 # hub only (reports open as siblings)
#   scripts/build_dist.sh <reports-dir>   # hub with every known report baked in
#
# The output is one HTML file: open it in any browser, no install, no network
# (the only network calls are the teacher-opt-in AI features, consent-gated).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
if [ $# -ge 1 ]; then
  uv run markable studio -o dist/markable.html --embed "$@"
else
  uv run markable studio -o dist/markable.html
fi
echo "Built dist/markable.html ($(du -h dist/markable.html | cut -f1))"
