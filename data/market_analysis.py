import requests
import openpyxl
from datetime import datetime

# ⛳️ 파라미터 설정
payload = {
    "stdrYyCd": "2024",         # 기준 연도
    "stdrSlctQu": "sameQu",     # 기준 분기 설정
    "stdrQuCd": "1",            # 분기 코드 (1~4)
    "stdrMnCd": "202412",       # 기준 월
    "selectTerm": "quarter",
    "svcIndutyCdL": "CS000000", # 업종 대분류
    "svcIndutyCdM": "all",      # 업종 중분류
    "stdrSigngu": "11",         # 자치구 코드 (서울)
    "selectInduty": "1",
    "infoCategory": "survival"
}

# 📡 API 요청
url = "https://golmok.seoul.go.kr/region/selectSurvivalRate.json"
headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
response = requests.post(url, data=payload, headers=headers)
response.raise_for_status()
json_data = response.json()

# ⏱ 분기 라벨 생성 함수
def get_same_quarter_years(base_year: int, quarter: int):
    return [(base_year - 2 + i, quarter) for i in range(3)]

base_year = int(payload["stdrYyCd"])
base_quarter = int(payload["stdrQuCd"])
same_quarters = get_same_quarter_years(base_year, base_quarter)

# 📘 엑셀 생성
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "상권분석 결과"

# 🧾 헤더 작성
headers = ["상권명(NM)", "코드(CD)"]
for y, q in same_quarters:
    label = f"{y}년 {q}분기"
    headers.extend([
        f"{label} 1년 생존율", f"{label} 3년 생존율", f"{label} 5년 생존율"
    ])
headers.append("구분(GUBUN)")
ws.append(headers)

# 📊 데이터 작성
for item in json_data:
    row = [
        item.get("NM", ""),
        item.get("CD", ""),
        item.get("FIRST_1Y", ""),
        item.get("FIRST_3Y", ""),
        item.get("FIRST_5Y", ""),
        item.get("SECOND_1Y", ""),
        item.get("SECOND_3Y", ""),
        item.get("SECOND_5Y", ""),
        item.get("THIRD_1Y", ""),
        item.get("THIRD_3Y", ""),
        item.get("THIRD_5Y", ""),
        item.get("GUBUN", "")
    ]
    ws.append(row)

# 💾 파일 이름 설정
file_name = f"상권분석_생존율_{base_quarter}분기.xlsx"
wb.save(file_name)
print(f"✅ 저장 완료: {file_name}")
