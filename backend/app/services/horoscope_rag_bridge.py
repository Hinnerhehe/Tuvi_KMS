"""Horoscope retrieval: whole star names, all queries and explicit source traceability."""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from backend.app.services.horoscope_features import catalog
from backend.app.core.config import DB_PATH

BOOK_FULL_NAMES = {'NPL': 'Nguyễn Phát Lộc', 'DAU': 'Đẩu Số Toàn Thư', 'BD': 'Tử Vi Bửu Đình'}
TOPIC_TITLES = {
    'ban_menh': 'BẢN MỆNH & TÍNH CÁCH CỐT LÕI', 'su_nghiep': 'CÔNG DANH & SỰ NGHIỆP',
    'tai_chinh': 'TÀI CHÍNH & TIỀN BẠC', 'tinh_cam': 'TÌNH CẢM & GIA ĐẠO',
    'van_han': 'VẬN HẠN HIỆN TẠI (ĐẠI HẠN VÀ TIỂU HẠN NĂM)',
}


def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s or '') if unicodedata.category(c) != 'Mn').replace('đ', 'd').replace('Đ', 'D')


def clean_star_name(name: str) -> str:
    return re.sub(r'\s*\([^)]*\)', '', name).strip()


def normalized(s: str) -> str:
    return ' '.join(re.findall(r'\w+', strip_accents(s).lower()))


STAR_NAMES = {s.saoID: s.saoTen for s in vars(catalog).values() if isinstance(s, catalog.Sao)}
STAR_TERMS = {normalized(name) for name in STAR_NAMES.values()}


def mentioned_stars(query: str) -> list[str]:
    q = ' ' + normalized(query) + ' '
    return sorted((name for name in STAR_TERMS if ' ' + name + ' ' in q), key=lambda x: (-len(x), x))


def palace_queries(palace: dict) -> list[str]:
    mains = [s['ten'] for s in palace.get('chinh_tinh', [])]
    risks = [s['ten'] for s in palace.get('risk_stars', palace.get('sat_tinh', []))]
    label = palace.get('ten', '')
    queries = []
    if len(mains) > 1:
        queries.append(' '.join(mains) + ' cung ' + label)
    for risk in risks:
        if mains:
            queries.append(f'{mains[0]} {risk} cung {label}')
        queries.append(f'{risk} cung {label}')
    queries.extend(f'{s} cung {label}' for s in mains)
    for star in palace.get('chinh_tinh', []):
        state = {'H': 'hãm', 'M': 'miếu', 'V': 'vượng', 'Đ': 'đắc địa'}.get(star['dac_tinh'])
        if state:
            queries.append(f"{star['ten']} {state} cung {label}")
    if not mains:
        queries.append(f'Vô Chính Diệu cung {label}')
    if palace.get('tuan_trung'):
        queries.extend(f'{s} Tuần cung {label}' for s in mains)
    if palace.get('triet_lo'):
        queries.extend(f'{s} Triệt cung {label}' for s in mains)
    return list(dict.fromkeys(queries))


def generate_horoscope_queries(features: dict[str, Any]) -> dict[str, list[str]]:
    palaces = {p['ten'].casefold(): p for p in features.get('palaces', [])}
    topics = {key: [] for key in TOPIC_TITLES}
    for key, name in [('ban_menh', 'Mệnh'), ('su_nghiep', 'Quan lộc'), ('tai_chinh', 'Tài bạch'), ('tinh_cam', 'Phu thê')]:
        if name.casefold() in palaces:
            topics[key] = palace_queries(palaces[name.casefold()])
    annual = features.get('nam_xem', {}).get('tieu_han')
    if annual:
        topics['van_han'].extend(palace_queries(annual))
    dh = features.get('dai_han_hien_tai')
    if dh:
        palace = next((p for p in palaces.values() if p['cung_so'] == dh['cung_so']), None)
        if palace:
            topics['van_han'].extend(palace_queries(palace))
    for h in features.get('tu_hoa', []):
        topic = {'HOA_LOC': 'tai_chinh', 'HOA_QUYEN': 'su_nghiep', 'HOA_KHOA': 'su_nghiep', 'HOA_KY': 'ban_menh'}[h['code']]
        topics[topic].append(f"{h['ten']} cung {h['cung_ten']}")
    return {key: list(dict.fromkeys(queries)) for key, queries in topics.items()}


def search_fts_sqlite(query: str, limit: int = 5, book_code: str | None = None,
                      db_path: Path | str | None = None) -> list[dict[str, Any]]:
    path = Path(db_path or DB_PATH)
    if not path.exists():
        return []
    stars = mentioned_stars(query)
    # AND whole names. Never broaden Vu Khuc into isolated "khuc" (Van Khuc).
    anchors = list(stars) or ([normalized(query)] if normalized(query) else [])
    if stars:
        qnorm = ' ' + normalized(query) + ' '
        anchors.extend(flag for flag in ['tuan', 'triet', 'ham', 'mieu', 'vuong', 'dac dia'] if ' ' + flag + ' ' in qnorm)
    if not anchors:
        return []
    match = ' AND '.join('"' + name.replace('"', '""') + '"' for name in anchors)
    sql = '''SELECT c.chunk_id, c.book_code, c.chapter, c.chunk_text, bm25(chunks_fts),
             c.part_number, c.pdf_page_start, c.pdf_page_end, c.trust_tier
             FROM chunks_fts f JOIN chunks c ON c.chunk_id=f.chunk_id
             WHERE chunks_fts MATCH ? AND c.trust_tier IN (1,2,3)'''
    params: list[Any] = [match]
    if book_code:
        sql += ' AND c.book_code=?'
        params.append(book_code)
    sql += ' ORDER BY bm25(chunks_fts) LIMIT ?'
    params.append(limit)
    with sqlite3.connect(f'file:{path.as_posix()}?mode=ro', uri=True) as conn:
        rows = conn.execute(sql, params).fetchall()
    results = []
    for cid, book, chapter, text, score, part, start, end, tier in rows:
        norm = ' ' + normalized(text or '') + ' '
        if any(' ' + star + ' ' not in norm for star in stars):
            continue
        raw = text or ''
        folded = strip_accents(raw).lower()
        positions = [folded.find(star) for star in stars if folded.find(star) >= 0]
        offset = max(0, min(positions, default=0) - 80)
        results.append(dict(chunk_id=cid, book_code=book, chapter=chapter or '', text=raw,
                            excerpt=raw[offset:offset + 500].strip(), score=float(score),
                            part_number=part, pdf_page_start=start, pdf_page_end=end, trust_tier=tier,
                            matched_stars=stars, matched_query=query))
    return results


def retrieve_horoscope_context(features: dict[str, Any], top_k_per_topic: int = 2,
                               db_path: Path | str | None = None) -> dict[str, Any]:
    queries = generate_horoscope_queries(features)
    topics, unique = {}, {}
    query_count = 0
    for topic, query_list in queries.items():
        candidates = {}
        for q in query_list:  # Later risk queries must not be starved by earlier hits.
            query_count += 1
            for hit in search_fts_sqlite(q, limit=4, db_path=db_path):
                rank = (len(hit['matched_stars']), -hit['score'])
                if hit['chunk_id'] not in candidates or rank > candidates[hit['chunk_id']][0]:
                    candidates[hit['chunk_id']] = (rank, hit)
        ranked = [pair[1] for pair in sorted(candidates.values(), key=lambda p: p[0], reverse=True)]
        chosen = ranked[:top_k_per_topic]
        topics[topic] = chosen
        for hit in chosen:
            unique.setdefault(hit['chunk_id'], hit)
        covered = {name for hit in unique.values() for name in mentioned_stars(hit['excerpt'])}
        for hit in ranked:
            if set(hit['matched_stars']) - covered and len(unique) < 22:
                unique.setdefault(hit['chunk_id'], hit)
                covered.update(mentioned_stars(hit['excerpt']))
    references = list(unique.values())
    for i, hit in enumerate(references, 1):
        hit['ref_id'] = i
    for topic, hits in topics.items():
        topics[topic] = [unique[h['chunk_id']] for h in hits]
    return {'topics': topics, 'reference_list': references, 'total_chunks': len(references), 'query_count': query_count}


def format_context_for_prompt(context: dict[str, Any]) -> str:
    lines = [' · '.join(TOPIC_TITLES.values()), 'Nguồn có thể có điều kiện bổ sung chưa khớp lá số. Không coi chỉ nhắc tên sao là đủ chứng cứ.']
    for hit in context.get('reference_list', []):
        lines.append(f"[{hit['ref_id']}] {BOOK_FULL_NAMES.get(hit['book_code'], hit['book_code'])} | {hit.get('chapter', '')}\n{hit.get('excerpt', hit['text'][:500])}")
    return '\n\n'.join(lines)
