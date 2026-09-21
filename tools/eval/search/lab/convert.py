"""Convert a Hugging Face model to a q8_0 GGUF with the box's own llama.cpp converter (~/llama.cpp, the source of the
installed 0.3.0-dev build). Native architectures only; official weights, no third-party GGUF in the loop.
usage: convert.py <name> ; output scratch/gguf/<name>-q8_0.gguf"""
import subprocess, sys, os
from huggingface_hub import snapshot_download
from common import SCRATCH
from models import EMBED, RERANK

name = sys.argv[1]
hf = {**EMBED, **RERANK}[name]["hf"]
path = snapshot_download(hf, allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja", "tokenizer*", "vocab*", "merges*", "special_tokens*"])
out = SCRATCH / "gguf" / f"{name}-q8_0.gguf"
out.parent.mkdir(exist_ok=True)
env = dict(os.environ, PYTHONPATH=os.path.expanduser("~/llama.cpp/gguf-py"))
r = subprocess.run([sys.executable, os.path.expanduser("~/llama.cpp/convert_hf_to_gguf.py"), path, "--outtype", "q8_0", "--outfile", str(out)],
                   env=env, capture_output=True, text=True)
print(r.stdout[-600:], r.stderr[-1500:])
print("exit", r.returncode, out, out.stat().st_size if out.exists() else None)
