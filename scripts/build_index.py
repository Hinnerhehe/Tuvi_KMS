#!/usr/bin/env python3
"""T06 — build_index.py: sinh chunk (T05) + vector index cho KMS Tử Vi.

Luồng:
  1. Đọc knowledge_items đã eligible (trust_tier trong enabled_tiers, có evidence)
  2. Chunk theo quy tắc trong configs/column_mapping.yaml:
     NPL 1 bản ghi = 1 chunk; DAU/BD gộp bản ghi liền kề 150–600 ký tự
  3. Embed từng chunk (model từ .env, mặc định BAAI/bge-m3)
  4. Ghi chunks + chunk_members vào SQLite, vector vào Qdrant/numpy
  5. Xuất data/processed/index_manifest.json

Chạy:
    python scripts/build_index.py                    # toàn bộ
    python scripts/build_index.py --limit 200        # thử nghiệm nhanh
    python scripts/build_index.py --no-embed         # chỉ sinh chunk, chưa embed
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from sqlalchemy import delete, select

from backend.app.core.config import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    MANIFEST_PATH,
    QDRANT_PATH,
    ensure_dirs,
)
from backend.app.db.models import Chunk, ChunkMember, KnowledgeItem
from backend.app.db.session import init_db, session_scope
from backend.app.services.chunker import build_chunks
from backend.app.services.normalize import nfc


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Sinh chunk + vector index")
    ap.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N chunk đầu (0 = tất cả)")
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--no-embed", action="store_true", help="Chỉ ghi chunk, bỏ qua embedding")
    ap.add_argument("--model", type=str, default=None, help="Ghi đè embedding model")
    ap.add_argument(
        "--store", choices=["qdrant", "numpy"], default=None, help="Ghi đè vector store"
    )
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    init_db()

    from backend.app.core import config as cfg
    if args.model:
        cfg.EMBEDDING_MODEL = args.model
    if args.store:
        cfg.VECTOR_STORE = args.store

    print(f"Embedding model: {cfg.EMBEDDING_MODEL}")
    print(f"Vector store   : {cfg.VECTOR_STORE}")
    print("Đang sinh chunk theo quy tắc column_mapping.yaml...")
    t0 = time.time()
    chunk_specs = build_chunks()
    print(f"Sinh {len(chunk_specs)} chunk trong {time.time() - t0:.1f}s")

    per_book: dict[str, int] = {}
    for spec in chunk_specs:
        per_book[spec.book_code] = per_book.get(spec.book_code, 0) + 1
    for book, count in sorted(per_book.items()):
        print(f"  {book}: {count} chunk")

    if args.limit:
        chunk_specs = chunk_specs[: args.limit]
        print(f"Giới hạn: dùng {len(chunk_specs)} chunk đầu")

    # --- embedding ---
    vectors: list[np.ndarray] | None = None
    if not args.no_embed:
        from sentence_transformers import SentenceTransformer

        print("Đang nạp model...")
        model = SentenceTransformer(cfg.EMBEDDING_MODEL, device="cpu")
        dim = model.get_sentence_embedding_dimension()
        print(f"Embedding dim: {dim} (cấu hình: {EMBEDDING_DIM})")

        texts = [c.embed_text for c in chunk_specs]
        vectors = []
        batch = args.batch_size
        started = time.time()
        for i in range(0, len(texts), batch):
            vecs = model.encode(
                texts[i : i + batch], batch_size=batch, normalize_embeddings=True
            )
            vectors.extend(vecs)
            done = min(i + batch, len(texts))
            elapsed = time.time() - started
            rate = done / elapsed if elapsed else 0
            eta = (len(texts) - done) / rate if rate else 0
            print(
                f"  [{done:>5}/{len(texts)}] {elapsed:6.0f}s đã trôi qua, "
                f"{rate:5.1f} chunk/s, còn ~{eta / 60:.1f} phút",
                flush=True,
            )
    else:
        print("Bỏ qua embedding (--no-embed)")

    # --- ghi DB + vector store ---
    store = None
    if vectors is not None:
        from backend.app.services.vector_store import get_vector_store

        store = get_vector_store()
        print(f"Vector store: {type(store).__name__}")

    with session_scope() as session:
        session.execute(delete(Chunk))
        session.execute(delete(ChunkMember))
        session.flush()

        chunk_rows = []
        for i, spec in enumerate(chunk_specs):
            embed_field = (
                np.asarray(vectors[i], dtype="float32").tobytes().hex()
                if vectors is not None
                else ""
            )
            row = Chunk(
                chunk_id=spec.chunk_id,
                book_code=spec.book_code,
                chapter=spec.chapter,
                chunk_text=nfc(spec.embed_text),
                embed_text=embed_field,
                trust_tier=spec.trust_tier,
                part_number=spec.part_number,
                pdf_page_start=spec.pdf_page_start,
                pdf_page_end=spec.pdf_page_end,
                chunking_version=spec.chunking_version,
                embedding_model=cfg.EMBEDDING_MODEL,
                indexed_at=datetime.now(timezone.utc),
                content_hash=spec.content_hash,
            )
            session.add(row)
            chunk_rows.append(row)
            for pos, kid in enumerate(spec.knowledge_ids, start=1):
                session.add(
                    ChunkMember(
                        chunk_id=spec.chunk_id, knowledge_id=kid, position=pos
                    )
                )
        session.flush()

        if store is not None:
            print("Đang ghi vector vào store...")
            store.upsert(chunk_rows)
            print(f"Store hiện có {store.count()} vector")

        total_items = session.query(KnowledgeItem).count()
        print(f"Đã ghi {len(chunk_specs)} chunk + chunk_members vào DB")

        manifest = {
            "embedding_model": cfg.EMBEDDING_MODEL,
            "embedding_dim": (
                int(vectors[0].shape[0]) if vectors is not None and len(vectors) else None
            ),
            "vector_store": cfg.VECTOR_STORE,
            "vectors_indexed": store.count() if store is not None else 0,
            "chunking_version": chunk_specs[0].chunking_version if chunk_specs else None,
            "chunks_per_book": per_book,
            "chunks_built": len(chunk_specs),
            "knowledge_total": total_items,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
