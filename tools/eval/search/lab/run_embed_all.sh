#!/bin/bash
# one process per model so the GPU is fully freed between models
PY=/home/dan/.local/share/sos-embed-venv/bin/python
cd "$(dirname "$0")"
for m in bge-base-en-v1.5 bge-large-en-v1.5 e5-small-v2 e5-base-v2 all-MiniLM-L12-v2 arctic-embed-s arctic-embed-m arctic-embed-m-v1.5 \
         mxbai-embed-large-v1 mxbai-embed-xsmall-v1 granite-embedding-small-english-r2 granite-embedding-english-r2 gte-small gte-base \
         multi-qa-MiniLM-L6-cos-v1 all-mpnet-base-v2; do
  echo "=== $m"; $PY embed.py $m 2>&1 | grep -v -E "Loading weights|Warning|deprecated" | tail -3
done
echo "=== all-MiniLM-L12-v2 @128"; $PY embed.py all-MiniLM-L12-v2 --maxlen 128 --tag @128 2>&1 | tail -1
echo "=== bge-small-en-v1.5 @256"; $PY embed.py bge-small-en-v1.5 --maxlen 256 --tag @256 2>&1 | tail -1
echo ALLDONE
