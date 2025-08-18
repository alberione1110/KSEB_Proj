import re
import pandas as pd
from flask import Blueprint, request, jsonify

from config.settings import get_engine  # ✅ 환경변수에서 안전하게 로드
from ai.report_ai import generate_report

bp = Blueprint("report", __name__)

def _pick_params():
    """1) JSON body 우선, 없으면 2) 쿼리스트링에서 가져오는 헬퍼"""
    data = request.get_json(silent=True) or {}
    region = (data.get("region") or request.args.get("region") or "").strip()
    gu_name = (data.get("gu_name") or request.args.get("gu_name") or "").strip()
    category_small = (data.get("category_small") or request.args.get("category_small") or "").strip()
    purpose = (data.get("purpose") or request.args.get("purpose") or "").strip()
    category_large = (data.get("category_large") or request.args.get("category_large") or "").strip()
    role = (data.get("role") or request.args.get("role") or "").strip()
    return {
        "region": region,
        "gu_name": gu_name,
        "category_small": category_small,
        "purpose": purpose,
        "category_large": category_large,
        "role": role,
    }

# ✅ '구 동'으로 들어와도 '동'만 뽑아 쓰도록 정규화
def _dong_only(name: str, gu: str) -> str:
    if not name:
        return ''
    n = re.sub(r'^\s*(서울특별시|서울시)\s*', '', name)
    if gu:
        n = re.sub(rf'^\s*{re.escape(gu)}\s*', '', n)
    return n.strip()

# --- 섹션 파서 유틸 ---
SECTION_TITLE_MAP = {
    1: "1. 기본 지역 정보",
    2: "2. 상권 변화",
    3: "3. 신생 기업 생존율 및 평균 영업 기간",
    4: "4. 개폐업 추이 및 진입 위험도",
    5: "5. 인구 및 유동 인구 특성",
    6: "6. 임대료 수준",
    7: "7. 매출 특성 요약",
}

def _parse_sections(text: str):
    """LLM이 만든 보고서 문자열을 프론트가 기대하는 sections 배열로 변환"""
    if not isinstance(text, str) or not text.strip():
        return []

    # 1) 마크다운/불릿 정리
    t = re.sub(r'^\s*[-*•]\s*', '', text, flags=re.MULTILINE)
    # '1.\n제목' → '1. 제목'
    t = re.sub(r'(?m)^\s*(\d+)\.\s*\n\s*', r'\1. ', t)

    # 2) '👉 종합 평가' 또는 '숫자. ' 단위로 분리
    parts = re.split(r'(?m)(?=^👉\s*종합\s*평가|^\d+\.\s)', t.strip())

    sections = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines = p.splitlines()
        title = lines[0].strip()

        # '1.' 처럼 숫자만 있는 제목 보정
        m = re.match(r'^(\d+)\.\s*$', title)
        if m:
            idx = int(m.group(1))
            title = SECTION_TITLE_MAP.get(idx, title)

        body = "\n".join(lines[1:]).strip()
        sections.append({"title": title, "content": body})

    # 3) '👉 종합 평가'가 있으면 맨 앞으로 이동
    eval_idx = next((i for i, s in enumerate(sections) if "종합 평가" in s["title"]), None)
    if eval_idx not in (None, 0):
        sections = [sections[eval_idx]] + sections[:eval_idx] + sections[eval_idx+1:]

    # 4) 종합 평가가 전혀 없으면 첫 문단으로 요약 생성해 앞에 추가
    if eval_idx is None:
        first_para = parts[0].split("\n\n")[0].strip() if parts else ""
        sections = [{"title": "👉 종합 평가", "content": first_para}] + sections

    return sections

@bp.route("/report", methods=["GET", "POST"])
def report():
    try:
        params = _pick_params()
        print("📥 /api/report params =", params)

        missing = [k for k in ["region", "gu_name", "category_small", "purpose"] if not params[k]]
        if missing:
            return jsonify({
                "ok": False,
                "error": "missing_required_params",
                "missing": missing,
                "hint": "예: ?region=연남동&gu_name=마포구&category_small=한식음식점&purpose=창업 준비",
            }), 400

        # 입력 region 정규화: '마포구 연남동' -> '연남동'
        region_only = _dong_only(params["region"], params["gu_name"])

        engine = get_engine()  # ✅ 안전한 엔진 로드

        # 1) category_large
        large_df = pd.read_sql_query(
            "SELECT category_large FROM subcategory_avg_operating_period_stats WHERE category_small = %s LIMIT 1",
            engine, params=(params["category_small"],)
        )
        if large_df.empty:
            return jsonify({"ok": False, "error": "not_found", "detail": "category_large를 찾을 수 없음"}), 404
        category_large = large_df["category_large"].iloc[0]

        # 2) service_code
        code_df = pd.read_sql_query(
            "SELECT service_code FROM service_type WHERE service_name LIKE %s LIMIT 1",
            engine, params=(f"%{params['category_small']}%",)
        )
        if code_df.empty:
            return jsonify({"ok": False, "error": "not_found", "detail": "service_code를 찾을 수 없음"}), 404
        service_code = code_df["service_code"].iloc[0]

        # 3) region_code  ← 여기서부터 region_only 사용
        region_df = pd.read_sql_query(
            "SELECT region_code FROM avg_operating_period_stats WHERE region_name = %s LIMIT 1",
            engine, params=(region_only,)
        )
        if region_df.empty:
            return jsonify({"ok": False, "error": "not_found", "detail": "region_code를 찾을 수 없음"}), 404
        region_code = region_df["region_code"].iloc[0]

        # 4) zone_ids
        zone_ids_df = pd.read_sql_query(
            "SELECT zone_id FROM zone_table WHERE region_name = %s",
            engine, params=(region_only,)
        )
        zone_ids = zone_ids_df["zone_id"].astype(str).tolist()
        if not zone_ids:
            return jsonify({"ok": False, "error": "not_found", "detail": "zone_id가 없음"}), 404

        # 리포트 생성 (텍스트/차트/존 설명)
        report_text, chart_data, zone_ids_str, zone_texts = generate_report(
            gu_name=params["gu_name"],
            region=region_only,
            category_large=category_large,
            category_small=params["category_small"],
            purpose=params["purpose"],
            region_code=region_code,
            service_code=service_code,
            zone_ids=zone_ids,
        )

        sections = _parse_sections(report_text)

        return jsonify({
            "ok": True,
            "summary": f"{params['gu_name']} {region_only} · {params['category_small']} · {params['purpose']}",
            "sections": sections,
            "chart_data": chart_data,
            "zone_ids": [str(z) for z in zone_ids],
            "zone_texts": zone_texts,
            "report_text": report_text,
        })
    except Exception as e:
        print("❌ /api/report error:", e)
        return jsonify({"ok": False, "error": "internal_error", "detail": str(e)}), 500
