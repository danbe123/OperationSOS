#!/usr/bin/env bash
# Operation SOS dev stack on the PC (spec section 13, "Development"). Started by `make dev`.
#   kiwix-serve  8090  over the sample ZIMs in $SOS_CORE/zim (library.xml built here with kiwix-manage)
#   sos-api      8000  uvicorn with SOS_DEV=1, the dev manifest and the repo's playbooks
#   caddy        8080  the production Caddyfile with its roots and upstreams overridden by environment
#                      variables (see install/caddy/Caddyfile for the contract)
# State and logs live under $SOS_DEV_DIR (default <repo>/.dev, ignored by git). Ctrl-C stops all three.
#
# Overrides: SOS_CORE (default /home/dan/sos-content), SOS_MANIFEST_DIR (default dev/manifest),
# SOS_PLAYBOOKS_DIR (default playbooks), SOS_MODEL (passed through to sos-api), SOS_KIWIX_PORT,
# SOS_PORT, SOS_HTTP_PORT, SOS_DEV_DIR.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONTENT=${SOS_CORE:-/home/dan/sos-content}
DEV_DIR=${SOS_DEV_DIR:-$REPO/.dev}
STATE=$DEV_DIR/state
EXT=$DEV_DIR/extended
LOGS=$DEV_DIR/logs
KIWIX_PORT=${SOS_KIWIX_PORT:-8090}
API_PORT=${SOS_PORT:-8000}
HTTP_PORT=${SOS_HTTP_PORT:-8080}
MANIFEST_DIR=${SOS_MANIFEST_DIR:-$REPO/dev/manifest}
PLAYBOOKS_DIR=${SOS_PLAYBOOKS_DIR:-$REPO/playbooks}
UVICORN=$REPO/api/.venv/bin/uvicorn

for tool in kiwix-serve kiwix-manage caddy curl; do
  command -v "$tool" >/dev/null || { echo "run-dev: $tool is not on PATH" >&2; exit 1; }
done
[ -x "$UVICORN" ] || { echo "run-dev: $UVICORN is missing; run 'make venv' first" >&2; exit 1; }
[ -d "$CONTENT/zim" ] || { echo "run-dev: no ZIM directory at $CONTENT/zim (set SOS_CORE)" >&2; exit 1; }

mkdir -p "$STATE/config" "$EXT" "$LOGS" "$CONTENT/maps" "$CONTENT/docs" "$CONTENT/models"

# 1. library.xml for kiwix-serve. sos-api regenerates it on boot and on every rescan; --monitorLibrary
#    reloads it, so this only needs to exist before kiwix-serve starts.
LIB=$STATE/library.xml
rm -f "$LIB"
shopt -s nullglob
for zim in "$CONTENT"/zim/*.zim; do
  kiwix-manage "$LIB" add "$zim" >/dev/null || echo "run-dev: kiwix-manage rejected $zim" >&2
done
shopt -u nullglob
if [ ! -f "$LIB" ]; then
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<library version="20110515">\n</library>\n' > "$LIB"
fi
echo "run-dev: library.xml with $(grep -c '<book ' "$LIB" || true) books at $LIB"

# 2. Web root: the built bundle when present, otherwise the install placeholder.
if [ -f "$REPO/web/dist/index.html" ]; then
  WEB_ROOT=$REPO/web/dist
else
  WEB_ROOT=$REPO/install/placeholder
  echo "run-dev: web/dist is not built; serving install/placeholder (run 'make build' for the app)"
fi

PIDS=()
# shellcheck disable=SC2329  # invoked through the traps below
cleanup() {
  trap - EXIT INT TERM
  echo "run-dev: stopping"
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

kiwix-serve --library "$LIB" --monitorLibrary --address all --port "$KIWIX_PORT" --urlRootLocation /kiwix \
  --nosearchbar --nolibrarybutton --blockexternal > "$LOGS/kiwix-serve.log" 2>&1 &
PIDS+=("$!")
echo "run-dev: kiwix-serve  http://127.0.0.1:$KIWIX_PORT/kiwix"

# The embedding server for semantic search, when the model is here (sos/embeddings.py; the box runs the
# same command as install/systemd/sos-embed.service). Without it search is the keyword search alone.
EMBED_PORT=${SOS_EMBED_PORT:-8091}
EMBED_MODEL=$CONTENT/models/embed/bge-small-en-v1.5-q8_0.gguf
if [ -f "$EMBED_MODEL" ] && command -v llama-server >/dev/null 2>&1; then
  if curl -fsS --max-time 1 "http://127.0.0.1:$EMBED_PORT/health" >/dev/null 2>&1; then
    echo "run-dev: embed        http://127.0.0.1:$EMBED_PORT (already running)"
  else
    llama-server -m "$EMBED_MODEL" --embedding --pooling cls -c 512 -ub 512 -b 512 --host 127.0.0.1 --port "$EMBED_PORT" -t 2 --no-webui \
      > "$LOGS/embed.log" 2>&1 &
    PIDS+=("$!")
    echo "run-dev: embed        http://127.0.0.1:$EMBED_PORT (bge-small, semantic search)"
  fi
else
  echo "run-dev: no embedding model at $EMBED_MODEL (or no llama-server): search is keyword only"
fi

SOS_DEV=1 SOS_CORE=$CONTENT SOS_EXT=$EXT SOS_STATE=$STATE SOS_WEB=$WEB_ROOT SOS_EMBED_URL="http://127.0.0.1:$EMBED_PORT" \
  SOS_MANIFEST_DIR=$MANIFEST_DIR SOS_PLAYBOOKS_DIR=$PLAYBOOKS_DIR \
  SOS_KIWIX_URL="http://127.0.0.1:$KIWIX_PORT/kiwix" SOS_PORT=$API_PORT SOS_MAPS_SRC="${SOS_MAPS_SRC:-$CONTENT/maps-src}" \
  "$UVICORN" sos.main:app --host 127.0.0.1 --port "$API_PORT" --proxy-headers --forwarded-allow-ips 127.0.0.1 \
  > "$LOGS/sos-api.log" 2>&1 &
PIDS+=("$!")
echo "run-dev: sos-api      http://127.0.0.1:$API_PORT/api/status  (SOS_DEV=1, manifest $MANIFEST_DIR, playbooks $PLAYBOOKS_DIR)"

SOS_HTTP_PORT=$HTTP_PORT SOS_WEB_ROOT=$WEB_ROOT SOS_MAPS_ROOT=$CONTENT/maps \
  SOS_DOCS_CORE=$CONTENT/docs SOS_DOCS_EXT=$EXT/docs \
  SOS_API_UPSTREAM=127.0.0.1:$API_PORT SOS_KIWIX_UPSTREAM=127.0.0.1:$KIWIX_PORT \
  XDG_DATA_HOME=$DEV_DIR/caddy XDG_CONFIG_HOME=$DEV_DIR/caddy \
  caddy run --config "$REPO/install/caddy/Caddyfile" --adapter caddyfile > "$LOGS/caddy.log" 2>&1 &
PIDS+=("$!")
echo "run-dev: caddy        http://127.0.0.1:$HTTP_PORT  (web root $WEB_ROOT)"
echo "run-dev: logs in $LOGS; Ctrl-C stops all three"

for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "http://127.0.0.1:$HTTP_PORT/api/status" >/dev/null 2>&1; then
    echo "run-dev: ready (http://127.0.0.1:$HTTP_PORT/api/status answered); run dev/smoke.sh in another terminal"
    break
  fi
  sleep 1
done

wait -n || true
echo "run-dev: a service exited; see $LOGS" >&2
exit 1
