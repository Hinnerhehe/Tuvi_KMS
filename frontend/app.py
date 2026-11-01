"""T14 — Giao diện Streamlit cho KMS Tử Vi.

Ba tab:
  1. Tra cứu  — tìm kiếm từ khóa (FTS5 bỏ dấu), kết quả tách theo sách,
                 badge Trust Tier và số trang PDF.
  2. Hỏi đáp  — gọi /api/v1/chat/ask, trả lời có dẫn nguồn [1], [2].
  3. Thống kê — tổng số bản ghi và phân bố Trust Tier.

Chạy:
    uvicorn backend.app.main:app --reload --port 8000   # terminal 1
    streamlit run frontend/app.py                        # terminal 2
"""
from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_BASE = os.getenv("KMS_API_BASE", "https://tuvi-kms-backend.onrender.com").rstrip("/")
TIMEOUT = 120

BOOK_TITLES = {
    "NPL": "Nguyễn Phát Lộc",
    "DAU": "Tử Vi Đẩu Số Toàn Thư",
    "BD": "Tử Vi Ứng Dụng — Bửu Đình",
}

# màu badge theo trust tier (dùng cho chip trong UI)
TIER_COLORS = {1: "#1a7f37", 2: "#0969da", 3: "#bf8700", 9: "#82061e"}

st.set_page_config(
    page_title="KMS Tử Vi",
    page_icon="☯",
    layout="wide",
)


# --------------------------------------------------------------------------
# gọi API
# --------------------------------------------------------------------------
def api_get(path: str) -> dict[str, Any] | None:
    try:
        resp = requests.get(f"{API_BASE}{path}", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"Không gọi được API tại {API_BASE}{path}: {exc}")
        return None


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    try:
        resp = requests.post(f"{API_BASE}{path}", json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"Không gọi được API tại {API_BASE}{path}: {exc}")
        return None


def tier_badge(tier: int, badge: str | None) -> str:
    color = TIER_COLORS.get(tier, "#57606a")
    label = badge or f"Tier {tier}"
    return (
        f'<span style="background:{color}22;border:1px solid {color};color:{color};'
        f'border-radius:10px;padding:1px 8px;font-size:12px;white-space:nowrap">'
        f"Tier {tier} · {label}</span>"
    )


def book_chip(book_code: str) -> str:
    return f"**{book_code}** — {BOOK_TITLES.get(book_code, book_code)}"


def page_label(c: dict) -> str:
    """Dựng nhãn trang theo quy ước: 'Phần N, PDF tr. X' cho BD, 'PDF tr. X' cho NPL/DAU."""
    page = c.get("pdf_page_start")
    if page is None:
        return "trang không xác định"
    part = c.get("part_number")
    if c.get("book_code") == "BD" and part:
        return f"Phần {part}, PDF tr. {page}"
    return f"PDF tr. {page}"


# --------------------------------------------------------------------------
# sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ☯ KMS Tử Vi")
    st.caption("Tra cứu tri thức Tử Vi từ 3 sách nguồn, có dẫn nguồn.")
    st.caption(f"API: `{API_BASE}`")

    health = api_get("/api/v1/health")
    if health and health.get("status") == "ok":
        st.success(
            f"DB: {health['knowledge_items']:,} bản ghi · {health['chunks']:,} chunk"
        )
    else:
        st.error(
            f"Không kết nối được backend. Hãy chạy:\n\n"
            f"`uvicorn backend.app.main:app --port 8000`"
        )


# --------------------------------------------------------------------------
# tiêu đề + tab
# --------------------------------------------------------------------------
st.title("KMS Tử Vi")
tab_search, tab_chat, tab_stats = st.tabs(["🔎 Tra cứu", "💬 Hỏi đáp RAG", "📊 Thống kê"])


# --------------------------------------------------------------------------
# TAB 1 — Tra cứu
# --------------------------------------------------------------------------
with tab_search:
    st.markdown(
        "Tìm kiếm từ khóa trong nội dung ba sách. Tìm kiếm **không phân biệt dấu**, "
        'nên "tu vi" khớp "Tử Vi".'
    )

    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        query = st.text_input(
            "Từ khóa", placeholder="VD: sao Thiên Phủ, khoa bảng, địa chi", label_visibility="collapsed"
        )
    with c2:
        top_k = st.number_input("Số kết quả", min_value=1, max_value=30, value=10, step=1)
    with c3:
        st.write("")
        st.write("")
        do_search = st.button("Tìm kiếm", type="primary", use_container_width=True)

    if do_search:
        if not query.strip():
            st.warning("Nhập từ khóa cần tìm.")
        else:
            with st.spinner("Đang tìm..."):
                data = api_post(
                    "/api/v1/search",
                    {
                        "query": query,
                        "top_k": int(top_k),
                        "use_dense": False,
                        "use_fts": True,
                    },
                )

            if data:
                if data.get("status") != "ok" or not data.get("results"):
                    st.info("Không tìm thấy kết quả nào.")
                else:
                    meta = data.get("meta", {})
                    st.caption(
                        f"{meta.get('count', 0)} kết quả · sách: "
                        f"{', '.join(meta.get('books', []))} · "
                        f"tier được bật: {meta.get('enabled_tiers', [])}"
                    )

                    # gom kết quả theo sách để "tách NPL / DAU / BD"
                    by_book: dict[str, list[dict]] = {}
                    for r in data["results"]:
                        by_book.setdefault(r["book_code"], []).append(r)

                    for book_code in ["NPL", "DAU", "BD"]:
                        if book_code not in by_book:
                            continue
                        with st.expander(
                            f"{BOOK_TITLES.get(book_code, book_code)} ({book_code})"
                            f" — {len(by_book[book_code])} kết quả",
                            expanded=True,
                        ):
                            for r in by_book[book_code]:
                                st.markdown(
                                    f"**[{r.get('index', '?')}] {r.get('chapter') or '—'}**"
                                )
                                st.markdown(
                                    f"{tier_badge(r['trust_tier'], r.get('ui_badge'))}"
                                    f" &nbsp;|&nbsp; `{r.get('page_label', '')}`"
                                    f" &nbsp;|&nbsp; mức tin cậy tier {r['trust_tier']}"
                                )
                                st.write(r.get("text", ""))
                                st.caption(
                                    f"chunk `{r.get('chunk_id')}` · "
                                    f"bản ghi: {', '.join(r.get('knowledge_ids', []))}"
                                )
                                st.divider()


# --------------------------------------------------------------------------
# TAB 2 — Hỏi đáp RAG
# --------------------------------------------------------------------------
with tab_chat:
    st.markdown(
        "Hỏi đáp dựa trên nội dung đã truy xuất từ ba sách. Câu trả lời **tách theo từng sách** "
        "và có dẫn nguồn `[1]`, `[2]`."
    )

    with st.expander("Gợi ý câu hỏi", expanded=False):
        st.markdown(
            "- Sao Thiên Phủ được giải nghĩa thế nào?\n"
            "- Cách khoa bảng được nói đến ở đâu?\n"
            "- So sánh cách giải thích của các sách về sao Tử Vi"
        )

    c1, c2 = st.columns([4, 1])
    with c1:
        question = st.text_area(
            "Câu hỏi",
            placeholder="VD: Sao Thiên Phủ được giải nghĩa thế nào?",
            height=90,
            label_visibility="collapsed",
        )
    with c2:
        st.write("")
        rag_top_k = st.number_input("Số nguồn", min_value=1, max_value=12, value=5, step=1)
        st.write("")
        do_ask = st.button("Hỏi", type="primary", use_container_width=True)

    if do_ask:
        if not question.strip():
            st.warning("Nhập câu hỏi.")
        else:
            with st.spinner("Đang truy xuất và tổng hợp..."):
                data = api_post(
                    "/api/v1/chat/ask",
                    {"question": question, "top_k": int(rag_top_k)},
                )

            if data:
                status = data.get("status", "error")
                answer = data.get("answer", "")

                if status == "answered":
                    st.markdown(answer)
                elif status == "out_of_scope":
                    st.warning(answer)
                elif status == "insufficient_evidence":
                    st.info(answer)
                else:
                    st.error(answer or "Không tạo được câu trả lời.")

                if data.get("message"):
                    st.caption(f"Thông báo hệ thống: {data['message']}")

                retr = data.get("retrieval", {})
                if retr:
                    st.caption(
                        f"Ứng viên: {retr.get('num_candidates', 0)} · "
                        f"ngữ cảnh dùng: {retr.get('num_contexts', 0)} · "
                        f"sách phủ: {', '.join(retr.get('books_covered', [])) or '—'}"
                    )

                # thẻ nguồn
                citations = data.get("citations", [])
                if citations:
                    st.subheader("Nguồn trích dẫn")
                    for c in citations:
                        with st.container(border=True):
                            st.markdown(
                                f"**[{c['ref']}] {c.get('book_title') or c['book_code']}** "
                                f"({c['book_code']})"
                            )
                            st.markdown(page_label(c))
                            st.markdown(
                                f"{tier_badge(c['trust_tier'], c.get('ui_badge'))}"
                            )
                            st.caption(
                                f"bản ghi: {', '.join(c.get('knowledge_ids', []))} · "
                                f"xác minh: {c.get('verification_status', 'unverified')}"
                            )
                            st.write(c.get("excerpt", ""))


# --------------------------------------------------------------------------
# TAB 3 — Thống kê
# --------------------------------------------------------------------------
with tab_stats:
    st.markdown("Tổng số bản ghi và phân bố Trust Tier.")

    data = api_get("/api/v1/stats")
    if not data or data.get("status") != "ok":
        st.error("Không lấy được dữ liệu thống kê.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng bản ghi", f"{data.get('total_records', 0):,}")
        c2.metric("Chunk đã index", f"{data.get('chunks', 0):,}")
        c3.metric("Dòng chỉ mục FTS5", f"{data.get('fts_rows', 0):,}")

        st.subheader("Phân bố Trust Tier")
        tiers = data.get("by_tier", [])
        if tiers:
            rows = []
            for t in tiers:
                rows.append(
                    {
                        "Trust Tier": t["trust_tier"],
                        "Số bản ghi": t["count"],
                        "Nhãn": t["label"],
                        "Badge UI": t["ui_badge"],
                        "Được index": "Có" if t["enabled"] else "Không",
                    }
                )
            st.dataframe(rows, use_container_width=True, hide_index=True)

            # thanh phân bố
            try:
                import pandas as pd

                df = pd.DataFrame(rows)
                st.bar_chart(df.set_index("Trust Tier")["Số bản ghi"])
            except Exception:
                pass

            st.caption(
                "Tier 9 = loại khỏi index cho đến khi review. "
                "Mọi bản ghi đều ở trạng thái `unverified` — chưa có dấu vết duyệt thủ công."
            )

        st.subheader("Phân bố theo sách")
        books = data.get("by_book", [])
        if books:
            st.dataframe(
                [{"Mã sách": b["book_code"], "Tên sách": BOOK_TITLES.get(b["book_code"], ""), "Số bản ghi": b["count"]} for b in books],
                use_container_width=True,
                hide_index=True,
            )
