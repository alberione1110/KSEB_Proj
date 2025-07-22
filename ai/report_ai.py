def generate_report_ai(data):
    print("[AI] 입력 데이터 확인:", data)

    role = data.get("role", "알 수 없음")
    industry = data.get("industry", "업종 없음")
    district = data.get("selectedDistrict", "지역 없음")

    return {
        "input_check": {
            "역할": role,
            "업종": industry,
            "지역": district,
            "월 매출": data.get("rawMonthlySales", "정보 없음"),
            "창업 목적": data.get("purpose", "정보 없음"),
        },
        "summary": f"{district}는 {industry} 업종에 적합한 지역으로 분석됩니다.",
        "dummy_insight": [
            f"역할: {role}",
            f"업종: {industry}",
            f"지역: {district}",
            f"월 매출: {data.get('rawMonthlySales', '정보 없음')}",
            f"목적: {data.get('purpose', '정보 없음')}",
        ]
    }