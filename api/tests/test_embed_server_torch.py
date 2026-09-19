"""tools/embed_server_torch.py: the PC-only fp16 GPU embedding server the bulk builds talk to.

The tool is a standalone script outside the `sos` package (it runs under a different interpreter: the
system Python, which has torch, plus a venv that has transformers), so it is loaded here by path rather
than imported. Nothing in these tests touches torch or a GPU: they drive the real HTTP handler over a
real socket with a fake embed function, which is exactly the seam the tool is shaped around."""
import importlib.util
import json
import socket
import sys
import threading
import types
from http.server import ThreadingHTTPServer
from pathlib import Path

import httpx
import numpy as np
import pytest

from sos import embeddings

REPO = Path(__file__).resolve().parents[2]
TOOL = REPO / "tools" / "embed_server_torch.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("embed_server_torch", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


@pytest.fixture
def serving():
    """Start the real handler on an ephemeral port with a caller-supplied embed function."""
    servers = []

    def start(embed_fn, **kwargs):
        server = ThreadingHTTPServer(("127.0.0.1", 0), tool.make_handler(embed_fn, **kwargs))
        servers.append(server)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        return f"http://127.0.0.1:{server.server_address[1]}"

    yield start
    for server in servers:
        server.shutdown()
        server.server_close()


def fake_embed(texts):
    """A vector per text that encodes its position, so order is checkable, in the model's real width."""
    return [[float(i + 1)] + [0.0] * (embeddings.DIMS - 1) for i, _ in enumerate(texts)]


def test_the_tool_imports_without_torch_or_transformers(monkeypatch):
    """The parsing, the response shaping and the handler must not drag torch in: the tests, and anyone
    reading the file, get at them without a GPU. Only the model loader imports it, lazily."""
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules


def test_health_is_200_once_the_server_is_up(serving):
    url = serving(fake_embed)
    assert httpx.get(f"{url}/health", timeout=5.0).status_code == 200


def test_the_embeddings_reply_is_the_shape_sos_embeddings_reads(serving):
    """The whole point of the tool: `sos.embeddings._vectors_from` must accept the reply unchanged, so
    the build cannot tell this server from llama-server."""
    url = serving(fake_embed)
    reply = httpx.post(f"{url}/embeddings", json={"input": ["alpha", "beta", "gamma"]}, timeout=10.0)
    assert reply.status_code == 200
    payload = reply.json()
    assert [row["index"] for row in payload] == [0, 1, 2]
    vectors = embeddings._vectors_from(payload)
    assert vectors.shape == (3, embeddings.DIMS)


def test_results_come_back_in_request_order(serving):
    url = serving(fake_embed)
    payload = httpx.post(f"{url}/embeddings", json={"input": ["a", "b", "c", "d"]}, timeout=10.0).json()
    # _vectors_from normalises, so the encoded position survives only as "first component is positive and
    # the rows are distinct"; the raw reply is where the order is checked exactly.
    assert [row["embedding"][0] for row in payload] == [1.0, 2.0, 3.0, 4.0]


def test_a_single_text_still_comes_back_as_a_list_of_one(serving):
    url = serving(fake_embed)
    payload = httpx.post(f"{url}/embeddings", json={"input": ["only"]}, timeout=10.0).json()
    assert len(payload) == 1
    assert embeddings._vectors_from(payload).shape == (1, embeddings.DIMS)


@pytest.mark.parametrize("body", [{"input": []},
                                  {"input": "a bare string"},
                                  {"input": ["fine", 7]},
                                  {"inputs": ["wrong key"]},
                                  {}])
def test_bad_input_is_a_json_error_not_a_crash(serving, body):
    url = serving(fake_embed)
    reply = httpx.post(f"{url}/embeddings", json=body, timeout=10.0)
    assert reply.status_code != 200
    assert reply.json()["error"]


def test_a_body_that_is_not_json_is_a_400(serving):
    url = serving(fake_embed)
    reply = httpx.post(f"{url}/embeddings", content=b"{not json", timeout=10.0)
    assert reply.status_code == 400
    assert reply.json()["error"]


def test_an_oversized_batch_is_refused_rather_than_taking_the_gpu_down(serving):
    """Documented behaviour: a request of more than MAX_BATCH texts is refused with 413 and embeds
    nothing, rather than being silently split or attempted. The builds send 32; a request orders of
    magnitude larger is a caller bug, and one huge padded batch is what runs a 12 GB card out of memory.
    413 is a non-200, so `embed_batch`'s shorten-and-retry path treats it as an EmbedError like any
    other refusal from llama-server."""
    seen = []

    def spy(texts):
        seen.append(texts)
        return fake_embed(texts)

    url = serving(spy, max_batch=4)
    reply = httpx.post(f"{url}/embeddings", json={"input": ["x"] * 5}, timeout=10.0)
    assert reply.status_code == 413
    assert reply.json()["error"]
    assert seen == []
    assert httpx.post(f"{url}/embeddings", json={"input": ["x"] * 4}, timeout=10.0).status_code == 200


def test_an_exception_in_the_embed_function_is_a_500_and_the_server_keeps_answering(serving):
    """A build must see a failed batch as a non-200 (which becomes EmbedError) and never as a hang: the
    lock around the GPU has to be released on the way out of a raising call too."""
    calls = {"n": 0}

    def sometimes(texts):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("CUDA out of memory")
        return fake_embed(texts)

    url = serving(sometimes)
    first = httpx.post(f"{url}/embeddings", json={"input": ["boom"]}, timeout=10.0)
    assert first.status_code == 500
    assert first.json()["error"]
    second = httpx.post(f"{url}/embeddings", json={"input": ["fine"]}, timeout=10.0)
    assert second.status_code == 200
    assert embeddings._vectors_from(second.json()).shape == (1, embeddings.DIMS)


def test_an_unknown_path_is_a_404(serving):
    url = serving(fake_embed)
    assert httpx.get(f"{url}/nope", timeout=5.0).status_code == 404
    assert httpx.post(f"{url}/nope", json={"input": ["a"]}, timeout=5.0).status_code == 404


def test_a_404_post_leaves_a_keep_alive_connection_usable(serving):
    """A reply that does not read the request's body leaves it in the socket, and the next request on
    that connection is parsed starting from the middle of the abandoned JSON. The builds send every
    batch down one keep-alive connection, so one mistyped path would break every batch after it."""
    url = serving(fake_embed)
    with httpx.Client(timeout=10.0) as client:
        assert client.post(f"{url}/nope", json={"input": ["x" * 200] * 20}).status_code == 404
        second = client.post(f"{url}/embeddings", json={"input": ["after the 404"]})
    assert second.status_code == 200
    assert embeddings._vectors_from(second.json()).shape == (1, embeddings.DIMS)


def _raw_post(url: str, headers: str, body: bytes) -> bytes:
    host, port = url.removeprefix("http://").split(":")
    with socket.create_connection((host, int(port)), timeout=10.0) as sock:
        sock.sendall(f"POST /embeddings HTTP/1.1\r\nHost: {host}\r\n{headers}\r\n\r\n".encode() + body)
        sock.settimeout(10.0)
        reply = b""
        while chunk := sock.recv(65536):
            reply += chunk
    return reply


@pytest.mark.parametrize("headers, body", [
    ("Content-Length: not-a-number", b'{"input": ["a"]}'),
    (f"Content-Length: {tool.MAX_BODY + 1}", b'{"input": ["a"]}'),
])
def test_a_request_whose_body_cannot_be_read_ends_the_connection_rather_than_desynchronising(serving, headers, body):
    """A Content-Length that is not a number leaves nowhere for the body to end, and one past MAX_BODY is
    not worth reading. Either way the connection cannot be reused, so the server says so and closes it
    instead of leaving the next request to be parsed out of whatever is left in the socket."""
    reply = _raw_post(serving(fake_embed), headers, body)
    assert reply.split(b"\r\n", 1)[0].split()[1] in (b"400", b"413")
    assert b"close" in reply.lower().split(b"\r\n\r\n", 1)[0]     # Connection: close, and the recv ended


def test_a_cuda_out_of_memory_empties_the_allocator_cache_before_answering(serving, monkeypatch):
    """Whatever the failed batch had allocated stays in torch's caching allocator, so the next batch can
    run out of memory the process is holding and not using. Nothing here imports torch: the handler must
    only reach for it when it is already loaded, which on a real server it is."""
    emptied = []
    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(
        is_available=lambda: True, empty_cache=lambda: emptied.append(True)))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    def out_of_memory(texts):
        raise RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB")

    url = serving(out_of_memory)
    assert httpx.post(f"{url}/embeddings", json={"input": ["boom"]}, timeout=10.0).status_code == 500
    assert emptied == [True]


def test_an_ordinary_failure_does_not_reach_for_the_gpu(serving, monkeypatch):
    emptied = []
    fake_torch = types.SimpleNamespace(cuda=types.SimpleNamespace(
        is_available=lambda: True, empty_cache=lambda: emptied.append(True)))
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    def broken(texts):
        raise ValueError("the tokeniser did not like that")

    url = serving(broken)
    assert httpx.post(f"{url}/embeddings", json={"input": ["boom"]}, timeout=10.0).status_code == 500
    assert emptied == []


def test_embeddings_payload_shapes_a_numpy_array_as_plain_floats():
    """The real embed function hands back a numpy array; the reply has to be JSON, not repr()."""
    payload = tool.embeddings_payload(np.arange(6, dtype=np.float16).reshape(2, 3))
    assert json.loads(json.dumps(payload)) == payload
    assert payload == [{"index": 0, "embedding": [0.0, 1.0, 2.0]},
                       {"index": 1, "embedding": [3.0, 4.0, 5.0]}]


def test_texts_from_rejects_before_any_work_happens():
    with pytest.raises(tool.BadRequest):
        tool.texts_from(b'{"input": []}', max_batch=8)
    assert tool.texts_from(b'{"input": ["a", "b"]}', max_batch=8) == ["a", "b"]


def test_the_docstring_names_the_model_label_the_build_must_record():
    """A build run against this server must be told to record what actually embedded it; the usage
    text at the top of the tool is where anyone starting it finds that out."""
    assert "SOS_EMBED_MODEL=bge-small-en-v1.5-fp16-torch" in tool.__doc__
