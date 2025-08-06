import sys
import os
import json
from flask import Blueprint, request, jsonify

# ai 디렉토리 등록
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ai import recommend_area  # run_recommendation(category_small, gu_name)

bp = Blueprint('recommend_area', __name__)

@bp.route('/recommend/area', methods=['POST'])
def recommend_area_route():
    data = request.get_json()
    category_small = data.get('category_small')  # 예: "커피-음료"
    gu_name = data.get('gu_name')                # 예: "중구"

    if not category_small or not gu_name:
        return jsonify({'error': 'Missing category_small or gu_name'}), 400

    try:
        # 1. 지역 추천 실행 (category_small 기준)
        recommend_area.run_recommendation(category_small, gu_name)

        # 2. 결과 파일 읽기
        json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'recommendation_dong.json'))
        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)

        if category_small not in result:
            return jsonify({'error': f'No recommendation found for {category_small}'}), 404

        return jsonify({'recommendations': result[category_small]})

    except Exception as e:
        print(f"[❌ Flask 에러] {e}")
        return jsonify({'error': f'Failed to process recommendation: {str(e)}'}), 500
