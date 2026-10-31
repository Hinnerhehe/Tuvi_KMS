"""One orchestration path for JSON and progress-stream endpoints."""
from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from uuid import uuid4

from backend.app.schemas.horoscope import HoroscopeRequest
from backend.app.core.config import HOROSCOPE_TIMEOUT_SECONDS
from backend.app.services.horoscope_features import generate_raw_horoscope, extract_horoscope_features
from backend.app.services.horoscope_rag_bridge import retrieve_horoscope_context, format_context_for_prompt
from backend.app.services.horoscope_analysis import build_star_facts
from backend.app.services.horoscope_interpreter import interpret_horoscope, HoroscopeGenerationError
from backend.app.services.pages import format_page_label

logger = logging.getLogger(__name__)


def reading_events(req: HoroscopeRequest):
    started = time.perf_counter()
    timings = {}
    request_id = str(uuid4())
    def progress(stage, message):
        return {'event': 'progress', 'stage': stage, 'message': message,
                'elapsed_ms': round((time.perf_counter() - started) * 1000, 1), 'request_id': request_id}
    try:
        yield progress('chart', 'Đang lập lá số và xác định cung tiểu hạn…')
        mark = time.perf_counter()
        raw = generate_raw_horoscope(req.ngay, req.thang, req.nam, req.chi_gio, req.gioi_tinh, req.duong_lich)
        features = extract_horoscope_features(raw, req.target_year)
        timings['chart'] = round((time.perf_counter() - mark) * 1000, 1)
        yield progress('retrieval', 'Đã lập lá số. Đang tìm nguồn theo tên sao và tổ hợp…')
        mark = time.perf_counter()
        context = retrieve_horoscope_context(features, req.top_k_per_topic)
        facts = build_star_facts(features, context)
        timings['retrieval'] = round((time.perf_counter() - mark) * 1000, 1)
        citations = [{
            'ref_id': s['ref_id'], 'chunk_id': s['chunk_id'], 'book_code': s['book_code'],
            'chapter': s.get('chapter', ''), 'part_number': s.get('part_number'),
            'pdf_page_start': s.get('pdf_page_start'), 'pdf_page_end': s.get('pdf_page_end'),
            'page_label': format_page_label(s['book_code'], s.get('part_number'), s.get('pdf_page_start')),
            'trust_tier': s.get('trust_tier'), 'verification_status': 'unverified',
            'excerpt': s.get('excerpt', s['text'][:500]), 'matched_query': s.get('matched_query', ''),
        } for s in context['reference_list']]
        report = {
            'status': 'ok', 'ho_ten': req.ho_ten or 'Người Xem',
            'thong_tin_co_ban': features['thong_tin_co_ban'], 'reading': {},
            'la_so': {'thap_ni_cung': raw['thap_ni_cung']}, 'citations': citations,
            'star_analysis': facts, 'annual': features['nam_xem'], 'palaces': features['palaces'],
            'meta': {'request_id': request_id, 'provider': req.provider, 'target_year': features['nam_xem']['year'],
                     'total_chunks_retrieved': len(citations), 'queries_evaluated': context['query_count']},
        }
        yield {'event': 'prepared', 'report': report}
        yield progress('generation', f"Đã có {len(citations)} nguồn. Đang tạo bài đọc; AI chờ tối đa {HOROSCOPE_TIMEOUT_SECONDS:g} giây, không thử lại tự động.")
        mark = time.perf_counter()
        # Heartbeats report real elapsed time while the single bounded request runs.
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(interpret_horoscope, features, format_context_for_prompt(context), req.provider, context)
            while True:
                try:
                    reading = future.result(timeout=1)
                    break
                except FutureTimeout:
                    yield progress('generation', 'Đang chờ Gemini tổng hợp; dữ kiện lá số đã sẵn sàng bên dưới.')
        timings['generation'] = round((time.perf_counter() - mark) * 1000, 1)
        timings['total'] = round((time.perf_counter() - started) * 1000, 1)
        generation = reading.pop('_generation')
        report = {**report, 'reading': reading, 'meta': {**report['meta'], **generation, 'timings_ms': timings}}
        logger.info('horoscope_read request_id=%s provider=%s reason=%s timings_ms=%s', request_id, generation['actual_provider'], generation['reason'], timings)
        yield {'event': 'result', 'report': report}
    except HoroscopeGenerationError as exc:
        yield {'event': 'error', 'code': exc.code, 'message': str(exc), 'request_id': request_id}
    except Exception:
        logger.exception('horoscope_read failed request_id=%s', request_id)
        yield {'event': 'error', 'code': 'processing_error', 'message': 'Không xử lý được lá số hoặc nguồn sách. Xem log backend với mã yêu cầu.', 'request_id': request_id}


def read_horoscope(req: HoroscopeRequest) -> dict:
    for event in reading_events(req):
        if event['event'] == 'result':
            return event['report']
        if event['event'] == 'error':
            return {'status': 'error', 'error_code': event['code'], 'detail': event['message'],
                    'ho_ten': req.ho_ten or '', 'thong_tin_co_ban': {}, 'reading': {},
                    'meta': {'request_id': event['request_id']}}
    raise RuntimeError('Reading stream ended without a terminal event.')
