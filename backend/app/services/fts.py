"""T07 — FTS5 keyword search (baseline) với bỏ dấu tiếng Việt.

Chiến lược: lưu bản bỏ dấu trong cột `text_unaccent` để FTS5 match không dấu,
đồng thời giữ `text` có dấu để hiển thị. Truy vấn cũng được bỏ dấu trước khi
truyền vào FTS5 -> "Tu Vi" khớp "tử vi".
"""
from __future__ import annotations

from sqlalchemy import text as sql_text

from backend.app.db.session import engine
from backend.app.services.normalize import strip_accents

FTS_TABLE = "chunks_fts"


def create_fts_table() -> None:
    """Tạo bảng ảo FTS5 nếu chưa có."""
    with engine.begin() as conn:
        conn.execute(
            sql_text(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
                    chunk_id UNINDEXED,
                    book_code UNINDEXED,
                    chapter,
                    text_unaccent,
                    tokenize = 'unicode61 remove_diacritics 2'
                )
                """
            )
        )


def drop_fts_table() -> None:
    with engine.begin() as conn:
        conn.execute(sql_text(f"DROP TABLE IF EXISTS {FTS_TABLE}"))


def rebuild_fts_index() -> int:
    """Xoá và nạp lại toàn bộ chunk vào FTS5. Trả về số dòng đã nạp."""
    from sqlalchemy import select

    from backend.app.db.models import Chunk
    from backend.app.db.session import session_scope

    create_fts_table()
    with session_scope() as session:
        rows = session.execute(
            select(
                Chunk.chunk_id,
                Chunk.book_code,
                Chunk.chapter,
                Chunk.chunk_text,
            )
        ).all()

    with engine.begin() as conn:
        conn.execute(sql_text(f"DELETE FROM {FTS_TABLE}"))
        conn.execute(
            sql_text(
                f"""
                INSERT INTO {FTS_TABLE}(chunk_id, book_code, chapter, text_unaccent)
                VALUES (:cid, :book, :chapter, :text)
                """
            ),
            [
                {
                    "cid": cid,
                    "book": book or "",
                    "chapter": chapter or "",
                    "text": strip_accents(text or ""),
                }
                for cid, book, chapter, text in rows
            ],
        )
    return len(rows)


def search_fts(
    query: str,
    top_k: int = 20,
    book_code: str | None = None,
    trust_tiers: set[int] | None = None,
) -> list[tuple[str, float]]:
    """Tìm bằng FTS5. Trả về (chunk_id, bm25_score) — score càng nhỏ càng tốt."""
    from sqlalchemy import select

    from backend.app.db.models import Chunk

    cleaned = strip_accents(query)
    # FTS5 query: bọc mỗi token trong dấu nháy để tránh lỗi cú pháp
    tokens = [t for t in cleaned.split() if t]
    if not tokens:
        return []
    match_expr = " OR ".join(f'"{t}"' for t in tokens)

    sql = sql_text(
        f"""
        SELECT f.chunk_id, bm25({FTS_TABLE}) AS score
        FROM {FTS_TABLE} f
        JOIN chunks c ON c.chunk_id = f.chunk_id
        WHERE {FTS_TABLE} MATCH :match
        """
    )
    params: dict = {"match": match_expr}
    conditions = []
    if book_code:
        conditions.append("c.book_code = :book")
        params["book"] = book_code
    if trust_tiers:
        placeholders = ",".join(f":t{i}" for i in range(len(trust_tiers)))
        conditions.append(f"c.trust_tier IN ({placeholders})")
        for i, t in enumerate(sorted(trust_tiers)):
            params[f"t{i}"] = t
    if conditions:
        sql = sql_text(
            f"""
            SELECT f.chunk_id, bm25({FTS_TABLE}) AS score
            FROM {FTS_TABLE} f
            JOIN chunks c ON c.chunk_id = f.chunk_id
            WHERE {FTS_TABLE} MATCH :match AND {' AND '.join(conditions)}
            ORDER BY score
            LIMIT :k
            """
        )
        params["k"] = top_k
    else:
        sql = sql_text(
            f"""
            SELECT f.chunk_id, bm25({FTS_TABLE}) AS score
            FROM {FTS_TABLE} f
            JOIN chunks c ON c.chunk_id = f.chunk_id
            WHERE {FTS_TABLE} MATCH :match
            ORDER BY score
            LIMIT :k
            """
        )
        params["k"] = top_k

    with engine.connect() as conn:
        rows = conn.execute(sql, params).all()
    return [(r[0], float(r[1])) for r in rows]


def fts_count() -> int:
    with engine.connect() as conn:
        return conn.execute(sql_text(f"SELECT count(*) FROM {FTS_TABLE}")).scalar() or 0


if __name__ == "__main__":
    n = rebuild_fts_index()
    print(f"Đã nạp {n} chunk vào FTS5")
    for cid, score in search_fts("tu vi", top_k=5):
        print(f"  {cid}  bm25={score:.3f}")
