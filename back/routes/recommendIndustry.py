import sys
import os
import json
from flask import Blueprint, request, jsonify

# ai 디렉토리 경로 등록
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ai import recommend_industry  # run_industry_recommendation(region, gu_name)

bp = Blueprint('recommend_industry', __name__)

@bp.route('/recommend/industry', methods=['POST'])
def recommend_industry_route():
    data = request.get_json()
    gu_name = data.get('gu_name')     # 예: "마포구"
    region = data.get('region')       # 예: "연남동"

    if not gu_name or not region:
        return jsonify({'error': 'Missing gu_name or region'}), 400

    try:
        # 1. 업종 추천 실행
        recommend_industry.run_industry_recommendation(region, gu_name)

        # 2. 결과 파일 경로
        json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recommendation_dong.json'))

        # 3. JSON 파일 열기
        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)

        # 4. 해당 지역(region)에 대한 추천 결과 추출
        if region not in result:
            return jsonify({'error': f'No recommendation found for {region}'}), 404

        return jsonify({'recommendations': result[region]})

    except Exception as e:
        print(f"[❌ Flask 에러] {e}")
        return jsonify({'error': f'Failed to process recommendation: {str(e)}'}), 500
