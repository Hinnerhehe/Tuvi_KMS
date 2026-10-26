"""Sinh embedding index cho toàn bộ RAG chunks.

Usage: python -m scripts.build_index
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import CHUNKS_JSON, DATA_XLSX, EMBED_NPY, INDEX_DIR
from rag.embedder import encode
from rag.loader import KEEP_COLS


def main():
    import pandas as pd

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(DATA_XLSX, sheet_name="RAG_CHUNKS")
    df = df[KEEP_COLS].fillna("")
    chunks = df.to_dict("records")
    print(f"Loaded {len(chunks)} chunks from {DATA_XLSX.name}")

    texts = [c["Embedding_Text"] for c in chunks]
    print("Encoding with multilingual MiniLM ...")
    vecs = np.asarray(encode(texts), dtype="float32")
    print(f"Embeddings shape: {vecs.shape}")

    np.save(EMBED_NPY, vecs)
    with open(CHUNKS_JSON, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=1)

    print(f"Saved {EMBED_NPY}")
    print(f"Saved {CHUNKS_JSON}")


if __name__ == "__main__":
    main()
