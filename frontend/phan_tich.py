"""Phân tích lá số Tử Vi — rule-based, offline, deterministic.

Đọc dữ liệu từ `lap_laso()` (frontend/lasoban.py) và suy ra cấu trúc theo
nguyên tắc Tử Vi truyền thống: chủ mệnh, tứ hóa, tuần/triệt, đại hạn và
các cung chính.

Phạm vi: mô tả cấu trúc sao + ý nghĩa theo lý thuyết, mang tính tham khảo;
không đưa khuyến nghị cá nhân về y tế/tài chính/pháp luật.
"""
from __future__ import annotations

# saoID -> (ten, mot dong dac trung)
CHINH_TINH = {
    1: ("Tử vi", "trung tâm, có ý dẫn dắt, phẩm cách, vị thế"),
    2: ("Liêm trinh", "nghiêm khắc, nguyên tắc, rèn giũa"),
    3: ("Thiên đồng", "tương thân, an nhàn, trọng tình cảm, hợp tác"),
    4: ("Vũ khúc", "tài chính, kỹ năng, kiên định, trọng thực tế"),
    5: ("Thái dương", "quảng bá, hào sảng, chủ danh tiếng, con trai"),
    6: ("Thiên cơ", "duyên, kế hoạch, linh hoạt, hay suy tính"),
    8: ("Thái âm", "nội tại, nữ giới, chủ mẫu hệ, bất động sản"),
    9: ("Tham lang", "tài hoa, xã hội, tham vọng, nhiều mối quan hệ"),
    10: ("Cự môn", "thảo đạt, chuyên môn, trọng khẩu thiệt"),
    11: ("Thiên tướng", "hỗ trợ, nghĩa khí, hợp làm việc nhóm"),
    12: ("Thiên lương", "bảo hộ, hòa giải, phúc đức, ổn định"),
    13: ("Thất sát", "quyết đoán, hành động, năng động, biến đổi"),
    14: ("Phá quân", "đột phá, cải cách, biến động lớn"),
}

# saoID tu hoa -> (ten, nghia)
TU_HOA = {
    94: ("Hóa lộc", "cơ hội tăng trưởng, của cải, quý nhân"),
    93: ("Hóa quyền", "quyền lực, quyết đoán, chủ động dẫn dắt"),
    92: ("Hóa khoa", "danh tiếng, học vấn, vẻ ngoài, may mắn"),
    95: ("Hóa kỵ", "điểm nghẽn, nghĩa vụ, mất mát, cần chú tâm"),
}

# ten cung -> linh vuc
DOMAIN = {
    "Mệnh": "bản chất, tinh thần, tổng cục",
    "Phụ mẫu": "cha mẹ, cấp trên, người hướng dẫn",
    "Phúc đức": "đời sống tinh thần, phúc phận, tuổi tác",
    "Điền trạch": "gia cư, bất động sản, người thân trong nhà",
    "Quan lộc": "sự nghiệp, công việc, tiền đồ",
    "Nô bộc": "bạn bè, đồng nghiệp, cộng tác viên",
    "Thiên di": "xa nhà, xã hội, môi trường bên ngoài",
    "Tật Ách": "sức khỏe, bệnh tật, tai ương",
    "Tài Bạch": "tài chính, tiền bạc, thu chi",
    "Tử tức": "con cái, học trò, đời sống riêng tư",
    "Phu thê": "hôn nhân, tình cảm, bạn đời",
    "Huynh đệ": "anh chị em, bằng hữu",
}


def _chinh(c: dict) -> list[dict]:
    """Các chính tinh trong một cung."""
    return [s for s in c.get("saos", []) if s.get("saoLoai") == 1]


def phan_tich(info: dict) -> dict:
    """Suy phân tích từ dict lá số do lap_laso() trả về."""
    cung = info["thap_ni_cung"]
    by_name = {c["ten_cung"]: c for c in cung}

    # --- Chủ mệnh ---
    menh = by_name.get("Mệnh", {})
    m_ct = _chinh(menh)
    if m_ct:
        chua_menh = " · ".join(
            f'{s["saoTen"]} ({s.get("saoDacTinh") or "—"})' for s in m_ct
        )
        chua_menh_nghia = " ".join(
            CHINH_TINH.get(s["saoID"], ("", ""))[1] for s in m_ct
        ).strip()
    else:
        chua_menh = "Vô chính diệu (mượn đối cung)"
        chua_menh_nghia = ("Cung mệnh không có chính tinh; "
                          "xem sao ở cung Thiên di làm chủ.")

    # --- Tứ hóa ---
    tu_hoa = []
    for sid, (ten, nghia) in TU_HOA.items():
        hit = next((c for c in cung
                    if any(s.get("saoID") == sid for s in c["saos"])), None)
        if hit:
            dong = [s["saoTen"] for s in _chinh(hit)]
            tu_hoa.append({
                "ten": ten,
                "nghia": nghia,
                "cung": hit["chuan_ten"],
                "linh_vuc": DOMAIN.get(hit["ten_cung"], ""),
                "dong_cung": " · ".join(dong)
                if dong else "độc hành (không kèm chính tinh)",
            })

    # --- Tuần / Triệt ---
    tuan = [c["chuan_ten"] for c in cung if c["tuan_trung"]]
    triet = [c["chuan_ten"] for c in cung if c["triet_lo"]]

    # --- Đại hạn (mỗi đại hạn 10 năm, xếp theo tuổi khởi hạn) ---
    dai_han = [{
        "tu": c["tu_dai_han"],
        "den": c["tu_dai_han"] + 9,
        "cung": c["chuan_ten"],
        "linh_vuc": DOMAIN.get(c["ten_cung"], ""),
        "sao": " · ".join(s["saoTen"] for s in _chinh(c)) or "vô chính diệu",
    } for c in sorted(
        (c for c in cung if c.get("tu_dai_han") is not None),
        key=lambda c: c["tu_dai_han"],
    )]

    # --- Các cung chính ---
    quan_trong = []
    for ten_cung in ["Quan lộc", "Tài Bạch", "Phu thê", "Thiên di", "Tật Ách"]:
        c = by_name.get(ten_cung)
        if not c:
            continue
        ct = _chinh(c)
        quan_trong.append({
            "linh_vuc": ten_cung,
            "cung": c["chuan_ten"],
            "sao": " · ".join(
                f'{s["saoTen"]} ({s.get("saoDacTinh") or "—"})'
                for s in ct
            ) or "vô chính diệu",
            "nghia": " ".join(
                CHINH_TINH.get(s["saoID"], ("", ""))[1] for s in ct
            ).strip(),
        })

    return {
        "chua_menh": chua_menh,
        "chua_menh_nghia": chua_menh_nghia,
        "tu_hoa": tu_hoa,
        "tuan": tuan,
        "triet": triet,
        "dai_han": dai_han,
        "quan_trong": quan_trong,
    }


def phan_tich_html(res: dict) -> str:
    """HTML cho khối phân tích (dùng st.markdown unsafe_allow_html)."""
    out = ['<div class="phan-tich">']

    out.append('<h3>Chủ mệnh</h3>')
    out.append(f'<p><b>{res["chua_menh"]}</b> — '
               f'{res["chua_menh_nghia"] or "—"}</p>')

    out.append('<h3>Tứ hóa · Lộc — Quyền — Khoa — Kỵ</h3><table>')
    out.append("<tr><th>Sao</th><th>Cung</th><th>Lĩnh vực</th>"
               "<th>Đồng cung</th><th>Ý nghĩa</th></tr>")
    for r in res["tu_hoa"]:
        out.append(
            f'<tr><td><b>{r["ten"]}</b></td><td>{r["cung"]}</td>'
            f'<td>{r["linh_vuc"]}</td><td>{r["dong_cung"]}</td>'
            f'<td>{r["nghia"]}</td></tr>'
        )
    out.append("</table>")

    out.append("<h3>Tuần – Triệt</h3>")
    out.append(
        f'<p>Tuần: {", ".join(res["tuan"]) or "—"} · '
        f'Triệt: {", ".join(res["triet"]) or "—"}</p>'
    )

    out.append('<h3>Đại hạn (mỗi đại hạn 10 năm)</h3><table>')
    out.append("<tr><th>Độ tuổi</th><th>Cung</th><th>Lĩnh vực</th>"
               "<th>Chính tinh</th></tr>")
    for r in res["dai_han"]:
        out.append(
            f'<tr><td>{r["tu"]}–{r["den"]}</td><td>{r["cung"]}</td>'
            f'<td>{r["linh_vuc"]}</td><td>{r["sao"]}</td></tr>'
        )
    out.append("</table>")

    out.append('<h3>Các cung chính</h3><table>')
    out.append("<tr><th>Lĩnh vực</th><th>Cung</th><th>Chính tinh</th>"
               "<th>Đặc trưng</th></tr>")
    for r in res["quan_trong"]:
        out.append(
            f'<tr><td>{r["linh_vuc"]}</td><td>{r["cung"]}</td>'
            f'<td>{r["sao"]}</td><td>{r["nghia"] or "—"}</td></tr>'
        )
    out.append("</table>")

    out.append('<p class="foot">Nội dung suy ra từ cấu trúc sao theo lý '
               'thuyết Tử Vi truyền thống (nguồn: lasotuvi, MIT); mang tính '
               'tham khảo, không thay thế quyết định cá nhân.</p>')
    out.append("</div>")
    return "".join(out)
