#!/usr/bin/env python3
"""A PyTorch fp16 embedding server for Operation SOS's PC-only bulk builds. Never on the box.

`sos build-embeddings-wikipedia` has some six million passages to embed. Through llama-server-cuda
(bge-small-en-v1.5-q8_0.gguf) the card manages about 140 texts a second whatever it is asked --
larger batches and more slots make it slower, several servers side by side gain nothing, `-ub`/`-c`
are worth about a tenth -- which is thirty to fifty hours. bge-small is a 33-million-parameter BERT;
real batched fp16 inference on the same card is many times that. This server speaks exactly the part
of llama-server's HTTP that `api/sos/embeddings.py` uses, so a build cannot tell the two apart:

    GET  /health      200 once the model is on the device
    POST /embeddings  {"input": [text, ...]} -> [{"index": i, "embedding": [floats]}, ...]

Anything else is a non-200 with a JSON `error`, which `EmbedClient`/`embed_sync` turn into an
`EmbedError` -- the same thing they do with llama-server's refusals. A request of more than
--max-batch texts is refused with 413 and embeds nothing: the builds send 32, so a batch orders of
magnitude larger is a caller bug, and one huge padded batch is how a 12 GB card runs out of memory.
Texts are truncated to --max-length (512) tokens, the model's own window -- unlike llama-server,
which errors on a long input and leaves `embed_batch` to shorten it and try again.

Set-up, once (this Ubuntu has no ensurepip, hence --without-pip; torch must come from the system
site-packages, so do not let pip pull another one in):

    python3 -m venv --without-pip ~/.local/share/sos-embed-venv --system-site-packages
    python3 -m pip --python ~/.local/share/sos-embed-venv/bin/python install pip
    ~/.local/share/sos-embed-venv/bin/python -m pip install transformers

Run it (the weights come from Hugging Face on first use and are cached under ~/.cache/huggingface):

    ~/.local/share/sos-embed-venv/bin/python tools/embed_server_torch.py --port 8091

Then point a build at it. It is fp16 rather than the manifest's q8_0 GGUF, so the build must be told
to record what really embedded the vectors, or the store's metadata claims a model it never saw:

    SOS_EMBED_MODEL=bge-small-en-v1.5-fp16-torch api/.venv/bin/sos build-embeddings-wikipedia ...

The build reuses any server already answering /health, so this one only has to be up first."""
from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "BAAI/bge-small-en-v1.5"
MAX_BATCH = 1024
MAX_BODY = 64 * 1024 * 1024


class BadRequest(Exception):
    """A request this server will not act on, carrying the status to answer with."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def texts_from(body: bytes, max_batch: int = MAX_BATCH) -> list[str]:
    """The texts of one /embeddings request, or BadRequest naming what is wrong with it."""
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise BadRequest(f"body is not JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise BadRequest("expected a JSON object with an 'input' key")
    texts = payload.get("input")
    if isinstance(texts, str):
        raise BadRequest("'input' must be a list of strings, not a single string")
    if not isinstance(texts, list) or not texts:
        raise BadRequest("'input' must be a non-empty list of strings")
    if not all(isinstance(t, str) for t in texts):
        raise BadRequest("'input' must contain only strings")
    if len(texts) > max_batch:
        raise BadRequest(f"{len(texts)} texts in one request, more than the {max_batch} allowed", status=413)
    return texts


def embeddings_payload(vectors) -> list[dict]:
    """llama-server's own reply shape, which `sos.embeddings._vectors_from` reads: the rows in request
    order, each tagged with its index. Plain floats, so a numpy array of float16 still serialises."""
    return [{"index": i, "embedding": [float(x) for x in row]} for i, row in enumerate(vectors)]


def make_handler(embed_fn, max_batch: int = MAX_BATCH):
    """The HTTP handler over any `embed_fn(texts) -> rows of floats`. One lock: the GPU takes one batch
    at a time, and a request that raises must release it on the way out or the next one hangs forever."""
    gpu = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "sos-embed-torch"

        def log_message(self, fmt, *args):
            pass        # a bulk build makes hundreds of thousands of requests; failures print themselves

        def _reply(self, status: int, payload) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.split("?", 1)[0] == "/health":
                self._reply(200, {"status": "ok"})
            else:
                self._reply(404, {"error": f"no such path: {self.path}"})

        def do_POST(self):
            if self.path.split("?", 1)[0] != "/embeddings":
                self._reply(404, {"error": f"no such path: {self.path}"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self._reply(400, {"error": "bad Content-Length"})
                return
            if length > MAX_BODY:
                self._reply(413, {"error": f"body of {length} bytes is too large"})
                return
            try:
                texts = texts_from(self.rfile.read(length), max_batch=max_batch)
            except BadRequest as exc:
                self._reply(exc.status, {"error": str(exc)})
                return
            try:
                with gpu:
                    vectors = embed_fn(texts)
                self._reply(200, embeddings_payload(vectors))
            except Exception as exc:
                traceback.print_exc()
                self._reply(500, {"error": f"{type(exc).__name__}: {exc}"})

    return Handler


def load_model(model: str, device: str, max_length: int):
    """The real embed function: CLS pooling over bge-small, fp16 on the GPU, padded only to the longest
    text in the request. torch and transformers are imported here and nowhere else, so everything above
    -- and the tests over it -- works on a machine with neither."""
    import torch
    from transformers import AutoModel, AutoTokenizer

    if device.startswith("cuda") and not torch.cuda.is_available():
        raise SystemExit("FAIL torch reports no CUDA device; pass --device cpu to embed on the CPU instead")
    tokenizer = AutoTokenizer.from_pretrained(model)
    dtype = torch.float16 if device.startswith("cuda") else torch.float32
    net = AutoModel.from_pretrained(model, dtype=dtype, attn_implementation="sdpa").to(device).eval()

    def embed(texts: list[str]):
        batch = tokenizer(texts, padding=True, truncation=True, max_length=max_length,
                          return_tensors="pt").to(device)
        with torch.inference_mode():
            hidden = net(**batch).last_hidden_state[:, 0]        # bge pools the CLS token, not the mean
            vectors = torch.nn.functional.normalize(hidden.float(), p=2, dim=1)
        return vectors.cpu().numpy()

    return embed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--max-batch", type=int, default=MAX_BATCH)
    args = parser.parse_args(argv)

    print(f"loading {args.model} on {args.device} ...", flush=True)
    embed = load_model(args.model, args.device, args.max_length)
    embed(["warm the kernels up so the first real batch is not the slow one"])
    server = ThreadingHTTPServer((args.host, args.port), make_handler(embed, max_batch=args.max_batch))
    print(f"embedding on http://{args.host}:{args.port} ({args.model}, {args.device})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
