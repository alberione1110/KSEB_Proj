from flask import Blueprint, request, jsonify
import sys
import os

# ai 폴더 경로 등록
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from ai import recommend_area

bp = Blueprint('recommend_area', __name__)

@bp.route('/recommend/area', methods=['POST'])
def recommend_area_route():
    data = request.json
    category_small = data.get('category_small')
    gu_name = data.get('gu_name')

    if not category_small or not gu_name:
        return jsonify({'error': 'Missing category_small or gu_name'}), 400

    # 🔧 인자 순서 수정: category_small이 첫 번째
    result = recommend_area.get_recommendation(category_small, gu_name)
    return jsonify({'recommendations': result})
