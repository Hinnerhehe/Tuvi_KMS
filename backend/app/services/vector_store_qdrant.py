"""Qdrant local persistent vector store implementation."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qm

from backend.app.core.config import QDRANT_PATH, EMBEDDING_DIM
from backend.app.db.models import Chunk


class QdrantVectorStore:
    COLLECTION = "kms_chunks"

    def __init__(self):
        self.path = QDRANT_PATH
        self.path.mkdir(parents=True, exist_ok=True)
        self.client = QdrantClient(path=str(self.path))
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.COLLECTION)
        except Exception:
            self.client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=qm.VectorParams(
                    size=EMBEDDING_DIM,
                    distance=qm.Distance.COSINE,
                ),
            )

    def _chunk_id_to_int(self, chunk_id: str) -> int:
        """Chuyển chunk_id thành integer ID cho Qdrant (dùng hash 64-bit)."""
        h = hashlib.sha256(chunk_id.encode()).digest()[:8]
        return int.from_bytes(h, "big", signed=False)

    def upsert(self, chunks: list[Chunk]) -> None:
        points = []
        for c in chunks:
            vec = np.frombuffer(bytes.fromhex(c.embed_text), dtype="float32")
            if vec.shape != (EMBEDDING_DIM,):
                raise ValueError(f"dim mismatch: {vec.shape} vs {EMBEDDING_DIM}")
            points.append(
                qm.PointStruct(
                    id=self._chunk_id_to_int(c.chunk_id),
                    vector=vec.tolist(),
                    payload={
                        "chunk_id": c.chunk_id,
                        "book_code": c.book_code,
                        "chapter": c.chapter,
                        "trust_tier": c.trust_tier,
                    },
                )
            )
        if points:
            self.client.upsert(collection_name=self.COLLECTION, points=points)

    def search(self, query_vec: np.ndarray, top_k: int, book_code: str | None = None):
        query_filter = None
        if book_code:
            query_filter = qm.Filter(
                must=[qm.FieldCondition(key="book_code", match=qm.MatchValue(value=book_code))]
            )
        res = self.client.search(
            collection_name=self.COLLECTION,
            query_vector=query_vec.tolist(),
            limit=top_k,
            query_filter=query_filter,
        )
        return [(p.payload["chunk_id"], p.score) for p in res]

    def delete(self, chunk_ids: list[str]):
        if chunk_ids:
            self.client.delete(
                collection_name=self.COLLECTION,
                points_selector=qm.PointIdsList(
                    points=[self._chunk_id_to_int(cid) for cid in chunk_ids]
                ),
            )

    def count(self) -> int:
        info = self.client.get_collection(self.COLLECTION)
        return info.points_count

    def close(self):
        pass