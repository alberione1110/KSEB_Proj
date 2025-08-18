import sys
import os
import json
import re
import difflib
from flask import Blueprint, request, jsonify

# ai 디렉토리 등록
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ai import recommend_area  # 기대: run_recommendation(category_small, gu_name) -> dict(payload)

bp = Blueprint('recommend_area', __name__)

# --- 유틸: 카테고리명 정규화 (업종 소분류) ---
_RE_MULTI_DOT = re.compile(r'[·∙•ㆍ]')
_RE_TILDE = re.compile(r'[~∼〜\-–—]')
_RE_WS = re.compile(r'\s+')

def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ''
    s = s.strip()
    s = s.replace('\r', '').replace('\n', '')
    s = _RE_MULTI_DOT.sub('', s)
    s = _RE_TILDE.sub('', s)
    s = _RE_WS.sub('', s)
    return s

def find_key_by_similarity(result_dict: dict, key_text: str):
    """result_dict의 키들 중 key_text와 가장 잘 맞는 키를 찾는다."""
    if not isinstance(result_dict, dict):
        return None
    # 완전 일치
    if key_text in result_dict:
        return key_text
    # 정규화 일치
    target = normalize_text(key_text)
    norm_map = {normalize_text(k): k for k in result_dict.keys()}
    if target in norm_map:
        return norm_map[target]
    # 부분/포함 일치
    for nk, orig in norm_map.items():
        if target and (target in nk or nk in target):
            return orig
    # 유사도 매칭
    close = difflib.get_close_matches(target, list(norm_map.keys()), n=1, cutoff=0.6)
    if close:
        return norm_map[close[0]]
    return None

def _load_recommendation_json():
    """
    실행 환경에 따라 생성 위치가 달라질 수 있으므로 여러 후보 경로를 탐색한다.
    """
    candidates = [
        # 런타임/캐시 우선
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'runtime', 'recommendation_dong.json')),
        # 하위 호환: routes/.., 프로젝트 루트, ai 폴더 등
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recommendation_dong.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'recommendation_dong.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ai', 'recommendation_dong.json')),
        # 혹시 파일명이 다른 경우를 대비
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recommendation_area.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'recommendation_area.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ai', 'recommendation_area.json')),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f), p
    return {}, None

@bp.route('/recommend/area', methods=['POST'])
def recommend_area_route():
    data = request.get_json(silent=True) or {}
    category_small = data.get('category_small')  # 예: "커피-음료"
    gu_name = data.get('gu_name')                # 예: "종로구"

    if not category_small or not gu_name:
        return jsonify({'error': 'Missing category_small or gu_name'}), 400

    try:
        # 1) 추천 실행 (파일 생성/갱신 포함)
        payload = recommend_area.run_recommendation(category_small, gu_name)

        # ✅ 실행 결과(payload)가 dict이고, 우리가 찾는 키가 있으면 바로 사용 (파일 I/O race 회피)
        if isinstance(payload, dict):
            key = category_small if category_small in payload else find_key_by_similarity(payload, category_small)
            if key:
                items = payload.get(key, [])
                # 필드 정리
                norm = []
                for it in (items if isinstance(items, list) else []):
                    norm.append({
                        'district': (it.get('district') or it.get('행정동명') or '').strip(),
                        'reason': (it.get('reason') or it.get('사유') or '').strip(),
                        'score': it.get('score') if isinstance(it.get('score'), (int, float)) else None,
                    })
                return jsonify({
                    'recommendations': norm,
                    'matched_category': key,
                    'meta': {'gu_name': gu_name, 'requested_category': category_small, 'json_path': None}
                }), 200

        # 2) 파일 로드(fallback) + 키 매칭
        result, json_path = _load_recommendation_json()
        key = find_key_by_similarity(result, category_small)
        items = result.get(key, []) if key else []
        norm = []
        for it in (items if isinstance(items, list) else []):
            norm.append({
                'district': (it.get('district') or it.get('행정동명') or '').strip(),
                'reason': (it.get('reason') or it.get('사유') or '').strip(),
                'score': it.get('score') if isinstance(it.get('score'), (int, float)) else None,
            })

        return jsonify({
            'recommendations': norm,
            'matched_category': key,
            'meta': {'gu_name': gu_name, 'requested_category': category_small, 'json_path': json_path}
        }), 200

    except Exception as e:
        # 429/파일없음 등 포함 — 프런트가 끊기지 않도록 200 + 빈 배열
        msg = str(e)
        print(f"[❌ Flask 라우트 에러] {msg}")
        return jsonify({
            'recommendations': [],
            'matched_category': None,
            'meta': {
                'gu_name': gu_name,
                'requested_category': category_small,
                'note': 'Error occurred but returning empty list.',
                'error': msg
            }
        }), 200
