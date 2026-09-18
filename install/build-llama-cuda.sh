#!/usr/bin/env bash
# Builds a second, CUDA-enabled llama-server for PC-side bulk embedding builds only (sos build-embeddings's
# household/Wikipedia collections). The box's own build stays the existing CPU-only native-ARM one -- this
# script never touches /usr/local/bin/llama-server or the systemd unit.
set -euo pipefail
SRC=${LLAMA_CPP_SRC:-$HOME/llama.cpp}
OUT=$HOME/.local/bin/llama-server-cuda
if [ ! -d "$SRC" ]; then
  echo "build-llama-cuda: cloning llama.cpp (see install/versions.env for the pinned tag)" >&2
  git clone --depth 1 --branch "$(grep '^LLAMA_CPP_TAG=' /home/dan/OperationSOS/install/versions.env | cut -d= -f2)" \
    https://github.com/ggml-org/llama.cpp "$SRC"
fi
cmake -S "$SRC" -B "$SRC/build-cuda" -DGGML_CUDA=ON -DLLAMA_BUILD_TESTS=OFF -DCMAKE_BUILD_TYPE=Release
cmake --build "$SRC/build-cuda" --config Release -j"$(nproc)" --target llama-server
mkdir -p "$(dirname "$OUT")"
cp "$SRC/build-cuda/bin/llama-server" "$OUT"
echo "build-llama-cuda: built $OUT"
"$OUT" --version
