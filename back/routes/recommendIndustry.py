import sys
import os
import json
import re
import difflib
from flask import Blueprint, request, jsonify

# ai 디렉토리 경로 등록
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from ai import recommend_industry  # run_industry_recommendation(region, gu_name)

bp = Blueprint('recommend_industry', __name__)

# --- 유틸: 지역명 정규화 ---
_RE_MULTI_DOT = re.compile(r'[·∙•ㆍ]')
_RE_TILDE = re.compile(r'[~∼〜\-–—]')
_RE_WS = re.compile(r'\s+')

def normalize_region(s: str) -> str:
    if not isinstance(s, str):
        return ''
    s = s.strip()
    s = s.replace('\r','').replace('\n','')
    s = _RE_MULTI_DOT.sub('', s)
    s = _RE_TILDE.sub('', s)
    s = _RE_WS.sub('', s)
    return s

def find_region_key(result_dict: dict, region: str):
    if not isinstance(result_dict, dict):
        return None
    # 1) 원본문자열 완전일치
    if region in result_dict:
        return region
    # 2) 정규화 일치
    target = normalize_region(region)
    norm_map = {normalize_region(k): k for k in result_dict.keys()}
    if target in norm_map:
        return norm_map[target]
    # 3) 부분/포함 일치
    for nk, orig in norm_map.items():
        if target and (target in nk or nk in target):
            return orig
    # 4) 유사도 매칭
    close = difflib.get_close_matches(target, list(norm_map.keys()), n=1, cutoff=0.6)
    if close:
        return norm_map[close[0]]
    return None

def _load_recommendation_json():
    # ✅ runtime 경로(감시 제외 디렉터리)를 우선 탐색
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'runtime', 'recommendation_industry.json')),
        # 프로젝트 루트 기준 여러 위치 탐색 (하위 호환)
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recommendation_industry.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'recommendation_industry.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ai', 'recommendation_industry.json')),
        # 과거 파일명 호환
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recommendation_dong.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'recommendation_dong.json')),
        os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ai', 'recommendation_dong.json')),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                return json.load(f), p
    # 없으면 빈 결과 반환
    return {}, None

@bp.route('/recommend/industry', methods=['POST'])
def recommend_industry_route():
    data = request.get_json(silent=True) or {}
    gu_name = data.get('gu_name')
    region  = data.get('region')

    if not gu_name or not region:
        return jsonify({'error': 'Missing gu_name or region'}), 400

    try:
        # 1) 추천 실행 (파일 생성/갱신도 수행)
        payload = recommend_industry.run_industry_recommendation(region, gu_name)

        # ✅ 실행 결과(payload)가 있으면 바로 사용 (파일 I/O race 회피)
        if isinstance(payload, dict) and region in payload:
            items = payload.get(region, [])
            for item in items:
                if 'category_small' in item and isinstance(item['category_small'], str):
                    item['category_small'] = item['category_small'].strip().replace('\r','')
            return jsonify({
                'recommendations': items,
                'matched_region': region,
                'meta': {'gu_name': gu_name, 'requested_region': region, 'json_path': None}
            }), 200

        # 2) JSON 로드(파일 기준) + 지역 매칭 (fallback)
        result, json_path = _load_recommendation_json()
        key = find_region_key(result, region)
        print(f"[recommend_industry] requested='{region}', matched='{key}', json='{json_path}'")

        items = result.get(key, []) if key else []
        # 문자열 꼬임 제거
        for item in items:
            if 'category_small' in item and isinstance(item['category_small'], str):
                item['category_small'] = item['category_small'].strip().replace('\r','')

        response = {
            'recommendations': items,
            'matched_region': key,
            'meta': {
                'gu_name': gu_name,
                'requested_region': region,
                'json_path': json_path
            }
        }
        # ✅ 항상 200으로 응답 (빈 배열 가능)
        return jsonify(response), 200

    except Exception as e:
        # LLM 429 등 포함 → 끊지 말고 200 + 빈 배열 반환
        msg = str(e)
        print(f"[❌ Flask 라우트 에러] {msg}")
        return jsonify({
            'recommendations': [],
            'matched_region': None,
            'meta': {
                'gu_name': gu_name,
                'requested_region': region,
                'note': 'Error occurred but returning empty list.',
                'error': msg
            }
        }), 200
