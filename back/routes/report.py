# routes/report.py

from flask import Blueprint, request, jsonify
from flask_cors import CORS

# 🔧 report_ai.py 경로를 직접 추가 (ai 폴더)
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ai')))
from ai.report_ai import generate_report_ai

bp = Blueprint('report', __name__)
CORS(bp)

@bp.route('/report', methods=['POST'])
def report():
    try:
        data = request.get_json()
        print("[Report] 받은 데이터:", data)

        # report_ai.py 호출
        result = generate_report_ai(data)
        return jsonify(result)

    except Exception as e:
        print("[Error] 리포트 생성 중 오류:", str(e))
        return jsonify({"error": "리포트 생성 실패"}), 500
