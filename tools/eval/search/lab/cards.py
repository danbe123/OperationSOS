"""Fetch each candidate's small config files (no weights) to record and check pooling, prefixes, architecture,
custom-code needs (auto_map -> trust_remote_code) and repo size. Writes results/model_cards.json."""
import json, sys
from huggingface_hub import HfApi, hf_hub_download
from common import dump
from models import EMBED, RERANK

api = HfApi()
out = {}
for name, cfg in {**EMBED, **RERANK}.items():
    hf = cfg["hf"]
    rec = {"hf": hf}
    try:
        info = api.model_info(hf, files_metadata=True)
        sib = info.siblings or []
        rec["files"] = {s.rfilename: s.size for s in sib if s.size and s.rfilename.endswith((".safetensors", ".bin", ".onnx", ".gguf"))}
        rec["license"] = next((t.split(":", 1)[1] for t in (info.tags or []) if t.startswith("license:")), None)
        rec["params_safetensors"] = (info.safetensors.total if info.safetensors else None)
    except Exception as e:
        rec["info_error"] = repr(e)[:200]
    for fname in ("config.json", "modules.json", "1_Pooling/config.json", "config_sentence_transformers.json", "sentence_bert_config.json"):
        try:
            p = hf_hub_download(hf, fname)
            rec[fname] = json.load(open(p))
        except Exception:
            pass
    c = rec.get("config.json", {})
    rec["architectures"] = c.get("architectures")
    rec["needs_remote_code"] = bool(c.get("auto_map"))
    out[name] = rec
    print(name, rec.get("architectures"), "remote" if rec["needs_remote_code"] else "native", rec.get("params_safetensors"),
          rec.get("1_Pooling/config.json", {}) and {k: v for k, v in rec["1_Pooling/config.json"].items() if v is True or k=="pooling_mode_cls_token"},
          (rec.get("config_sentence_transformers.json") or {}).get("prompts"), flush=True)
dump("model_cards.json", out)
