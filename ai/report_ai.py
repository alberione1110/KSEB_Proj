def generate_report_ai(data):
    print("[AI] 입력 데이터 확인:", data)

    role = data.get("role", "알 수 없음")
    category_large = data.get("category_large", "대분류 없음")
    category_small = data.get("category_small", "소분류 없음")
    gu_name = data.get("gu_name", "구 정보 없음")
    region = data.get("region", "동 정보 없음")
    industry = category_small  # 기존 industry 대체

    full_location = f"{gu_name} {region}".strip()

    return {
        "input_check": {
            "역할": role,
            "업종 대분류": category_large,
            "업종 소분류": category_small,
            "지역": full_location,
            "월 매출": data.get("rawMonthlySales", "정보 없음"),
            "창업 목적": data.get("purpose", "정보 없음"),
        },
        "summary": f"{full_location}는 {category_small} 업종에 적합한 지역으로 분석됩니다.",
        "dummy_insight": [
            f"역할: {role}",
            f"업종 대분류: {category_large}",
            f"업종 소분류: {category_small}",
            f"지역: {full_location}",
            f"월 매출: {data.get('rawMonthlySales', '정보 없음')}",
            f"목적: {data.get('purpose', '정보 없음')}",
        ]
    }
