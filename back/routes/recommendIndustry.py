import sys
import os
from flask import Blueprint, request, jsonify

# ai 디렉토리 경로를 시스템 경로에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ai import recommend_industry  # AI 추천 로직 모듈

bp = Blueprint('recommend_industry', __name__)

@bp.route('/recommend/industry', methods=['POST'])
def recommend_industry_route():
    data = request.get_json()
    gu_name = data.get('gu_name')
    region = data.get('region')

    if not gu_name or not region:
        return jsonify({'error': 'Missing gu_name or region'}), 400

    # AI 추천 결과 가져오기
    result = recommend_industry.get_recommendation(gu_name, region)
    return jsonify({'recommendations': result})
