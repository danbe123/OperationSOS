#!/bin/bash
PY=/home/dan/.local/share/sos-embed-venv/bin/python
G=/tmp/claude-1000/-home-dan/c0534df7-5406-4037-af74-30748090450c/scratchpad/lab/gguf
cd "$(dirname "$0")"
port=8120
for m in "$@"; do
  echo "=== $m"
  [ -f $G/$m-q8_0.gguf ] || $PY convert.py $m 2>&1 | tail -3
  $PY serve_bench.py embed $m $G/$m-q8_0.gguf $port 2>&1 | grep -v -E "Warning|longer than" | tail -1
  port=$((port+1))
done
echo DDONE
