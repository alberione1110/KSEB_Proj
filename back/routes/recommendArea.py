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
    industry = data.get('industry')

    if not industry:
        return jsonify({'error': 'Missing industry'}), 400

    result = recommend_area.get_recommendation(industry)
    return jsonify({'recommendations': result})
