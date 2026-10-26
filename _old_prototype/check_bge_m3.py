"""Kiểm tra khả năng chạy BAAI/bge-m3 trên máy này (RAM 7.4GB, free ~1.2GB).

Đây là cổng chặn T06: nếu không embed được thì phải đổi model.
"""
import os
import sys
import time

# giới hạn thread để tránh tranh chấp RAM/CPU
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

import psutil
from sentence_transformers import SentenceTransformer


def ram_free_gb() -> float:
    return psutil.virtual_memory().available / 1e9


def main():
    print(f"RAM free trước khi nạp: {ram_free_gb():.2f} GB")
    t0 = time.time()
    model = SentenceTransformer("BAAI/bge-m3", device="cpu")
    load_s = time.time() - t0
    print(f"Nạp model: {load_s:.1f}s")
    print(f"RAM free sau khi nạp:  {ram_free_gb():.2f} GB")
    print(f"Embedding dim: {model.get_sentence_embedding_dimension()}")

    # đo tốc độ trên batch nhỏ (corpus 8.680 chunk)
    texts = ["Tử Vi là hệ thống diễn giải vũ trụ."] * 16
    t0 = time.time()
    model.encode(texts, batch_size=8, show_progress_bar=False)
    per = (time.time() - t0) / 16
    print(f"Tốc độ: {per*1000:.0f} ms/chunk -> 8680 chunk mất ~{per*8680/60:.1f} phút")
    print(f"RAM free sau embed:    {ram_free_gb():.2f} GB")


if __name__ == "__main__":
    sys.exit(main())
