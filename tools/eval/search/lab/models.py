"""The model registry: each model's documented pooling and prefixes (verified against the repo's own
sentence-transformers config by cards.py, which writes results/model_cards.json)."""
QP = "Represent this sentence for searching relevant passages: "

EMBED = {
    # name: hf id, pooling, query prefix, passage prefix
    "bge-small-en-v1.5":   dict(hf="BAAI/bge-small-en-v1.5", pool="cls", qp=QP, pp="", control=True),
    "bge-base-en-v1.5":    dict(hf="BAAI/bge-base-en-v1.5", pool="cls", qp=QP, pp=""),
    "bge-large-en-v1.5":   dict(hf="BAAI/bge-large-en-v1.5", pool="cls", qp=QP, pp="", upper=True),
    "e5-small-v2":         dict(hf="intfloat/e5-small-v2", pool="mean", qp="query: ", pp="passage: "),
    "e5-base-v2":          dict(hf="intfloat/e5-base-v2", pool="mean", qp="query: ", pp="passage: "),
    "all-MiniLM-L12-v2":   dict(hf="sentence-transformers/all-MiniLM-L12-v2", pool="mean", qp="", pp=""),
    "arctic-embed-s":      dict(hf="Snowflake/snowflake-arctic-embed-s", pool="cls", qp=QP, pp=""),
    "arctic-embed-m":      dict(hf="Snowflake/snowflake-arctic-embed-m", pool="cls", qp=QP, pp=""),
    "arctic-embed-m-v1.5": dict(hf="Snowflake/snowflake-arctic-embed-m-v1.5", pool="cls", qp=QP, pp=""),
    "mxbai-embed-large-v1": dict(hf="mixedbread-ai/mxbai-embed-large-v1", pool="cls", qp=QP, pp="", upper=True),
    "mxbai-embed-xsmall-v1": dict(hf="mixedbread-ai/mxbai-embed-xsmall-v1", pool="cls", qp=QP, pp=""),
    "granite-embedding-small-english-r2": dict(hf="ibm-granite/granite-embedding-small-english-r2", pool="cls", qp="", pp=""),
    "granite-embedding-english-r2": dict(hf="ibm-granite/granite-embedding-english-r2", pool="cls", qp="", pp=""),
    "gte-small":           dict(hf="thenlper/gte-small", pool="mean", qp="", pp=""),
    "gte-base":            dict(hf="thenlper/gte-base", pool="mean", qp="", pp=""),
    "multi-qa-MiniLM-L6-cos-v1": dict(hf="sentence-transformers/multi-qa-MiniLM-L6-cos-v1", pool="mean", qp="", pp=""),
    "all-mpnet-base-v2":   dict(hf="sentence-transformers/all-mpnet-base-v2", pool="mean", qp="", pp=""),
}

RERANK = {
    "bge-reranker-base":       dict(hf="BAAI/bge-reranker-base"),
    "bge-reranker-v2-m3":      dict(hf="BAAI/bge-reranker-v2-m3"),
    "ms-marco-MiniLM-L-6-v2":  dict(hf="cross-encoder/ms-marco-MiniLM-L-6-v2"),
    "ms-marco-MiniLM-L-12-v2": dict(hf="cross-encoder/ms-marco-MiniLM-L-12-v2"),
    "mxbai-rerank-xsmall-v1":  dict(hf="mixedbread-ai/mxbai-rerank-xsmall-v1"),
    "gte-reranker-modernbert-base": dict(hf="Alibaba-NLP/gte-reranker-modernbert-base"),
    "mxbai-rerank-base-v1":    dict(hf="mixedbread-ai/mxbai-rerank-base-v1"),
}
