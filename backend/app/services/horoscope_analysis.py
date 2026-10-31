"""Observable natal facts and explicit source links; no unsupported risk scores."""
from backend.app.services.horoscope_rag_bridge import normalized


def palace_summary(palace: dict | None) -> str:
    if not palace:
        return 'Chưa xác định cung tương ứng.'
    mains = ', '.join(f"{s['ten']} ({s['dac_tinh']})" for s in palace['chinh_tinh']) or 'Vô chính diệu'
    risks = ', '.join(f"{s['ten']} ({s['dac_tinh']})" for s in palace['risk_stars']) or 'không có sao thuộc nhóm cần lưu ý trong danh mục hiện tại'
    supports = ', '.join(s['ten'] for s in palace['cat_tinh']) or 'chưa có cát tinh trong danh mục hiện tại'
    flags = ', '.join(name for key, name in [('tuan_trung', 'Tuần'), ('triet_lo', 'Triệt')] if palace.get(key)) or 'không có Tuần/Triệt'
    return f"{palace['ten']} tại {palace['chuan_ten']}: {mains}. Nhóm cần lưu ý: {risks}. Nhóm hỗ trợ: {supports}. {flags}."


def build_star_facts(features: dict, context: dict) -> list[dict]:
    annual = features.get('nam_xem', {}).get('tieu_han')
    decade = features.get('dai_han_hien_tai') or {}
    important = {'mệnh', 'quan lộc', 'tài bạch', 'phu thê', 'thiên di'}
    facts = []
    for p in features.get('palaces', []):
        roles = []
        if p['cung_so'] == features.get('thong_tin_co_ban', {}).get('cung_than_so'):
            roles.append('Thân cư')
        if annual and p['cung_so'] == annual['cung_so']:
            roles.append(f"Tiểu hạn {features['nam_xem']['year']}")
        if p['cung_so'] == decade.get('cung_so'):
            roles.append('Đại hạn hiện tại')
        if p['ten'].casefold() not in important and not roles:
            continue
        chosen = {}
        for group in ['risk_stars', 'chinh_tinh', 'cat_tinh']:
            for star in p[group]:
                chosen.setdefault(star['id'], (star, group))
        for star, group in chosen.values():
            anchor = ' ' + normalized(star['ten']) + ' '
            refs = [s['ref_id'] for s in context.get('reference_list', [])
                    if anchor in ' ' + normalized(s.get('excerpt', s['text'][:500])) + ' ']
            facts.append({
                'fact_id': f"c{p['cung_so']}_s{star['id']}", 'star_id': star['id'],
                'sao': star['ten'], 'nhom': group, 'dac_tinh': star['dac_tinh'],
                'cung': p['ten'], 'dia_chi': p['chuan_ten'], 'roles': roles,
                'tuan': p['tuan_trung'], 'triet': p['triet_lo'], 'source_refs': refs,
                'source_status': 'Có đoạn nhắc tên sao; cần đối chiếu thêm điều kiện tổ hợp/cung.' if refs else 'Chưa tìm được đoạn sách phù hợp để diễn giải.',
            })
    return facts
