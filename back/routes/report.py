# routes/report.py

from flask import Blueprint, request, jsonify
from flask_cors import CORS
import pandas as pd
import json
import os
import re
from sqlalchemy import create_engine
import pymysql
import sys

# 🔧 ai 코드 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ai')))
from ai.report_ai import run_report

bp = Blueprint('report', __name__)
CORS(bp)

# ✅ RDS 접속 정보
DB_USER = 'oesnue'
DB_PASSWORD = 'gPwls0105!'
DB_HOST = 'daktor-commercial-prod.czig88k8s0e8.ap-northeast-2.rds.amazonaws.com'
DB_PORT = 3306
DB_NAME = 'daktor_db'

engine = create_engine(
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
    connect_args={'charset': 'utf8mb4'}
)

# 🔧 CSV 경로
REGION_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/region_info.csv'))
SERVICE_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data/service_type.csv'))

@bp.route('/report', methods=['POST'])
def report():
    try:
        data = request.get_json()
        print("[Report] 받은 데이터:", data)

        gu_name = data.get('gu_name')
        region = data.get('region')
        category_large = data.get('category_large')
        category_small = data.get('category_small')
        purpose = data.get('purpose')
        years = data.get('years', ['2024'])  # 리스트 형태로 받거나 기본값

        # 지역코드 매핑
        region_df = pd.read_csv(REGION_CSV_PATH)
        matched_region = region_df[region_df['region_name'].str.contains(region)]
        if matched_region.empty:
            return jsonify({"error": f"지역 '{region}'에 해당하는 지역코드가 없습니다."}), 400
        region_code = matched_region.iloc[0]['region_code']

        # 업종코드 매핑
        service_df = pd.read_csv(SERVICE_CSV_PATH)
        matched_service = service_df[service_df['service_name'].str.contains(category_small)]
        if matched_service.empty:
            return jsonify({"error": f"업종 '{category_small}'에 해당하는 서비스코드가 없습니다."}), 400
        service_code = matched_service.iloc[0]['service_code']

        # ✅ RDS에서 zone_id 조회
        zone_query = f"""
        SELECT zone_id FROM zone_table WHERE region_name LIKE '%{region}%'
        """
        zone_ids_df = pd.read_sql_query(zone_query, engine)
        zone_ids = zone_ids_df['zone_id'].tolist()
        if not zone_ids:
            return jsonify({"error": f"{region}에 해당하는 zone_id가 없습니다."}), 404

        print(f"[Report] region_code: {region_code}, service_code: {service_code}, zone_ids: {zone_ids}")

        # ✅ AI 보고서 생성
        run_report(
            gu_name,
            region,
            category_large,
            category_small,
            purpose,
            region_code,
            service_code,
            years
        )

        # report.txt 파싱
        with open("report.txt", "r", encoding="utf-8") as f:
            report_text = f.read()

        sections = re.split(r"(?=\n?\d+\.\s|👉)", report_text.strip())
        parsed_sections = []
        for section in sections:
            lines = section.strip().split("\n", 1)
            if len(lines) == 2:
                title = lines[0].strip()
                content = lines[1].strip()
            else:
                title = lines[0].strip()
                content = ""
            parsed_sections.append({"title": title, "content": content})

        # chart_data.json 로딩
        if os.path.exists("chart_data.json"):
            with open("chart_data.json", "r", encoding="utf-8") as f:
                chart_data = json.load(f)
        else:
            chart_data = {}

        # ✅ JSON 응답
        return jsonify({
            "summary": report_text[:300],  # 요약
            "sections": parsed_sections,
            "chart_data": chart_data,
            "zone_ids": zone_ids
        })

    except Exception as e:
        print("[Error] 리포트 생성 중 오류:", str(e))
        return jsonify({"error": "리포트 생성 실패"}), 500
