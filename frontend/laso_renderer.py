"""Side-effect-free 12-palace component shared by both Streamlit apps."""
from html import escape

CHI_GRID_POS = {
    1: (3, 0), 2: (3, 1), 3: (0, 3), 4: (1, 3), 5: (2, 3),
    6: (0, 2), 7: (0, 1), 8: (0, 0), 9: (1, 0), 10: (2, 0),
    11: (3, 2), 12: (3, 3),
}
GOOD_SAOS = {92, 93, 94, 98, 59, 60, 57, 58, 67, 68, 71, 72, 24, 34, 80}
BAD_SAOS = {51, 52, 53, 54, 55, 56, 95, 99, 104, 21, 36, 30, 69, 70}
DAC_TINH_COLOR = {"M": "#1a7f37", "V": "#2da44e", "Đ": "#0969da", "B": "#57606a", "H": "#cf222e"}


def sao_html(c: dict) -> str:
    parts = []
    for star in c.get("saos", []):
        name = escape(str(star.get("saoTen", "—")))
        if star.get("saoLoai", 2) == 1:
            parts.append(f'<span class="sao chinh">{name}</span>')
            dignity = star.get("saoDacTinh")
            if dignity:
                color = DAC_TINH_COLOR.get(dignity, "#57606a")
                parts.append(f'<span class="qc" style="color:{color}">{escape(str(dignity))}</span>')
        else:
            sid = star.get("saoID")
            cls = "tot" if sid in GOOD_SAOS else "hung" if sid in BAD_SAOS else ""
            parts.append(f'<span class="sao phu {cls}">{name}</span>')
    return " ".join(parts) or '<span class="sao phu">Chưa có sao</span>'


def luoi_html(cacs_cung: list[dict]) -> str:
    """Traditional 4×4 perimeter; CSS makes the same 12 cells a list on phones."""
    cells = {}
    for cung in cacs_cung:
        position = CHI_GRID_POS.get(cung.get("cung_so"))
        if position is None:
            continue
        meta = []
        age = cung.get("tu_dai_han")
        if age is not None:
            meta.append(f"Đại hạn {age}–{age + 9}")
        if cung.get("tieu_han_chi"):
            meta.append(f"Tiểu hạn: {cung['tieu_han_chi']}")
        if cung.get("tuan_trung"):
            meta.append("Tuần")
        if cung.get("triet_lo"):
            meta.append("Triệt")
        title = str(cung.get("ten_cung", "")) + (" (Thân)" if cung.get("co_thanh") else "")
        cells[position] = (
            '<div class="cell">'
            f'<div class="chi">{escape(str(cung.get("chuan_ten", "")))} · {escape(str(cung.get("hanh_cung", "")))}</div>'
            f'<div class="ten">{escape(title)}</div>'
            f'<div class="saos">{sao_html(cung)}</div>'
            f'<div class="meta">{escape(" · ".join(meta))}</div></div>'
        )
    result = []
    for row in range(4):
        for col in range(4):
            result.append(cells.get((row, col), '<div class="cell center" aria-hidden="true"></div>'))
    return '<div class="grid">' + "".join(result) + '</div>'
