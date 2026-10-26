#!/usr/bin/env python3
"""
inspect_excel.py — khảo sát file Excel tri thức Tử Vi và sinh docs/data_dictionary.md

Việc script làm:
  1. Liệt kê sheet, số dòng/cột, vai trò (dùng / bỏ qua) theo column_mapping.yaml
  2. Thống kê từng cột: % có dữ liệu, số giá trị khác nhau, vài giá trị mẫu
  3. Phân bố các cột dạng trạng thái (theo từng sách nếu có Book_Code)
  4. Kiểm tra mapping: sheet/cột trong YAML có tồn tại trong Excel không
  5. Kiểm tra chất lượng: số lượng kỳ vọng, evidence join, review, độ dài text,
     parse số trang, phân bố trust tier

Chạy:
  python scripts/inspect_excel.py \
      --excel data/raw/TuVi_KMS_3Books_CANONICAL_MASTER_DEDUP_v1_0.xlsx \
      --mapping configs/column_mapping.yaml \
      --out docs/data_dictionary.md

Yêu cầu: pandas, openpyxl, pyyaml. Script chỉ ĐỌC Excel, không sửa file.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

MAPPED_SECTIONS = [
    "sources", "source_parts", "knowledge_items", "evidence",
    "id_redirects", "vocabulary", "taxonomy", "extraction_review",
]
BOOK_COL = "Book_Code"


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def esc(value, limit: int = 60) -> str:
    """Làm sạch giá trị để đưa vào ô bảng Markdown."""
    s = str(value).replace("\n", " ").replace("\r", " ").replace("|", "\\|").strip()
    return s if len(s) <= limit else s[: limit - 1] + "…"


def md_table(headers: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(esc(c, 80) for c in r) + " |")
    return lines


def pct(part: float, whole: float) -> str:
    return "0%" if whole == 0 else f"{part / whole * 100:.1f}%"


def load_mapping(path: Path) -> dict | None:
    if yaml is None:
        print("[WARN] Chưa cài pyyaml -> bỏ qua kiểm tra mapping (pip install pyyaml)", file=sys.stderr)
        return None
    if not path.exists():
        print(f"[WARN] Không thấy {path} -> bỏ qua kiểm tra mapping", file=sys.stderr)
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------
# Phần 1-3: mô tả sheet, cột, phân bố
# ----------------------------------------------------------------------------
def sheet_roles(sheets: dict, mapping: dict | None) -> dict[str, str]:
    roles = {name: "chưa phân loại" for name in sheets}
    if not mapping:
        return roles
    for name in mapping.get("sheets_ignored", []):
        if name in roles:
            roles[name] = "bỏ qua"
    for sec in MAPPED_SECTIONS:
        sname = (mapping.get(sec) or {}).get("sheet")
        if sname in roles:
            roles[sname] = f"dùng ({sec})"
    return roles


def describe_columns(df: pd.DataFrame) -> list[list]:
    rows = []
    n = len(df)
    for col in df.columns:
        s = df[col]
        nn = int(s.notna().sum())
        distinct = int(s.nunique(dropna=True))
        samples = " ; ".join(esc(v, 28) for v in s.dropna().unique()[:3])
        rows.append([col, pct(nn, n), distinct, samples])
    return rows


def categorical_sections(name: str, df: pd.DataFrame, max_distinct: int = 15) -> list[str]:
    """Bảng phân bố cho các cột ít giá trị (trạng thái, loại...). Tách theo sách nếu có."""
    if len(df) < 30:
        return []
    out: list[str] = []
    for col in df.columns:
        if col == BOOK_COL:
            continue
        nun = df[col].nunique(dropna=True)
        if not (1 < nun <= max_distinct):
            continue
        vals = df[col].fillna("(trống)")
        if BOOK_COL in df.columns:
            ct = pd.crosstab(vals, df[BOOK_COL].fillna("?"))
            headers = [col] + list(ct.columns)
            rows = [[idx] + [int(v) for v in ct.loc[idx]] for idx in ct.index]
        else:
            vc = vals.value_counts()
            headers, rows = [col, "số dòng"], [[k, int(v)] for k, v in vc.items()]
        out += [f"**{name}.{col}**", ""] + md_table(headers, rows) + [""]
    return out


# ----------------------------------------------------------------------------
# Phần 4: kiểm tra mapping
# ----------------------------------------------------------------------------
def check_mapping(sheets: dict, mapping: dict) -> tuple[list[str], int]:
    problems: list[list] = []
    total = 0
    for sec in MAPPED_SECTIONS:
        cfg = mapping.get(sec)
        if not cfg:
            continue
        sname = cfg["sheet"]
        if sname not in sheets:
            problems.append([sec, sname, "(sheet)", "KHÔNG TỒN TẠI"])
            continue
        for field, col in cfg["columns"].items():
            total += 1
            if col not in sheets[sname].columns:
                problems.append([sec, sname, f"{field} -> {col}", "THIẾU CỘT"])
    lines = [f"Đã kiểm {total} cột được ánh xạ; lỗi: **{len(problems)}**.", ""]
    if problems:
        lines += md_table(["section", "sheet", "trường -> cột", "kết quả"], problems) + [""]
    return lines, len(problems)


# ----------------------------------------------------------------------------
# Phần 5: kiểm tra chất lượng
# ----------------------------------------------------------------------------
def assign_tiers(df: pd.DataFrame, kc: dict, tcfg: dict) -> pd.Series:
    tier = pd.Series([None] * len(df), index=df.index, dtype="object")
    for rule in tcfg["rules"]:
        mask = pd.Series(True, index=df.index)
        for key, val in rule["when"].items():
            contains = key.endswith("_contains")
            field = key[: -len("_contains")] if contains else key
            col = df[kc[field]].fillna("")
            vals = val if isinstance(val, list) else [val]
            m = col.apply(lambda s: any(v in s for v in vals)) if contains else col.isin(vals)
            mask &= m
        tier[mask & tier.isna()] = rule["tier"]
    return tier.fillna(tcfg.get("default_tier", 9))


def quality_checks(sheets: dict, mapping: dict) -> list[str]:
    out: list[str] = []
    ki_cfg = mapping["knowledge_items"]
    kc = ki_cfg["columns"]
    ki = sheets[ki_cfg["sheet"]]
    book = kc["book_code"]

    # 3.1 Số lượng kỳ vọng
    out += ["### 3.1 Số bản ghi active so với kỳ vọng", ""]
    actual = ki.groupby(book).size().to_dict()
    exp = mapping.get("expected_counts", {})
    rows = []
    for b in [k for k in exp if k != "total"]:
        a = actual.get(b, 0)
        rows.append([b, exp[b], a, "OK" if a == exp[b] else "LỆCH"])
    if "total" in exp:
        rows.append(["TỔNG", exp["total"], len(ki), "OK" if len(ki) == exp["total"] else "LỆCH"])
    out += md_table(["sách", "kỳ vọng", "thực tế", "kết quả"], rows) + [""]
    uniq = ki[kc["knowledge_id"]].is_unique
    out += [f"- `{kc['knowledge_id']}` duy nhất: **{'CÓ' if uniq else 'KHÔNG'}**"]
    for f in ki_cfg.get("required", []):
        out += [f"- Cột bắt buộc `{kc[f]}` bị trống: **{int(ki[kc[f]].isna().sum())}** dòng"]
    out += [""]

    # 3.2 Evidence
    out += ["### 3.2 Evidence", ""]
    ev_cfg = mapping["evidence"]
    ec = ev_cfg["columns"]
    ev = sheets[ev_cfg["sheet"]]
    ev_ids = set(ev[ec["knowledge_id"]].dropna())
    covered = ki[kc["knowledge_id"]].isin(ev_ids)
    rows = []
    for b, g in ki.groupby(book):
        rows.append([b, len(g), int(covered[g.index].sum()), pct(covered[g.index].sum(), len(g))])
    out += md_table(["sách", "bản ghi active", "có evidence", "tỷ lệ"], rows) + [""]
    rd_cfg = mapping.get("id_redirects")
    orphan = ev[~ev[ec["knowledge_id"]].isin(ki[kc["knowledge_id"]])]
    if rd_cfg and rd_cfg["sheet"] in sheets:
        redirect_ids = set(sheets[rd_cfg["sheet"]][rd_cfg["columns"]["original_id"]].dropna())
        resolved = int(orphan[ec["knowledge_id"]].isin(redirect_ids).sum())
        out += [f"- Evidence trỏ tới ID không còn active: **{len(orphan)}** "
                f"(tra được qua id_redirects: **{resolved}**)"]
    out += [""]
    for col_field in ["printed_page", "part_number", "pdf_page"]:
        col = ec[col_field]
        rows = [[b, pct(g[col].isna().sum(), len(g)) + " trống"] for b, g in ev.groupby(ec["book_code"])]
        out += [f"**evidence.{col}**", ""] + md_table(["sách", "tỷ lệ trống"], rows) + [""]
    org = ev.groupby([ec["book_code"], ec["origin"]]).size().reset_index()
    out += ["**evidence.origin**", ""] + md_table(["sách", "origin", "số dòng"], org.values.tolist()) + [""]

    # 3.3 Review audit
    out += ["### 3.3 Dấu vết review (sheet extraction)", ""]
    er_cfg = mapping.get("extraction_review")
    if er_cfg and er_cfg["sheet"] in sheets:
        rc = er_cfg["columns"]
        er = sheets[er_cfg["sheet"]]
        rows = []
        for b, g in er.groupby(rc["book_code"]):
            rows.append([b, len(g), int(g[rc["reviewer"]].notna().sum()),
                         int(g[rc["review_date"]].notna().sum())])
        out += md_table(["sách", "dòng", "có Reviewer", "có Review_Date"], rows) + [""]
        out += ["_Nếu cột 'có Reviewer' = 0 thì file chưa có dấu vết người duyệt nào._", ""]
        st = er.groupby([rc["book_code"], rc["review_status"]], dropna=False).size().reset_index()
        out += md_table(["sách", "review_status", "số dòng"], st.fillna("(trống)").values.tolist()) + [""]

    # 3.4 Độ dài text
    out += ["### 3.4 Độ dài `text` (ký tự)", ""]
    short = mapping.get("chunking", {}).get("short_record_chars", 40)
    ln = ki[kc["text"]].fillna("").str.len()
    rows = []
    for b, g in ln.groupby(ki[book]):
        rows.append([b, len(g), int(g.quantile(0.25)), int(g.median()), int(g.quantile(0.75)),
                     int(g.max()), int((g < short).sum())])
    out += md_table(["sách", "n", "p25", "trung vị", "p75", "max", f"<{short} ký tự"], rows) + [""]

    # 3.5 Parse số trang
    out += ["### 3.5 Parse số trang `PDF_Pages`", ""]
    pp = mapping["page_parsing"]
    sep = pp["separator"]
    pats = {k: re.compile(v) for k, v in pp["patterns"].items()}
    bad_rows = []
    for b, g in ki.groupby(book):
        pat = pats.get(b, pats["default"])
        def ok(v, pat=pat):
            if pd.isna(v):
                return False
            return all(pat.fullmatch(p.strip()) for p in str(v).split(sep))
        bad = int((~g[kc["pdf_pages_raw"]].apply(ok)).sum())
        bad_rows.append([b, len(g), bad])
    out += md_table(["sách", "bản ghi", "không parse được"], bad_rows) + [""]

    # 3.6 Trust tier
    out += ["### 3.6 Phân bố trust tier", ""]
    tcfg = mapping["trust_tiers"]
    tiers = assign_tiers(ki, kc, tcfg)
    ct = pd.crosstab(ki[book], tiers)
    enabled = set(tcfg.get("enabled_tiers", []))
    headers = ["sách"] + [f"tier {c}" for c in ct.columns] + ["sẽ index"]
    rows = []
    for b in ct.index:
        idx = sum(int(ct.loc[b, c]) for c in ct.columns if c in enabled)
        rows.append([b] + [int(ct.loc[b, c]) for c in ct.columns] + [idx])
    total_idx = sum(r[-1] for r in rows)
    rows.append(["TỔNG"] + [int(ct[c].sum()) for c in ct.columns] + [total_idx])
    out += md_table(headers, rows) + [""]
    out += [f"enabled_tiers = {sorted(enabled)}", ""]
    for t, d in tcfg.get("definitions", {}).items():
        out += [f"- tier {t}: {d['label']}"]
    out += [""]

    # 3.7 Vocabulary
    out += ["### 3.7 Vocabulary", ""]
    v_cfg = mapping.get("vocabulary")
    if v_cfg and v_cfg["sheet"] in sheets:
        vc = v_cfg["columns"]
        vd = sheets[v_cfg["sheet"]]
        out += [f"- Số dòng: **{len(vd)}**, thuật ngữ khác nhau: **{vd[vc['term']].nunique()}**",
                f"- Dòng có alias: **{pct(vd[vc['aliases']].notna().sum(), len(vd))}**", ""]
        st = vd[vc["status"]].fillna("(trống)").value_counts()
        out += md_table(["status", "số dòng"], [[k, int(v)] for k, v in st.items()]) + [""]
    return out


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--excel", default="data/raw/TuVi_KMS_3Books_CANONICAL_MASTER_DEDUP_v1_0.xlsx")
    ap.add_argument("--mapping", default="configs/column_mapping.yaml")
    ap.add_argument("--out", default="docs/data_dictionary.md")
    args = ap.parse_args()

    excel = Path(args.excel)
    if not excel.exists():
        print(f"[ERROR] Không thấy file Excel: {excel}", file=sys.stderr)
        return 2

    print(f"Đọc {excel.name} ...")
    sheets = pd.read_excel(excel, sheet_name=None, dtype=str)
    mapping = load_mapping(Path(args.mapping))
    roles = sheet_roles(sheets, mapping)

    md: list[str] = [
        "# Data dictionary — KMS Tử Vi",
        "",
        f"- File: `{excel.name}`",
        f"- SHA-256: `{sha256_of(excel)}`",
        f"- Sinh lúc: {datetime.now():%Y-%m-%d %H:%M} (tự động bởi `scripts/inspect_excel.py`, không sửa tay)",
        f"- Số sheet: {len(sheets)}",
        "",
        "## 1. Danh sách sheet",
        "",
    ]
    rows = [[n, len(df), len(df.columns), roles[n]] for n, df in sheets.items()]
    md += md_table(["sheet", "dòng", "cột", "vai trò"], rows) + [""]

    n_problems = 0
    if mapping:
        md += ["## 2. Kiểm tra column_mapping.yaml", ""]
        lines, n_problems = check_mapping(sheets, mapping)
        md += lines
        if n_problems == 0:
            md += ["## 3. Kiểm tra chất lượng dữ liệu", ""]
            try:
                md += quality_checks(sheets, mapping)
            except KeyError as e:
                md += [f"**Lỗi khi kiểm tra chất lượng: thiếu khóa/cột {e}**", ""]
                n_problems += 1
        else:
            md += ["_Sửa mapping trước rồi chạy lại để có phần kiểm tra chất lượng._", ""]

    md += ["## 4. Chi tiết từng sheet", ""]
    for name, df in sheets.items():
        md += [f"### {name}  ({len(df)} dòng, {len(df.columns)} cột — {roles[name]})", ""]
        md += md_table(["cột", "có dữ liệu", "giá trị khác nhau", "ví dụ"], describe_columns(df)) + [""]
        md += categorical_sections(name, df)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Đã ghi {out}  ({'có ' + str(n_problems) + ' lỗi mapping' if n_problems else 'mapping OK'})")
    return 1 if n_problems else 0


if __name__ == "__main__":
    sys.exit(main())
