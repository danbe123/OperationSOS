#!/usr/bin/env bash
# Proves dev/smoke.sh's PASS/FAIL logic against dev/smoke-stub.py: every check passes on a good stub
# (exit 0), and exactly the two broken checks fail on a stub that answers 500 for search and 204 for
# the captive-portal probe (exit 1). Run by `make test`.
set -euo pipefail

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=$(mktemp)
trap 'rm -f "$OUT"' EXIT

free_port() {
  python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

# run_mode <good|broken>: start the stub, run smoke.sh into $OUT, stop the stub, return smoke.sh's exit code.
run_mode() {
  local mode=$1 port pid rc=0
  port=$(free_port)
  python3 "$HERE/smoke-stub.py" "$mode" "$port" &
  pid=$!
  for _ in $(seq 1 50); do
    if curl -s -o /dev/null "http://127.0.0.1:$port/api/status"; then break; fi
    sleep 0.1
  done
  SOS_SMOKE_URL="http://127.0.0.1:$port" bash "$HERE/smoke.sh" > "$OUT" || rc=$?
  kill "$pid"
  wait "$pid" 2>/dev/null || true
  return "$rc"
}

expect() {  # expect <description> <condition...>
  local what=$1
  shift
  if "$@"; then return 0; fi
  echo "smoke-selftest: FAIL: $what" >&2
  cat "$OUT" >&2
  exit 1
}

rc=0
run_mode good || rc=$?
expect "good stub exits 0" [ "$rc" -eq 0 ]
expect "good stub: 7 PASS lines" [ "$(grep -c '^PASS ' "$OUT")" -eq 7 ]
expect "good stub: no FAIL lines" [ "$(grep -c '^FAIL ' "$OUT" || true)" -eq 0 ]
expect "good stub: summary line" grep -qx 'smoke: 7 passed, 0 failed' "$OUT"

rc=0
run_mode broken || rc=$?
expect "broken stub exits 1" [ "$rc" -eq 1 ]
expect "broken stub: 5 PASS lines" [ "$(grep -c '^PASS ' "$OUT")" -eq 5 ]
expect "broken stub: search fails" grep -q '^FAIL GET /api/search?q=water (got 500' "$OUT"
expect "broken stub: probe fails" grep -q '^FAIL GET /generate_204 (got 204' "$OUT"
expect "broken stub: summary line" grep -qx 'smoke: 5 passed, 2 failed' "$OUT"

echo "smoke-selftest: OK"
