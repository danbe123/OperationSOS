"""Models skipped because their config.json names custom code (auto_map => trust_remote_code). Only config.json is fetched."""
import json
from huggingface_hub import hf_hub_download
from common import dump
out = {}
for r in ("nomic-ai/nomic-embed-text-v1.5", "nomic-ai/nomic-embed-text-v1", "Alibaba-NLP/gte-base-en-v1.5", "jinaai/jina-embeddings-v2-base-en", "jinaai/jina-embeddings-v2-small-en",
          "Snowflake/snowflake-arctic-embed-m-v2.0", "Snowflake/snowflake-arctic-embed-m-long", "Alibaba-NLP/gte-large-en-v1.5", "jinaai/jina-reranker-v1-tiny-en", "jinaai/jina-reranker-v1-turbo-en"):
    try:
        c = json.load(open(hf_hub_download(r, "config.json")))
        out[r] = {"auto_map": c.get("auto_map"), "architectures": c.get("architectures"), "needs_remote_code": bool(c.get("auto_map"))}
    except Exception as e:
        out[r] = {"error": repr(e)[:120]}
    print(r, out[r].get("needs_remote_code"), out[r].get("architectures"))
dump("skipped_remote_code.json", out)
