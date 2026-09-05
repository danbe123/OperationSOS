#!/usr/bin/env bash
# Operation SOS smoke test: one PASS or FAIL line per check against a running stack, exit 1 on any FAIL.
#   dev/smoke.sh                                  the dev stack from `make dev` (Caddy on 8080)
#   SOS_SMOKE_URL=http://10.42.0.1 dev/smoke.sh   a box, from a laptop on the hotspot
# SOS_SMOKE_BOOK names the ZIM whose reader root must answer (default: the sample Wikipedia ZIM).
set -uo pipefail

BASE=${SOS_SMOKE_URL:-http://127.0.0.1:8080}
BOOK=${SOS_SMOKE_BOOK:-wikipedia_en_100_mini_2026-01}
pass=0
fail=0

# check <label> <path> <expected-status> <body-regex> [follow]
check() {
  local label=$1 path=$2 want=$3 pattern=$4 follow=${5:-} tmp code
  tmp=$(mktemp)
  if [ -n "$follow" ]; then
    code=$(curl -sS -L -o "$tmp" -w '%{http_code}' --max-time 20 "$BASE$path" 2>/dev/null || echo 000)
  else
    code=$(curl -sS -o "$tmp" -w '%{http_code}' --max-time 20 "$BASE$path" 2>/dev/null || echo 000)
  fi
  if [ "$code" = "$want" ] && grep -Eq -- "$pattern" "$tmp"; then
    echo "PASS $label ($code)"
    pass=$((pass + 1))
  else
    echo "FAIL $label (got $code, wanted $want matching '$pattern'; body: $(head -c 100 "$tmp" | tr '\n' ' '))"
    fail=$((fail + 1))
  fi
  rm -f "$tmp"
}

# check_redirect <path> <location>: a 302 whose Location header is exactly <location>
check_redirect() {
  local path=$1 want=$2 headers code loc
  headers=$(curl -sS -o /dev/null -D - --max-time 20 "$BASE$path" 2>/dev/null || true)
  code=$(printf '%s\n' "$headers" | head -1 | awk '{ print $2 }')
  loc=$(printf '%s\n' "$headers" | awk 'tolower($1) == "location:" { print $2 }' | tr -d '\r')
  if [ "$code" = "302" ] && [ "$loc" = "$want" ]; then
    echo "PASS GET $path -> 302 $loc"
    pass=$((pass + 1))
  else
    echo "FAIL GET $path (got ${code:-nothing} ${loc:-without Location}; wanted 302 $want)"
    fail=$((fail + 1))
  fi
}

check "GET /api/status" /api/status 200 '"version"'
check "GET /api/library" /api/library 200 '"categories"'
check "GET /api/search?q=water" '/api/search?q=water' 200 '"results"'
check "GET /api/suggest?q=wat" '/api/suggest?q=wat' 200 '^\['
check "GET /kiwix/content/$BOOK/" "/kiwix/content/$BOOK/" 200 '<html' follow
check "GET /welcome" /welcome 200 '10\.42\.0\.1'
check_redirect /generate_204 http://10.42.0.1/welcome

echo "smoke: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
