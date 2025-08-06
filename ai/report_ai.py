from openai import OpenAI
import os
import re
import pandas as pd
from sqlalchemy import create_engine
import pymysql
import json

def run_report (gu_name, region, category_large, category_small, purpose, region_code, service_code, years):
    client = OpenAI(api_key="")  

    host = 'daktor-commercial-prod.czig88k8s0e8.ap-northeast-2.rds.amazonaws.com'
    port = 3306
    user = 'oesnue'
    password = 'gPwls0105!'
    database = 'daktor_db'

    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}",
        connect_args={'charset': 'utf8mb4'}
    )

    # 연결 시도
    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
            connect_timeout=5
        )
        print("✅ RDS 연결 성공")

        # 간단한 쿼리 테스트
        with conn.cursor() as cursor:
            cursor.execute("SHOW TABLES;")
            for row in cursor.fetchall():
                print(row)

        conn.close()

    except Exception as e:
        print("❌ 연결 실패:", e)

    print("1. DB 연결 및 쿼리 시작")

    # ✅ 개폐업수: 연도별 데이터 사용 (3년치 평균 아님, 그대로 둠)
    open_close_df = pd.read_sql_query(f"""
    SELECT year, num_open, num_close
    FROM openclose_stats
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND year IN ({','.join(map(str, years))})
    ORDER BY year
    """, engine)

    # ✅ 신생기업 생존율: 분기 데이터 평균 사용
    survival_df = pd.read_sql_query(f"""
    SELECT 
        ROUND(AVG(survival_rate_1yr), 1) AS avg_survival_rate_1yr,
        ROUND(AVG(survival_rate_3yr), 1) AS avg_survival_rate_3yr,
        ROUND(AVG(survival_rate_5yr), 1) AS avg_survival_rate_5yr
    FROM startup_survival_rate
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND year BETWEEN 2022 AND 2025
    AND quarter IN (1, 2, 3, 4)
    """, engine)

    # ✅ 임대시세: 분기 데이터 평균
    rent_df = pd.read_sql_query(f"""
    SELECT 
        ROUND(AVG(rent_first_floor)) AS avg_rent_first_floor,
        ROUND(AVG(rent_other_floors)) AS avg_rent_other_floors
    FROM rental_price_stats
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND year BETWEEN 2022 AND 2025
    AND quarter IN (1, 2, 3, 4)
    """, engine)

    # ✅ 점포 수: 연도별 변화 추이 비교 (2023, 2024, 2025)
    store_df = pd.read_sql_query(f"""
    SELECT year, store_total, store_franchise, store_nonfranchise
    FROM store_count_stats
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND year IN ({','.join(map(str, years))})
    ORDER BY year
    """, engine)

    # ✅ 평균 영업 기간: 연도·분기별 데이터 평균
    avg_years_df = pd.read_sql_query(f"""
    SELECT 
        ROUND(AVG(value), 1) AS avg_10yr
    FROM subcategory_avg_operating_period_stats
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND category_large = '{category_large}' AND category_small = '{category_small}'
    AND indicator = 'avg_operating_years_10'
    AND year BETWEEN 2022 AND 2025
    AND quarter IN (1, 2, 3, 4)
    """, engine)

    avg_years_df2 = pd.read_sql_query(f"""
    SELECT 
        ROUND(AVG(value), 1) AS avg_30yr
    FROM subcategory_avg_operating_period_stats
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND category_large = '{category_large}' AND category_small = '{category_small}'
    AND indicator = 'avg_operating_years_30'
    AND year BETWEEN 2022 AND 2025
    AND quarter IN (1, 2, 3, 4)
    """, engine)

    # ✅ 유동 인구: 분기 데이터 평균
    floating_df = pd.read_sql_query(f"""
    SELECT year, quarter, floating_population, residential_population, working_population
    FROM floating_population_stats
    WHERE region_name = '{region}' AND region_code = {region_code}
    AND year BETWEEN 2022 AND 2025
    AND quarter IN (1, 2, 3, 4)
    ORDER BY year, quarter
    """, engine)

    if not floating_df.empty:
        floating_pop = round(floating_df["floating_population"].mean())
        residential_pop = round(floating_df["residential_population"].mean())
        working_pop = round(floating_df["working_population"].mean())
    else:
        floating_pop = residential_pop = working_pop = 0  # 또는 None, 또는 "데이터 없음"


    # ✅ sales 관련 데이터 조회 (연도별 테이블 + 분기 필터로 반복 조회)
    sales_years = [2022, 2023, 2024]
    quarters = [1, 2, 3, 4]

    # ✅ zone_id, zone_name 가져오기
    zone_query = f"""
    SELECT zone_id, zone_name 
    FROM zone_table 
    WHERE region_name = '{region}'
    """
    zone_df = pd.read_sql_query(zone_query, engine)
    zone_ids = zone_df['zone_id'].tolist()
    zone_names = dict(zip(zone_df['zone_id'].astype(str), zone_df['zone_name']))

    zone_ids_str = ','.join(map(str, zone_ids))

    # ✅ zone_store_count 테이블에서 점포 수 불러오기
    store_count_df_list = []
    for year in sales_years:
        for quarter in quarters:
            store_counts = pd.read_sql_query(f"""
                SELECT zone_id, service_name, count, {year} AS year, {quarter} AS quarter
                FROM zone_store_count_{year}
                WHERE service_name = '{category_small}'
                AND quarter = {quarter}
                AND zone_id IN ({zone_ids_str})
            """, engine)
            store_counts["zone_id"] = store_counts["zone_id"].astype(str)
            store_count_df_list.append(store_counts)
            
    # 결과 저장 리스트
    summary_df_list = []
    gender_age_df_list = []
    sales_day_df_list = []
    sales_hour_df_list = []

    # ✅ zone_id 반복 (매출 관련 테이블)
    for zone_id in zone_ids:
        for year in sales_years:
            for quarter in quarters:
                # 매출 요약
                summary = pd.read_sql_query(f"""
                    SELECT monthly_sales, monthly_count, weekday_sales, weekend_sales, {year} AS year, {quarter} AS quarter
                    FROM sales_summary_{year}
                    WHERE quarter = {quarter}
                    AND zone_id = '{zone_id}'
                    AND service_code = '{service_code}'
                """, engine)
                summary["zone_id"] = str(zone_id)  # zone_id 문자열화
                summary_df_list.append(summary)

                # 성별·연령대 매출
                gender_age = pd.read_sql_query(f"""
                    SELECT gender, age_group, SUM(sales_amount) AS total_sales, {year} AS year, {quarter} AS quarter
                    FROM sales_by_gender_age_{year}
                    WHERE quarter = {quarter}
                    AND zone_id = '{zone_id}'
                    AND service_code = '{service_code}'
                    GROUP BY gender, age_group
                """, engine)
                gender_age["zone_id"] = str(zone_id)
                gender_age_df_list.append(gender_age)

                # 요일 매출
                day = pd.read_sql_query(f"""
                    SELECT day_of_week, SUM(sales_amount) AS total_sales, {year} AS year, {quarter} AS quarter
                    FROM sales_by_day_{year}
                    WHERE quarter = {quarter}
                    AND zone_id = '{zone_id}'
                    AND service_code = '{service_code}'
                    GROUP BY day_of_week
                """, engine)
                day["zone_id"] = str(zone_id)
                sales_day_df_list.append(day)

                # 시간대 매출
                hour = pd.read_sql_query(f"""
                    SELECT time_range, SUM(sales_amount) AS total_sales, {year} AS year, {quarter} AS quarter
                    FROM sales_by_hour_{year}
                    WHERE quarter = {quarter}
                    AND zone_id = '{zone_id}'
                    AND service_code = '{service_code}'
                    GROUP BY time_range
                """, engine)
                hour["zone_id"] = str(zone_id)
                sales_hour_df_list.append(hour)


    # concat으로 통합
    store_count_df = pd.concat(store_count_df_list, ignore_index=True)
    summary_df = pd.concat(summary_df_list, ignore_index=True)
    gender_age_df = pd.concat(gender_age_df_list, ignore_index=True)
    sales_day_df = pd.concat(sales_day_df_list, ignore_index=True)
    sales_hour_df = pd.concat(sales_hour_df_list, ignore_index=True)

    # ✅ 연도+분기+zone_id 기준으로 점포 수 join
    summary_merged = pd.merge(
        summary_df,
        store_count_df,
        on=["zone_id", "year", "quarter"],
        how="left"
    )

    # ✅ 점포 수 기준 평균 매출 계산
    summary_merged["avg_sales_per_store"] = summary_merged.apply(
        lambda row: row["monthly_sales"] / row["count"] if row["count"] and row["count"] > 0 else None,
        axis=1
    )

    # === 아래는 기존 요약 지표 계산 ===

    def get_value_safe(df, column):
        if not df.empty and column in df.columns:
            val = df[column].iloc[0]
            return val if pd.notnull(val) else 0
        return 0

    # 총 매출과 건수 → 객단가
    monthly_sales_total = summary_df["monthly_sales"].sum()
    monthly_count_total = summary_df["monthly_count"].sum()
    avg_sales_per_order = monthly_sales_total / monthly_count_total if monthly_count_total != 0 else 0

    weekday_sales = get_value_safe(summary_df, "weekday_sales")
    weekend_sales = get_value_safe(summary_df, "weekend_sales")

    # 성별·연령대 상위 그룹
    if not gender_age_df.empty:
        top_row = gender_age_df.sort_values("total_sales", ascending=False).iloc[0]
        gender_top = top_row["gender"]
        age_top = top_row["age_group"]
    else:
        gender_top = "정보 없음"
        age_top = "정보 없음"

    # 매출 피크 요일
    if not sales_day_df.empty and "total_sales" in sales_day_df.columns:
        top_day = sales_day_df.loc[sales_day_df["total_sales"].idxmax(), "day_of_week"]
    else:
        top_day = "정보 없음"

    # 매출 피크 시간대
    if not sales_hour_df.empty and "total_sales" in sales_hour_df.columns:
        top_hour = sales_hour_df.loc[sales_hour_df["total_sales"].idxmax(), "time_range"]
    else:
        top_hour = "정보 없음"


    # === 1. 연도별 점포 수 변화 ===
    store_yearly_data = {
        "labels": store_df["year"].tolist(),
        "values": store_df["store_total"].tolist()
    }

    # 연도별 개폐업 수
    open_close_data = {
        "labels": open_close_df["year"].tolist(),
        "open": open_close_df["num_open"].tolist(),
        "close": open_close_df["num_close"].tolist()
    }

    # === 3. 신생기업 생존율 ===
    survival_data = {
        "labels": ["1년", "3년", "5년"],
        "values": [
            survival_df["avg_survival_rate_1yr"][0],
            survival_df["avg_survival_rate_3yr"][0],
            survival_df["avg_survival_rate_5yr"][0]
        ]
    }
    # 평균 영업 기간 데이터
    operating_period_data = {
        "labels": ["10년 평균", "30년 평균"],
        "values": [
            avg_years_df["avg_10yr"][0] if not avg_years_df.empty else 0,
            avg_years_df2["avg_30yr"][0] if not avg_years_df2.empty else 0
        ]
    }

    # === 4. 임대료 비교 ===
    rent_data = {
        "labels": ["1층", "1층 외"],
        "values": [
            rent_df["avg_rent_first_floor"][0],
            rent_df["avg_rent_other_floors"][0]
        ]
    }

    # === 5. 유동인구 추이 ===
    floating_data = {
        "labels": (floating_df["year"].astype(str) + "Q" + floating_df["quarter"].astype(str)).tolist(),
        "values": floating_df["floating_population"].tolist()
    }

    # === 6. 매출 관련 데이터 (zone별) ===
    sales_data = {}
    for zone_id in summary_merged["zone_id"].unique():
        summary_zone = summary_merged[summary_merged["zone_id"] == zone_id]
        gender_age_zone = gender_age_df[gender_age_df["zone_id"] == zone_id]
        sales_day_zone = sales_day_df[sales_day_df["zone_id"] == zone_id]
        sales_hour_zone = sales_hour_df[sales_hour_df["zone_id"] == zone_id]

        # --- 점포 수 가져오기 ---
        store_count = summary_zone["count"].mean() if "count" in summary_zone.columns else 0

        # 1) 요일별 매출 (점포당 평균 매출 원 단위)
        sales_day_sorted = sales_day_zone.sort_values("day_of_week")
        if store_count and store_count > 0:
            day_values = (sales_day_sorted["total_sales"] / store_count).tolist()
        else:
            day_values = [0] * len(sales_day_sorted)
        sales_by_day = {
            "labels": sales_day_sorted["day_of_week"].tolist(),
            "values": day_values
        }

        # 2) 시간대별 매출 (점포당 평균 매출 원 단위)
        if store_count and store_count > 0:
            hour_values = (sales_hour_zone["total_sales"] / store_count).tolist()
        else:
            hour_values = [0] * len(sales_hour_zone)
        sales_by_hour = {
            "labels": sales_hour_zone["time_range"].tolist(),
            "values": hour_values
        }

        # 3) 성별 매출 (총합 그대로 사용)
        gender_df = gender_age_zone[gender_age_zone["gender"].isin(["남성", "여성"])] \
            .groupby("gender", as_index=False)["total_sales"].sum()
        sales_by_gender = {
            "labels": gender_df["gender"].tolist(),
            "values": gender_df["total_sales"].tolist()
        }

        # 4) 연령대별 매출 (총합 그대로 사용)
        age_df = gender_age_zone[~gender_age_zone["gender"].isin(["남성", "여성"])].copy()
        age_df["age_group"] = age_df["age_group"].astype(str)
        age_df["age_group"] = age_df["age_group"].apply(lambda x: "60대 이상" if "60" in x and "이상" in x else x + "대")
        age_df = age_df.groupby("age_group", as_index=False)["total_sales"].sum()
        sales_by_age_group = {
            "labels": age_df["age_group"].tolist(),
            "values": age_df["total_sales"].tolist()
        }

        # 5) 평일 vs 주말 매출 (점포당 평균)
        weekday_sales = summary_zone["weekday_sales"].sum() / store_count if store_count else 0
        weekend_sales = summary_zone["weekend_sales"].sum() / store_count if store_count else 0
        weekday_vs_weekend = {
            "labels": ["평일", "주말"],
            "values": [weekday_sales, weekend_sales]
        }

        # 6) 객단가 (총 매출 ÷ 건수)
        monthly_sales_total = summary_zone["monthly_sales"].sum()
        monthly_count_total = summary_zone["monthly_count"].sum()
        avg_price_per_order = monthly_sales_total / monthly_count_total if monthly_count_total else 0
        avg_price_data = {
            "labels": ["객단가"],
            "values": [avg_price_per_order]
        }

        sales_data[str(zone_id)] = {
            "sales_by_day": sales_by_day,
            "sales_by_hour": sales_by_hour,
            "sales_by_gender": sales_by_gender,
            "sales_by_age_group": sales_by_age_group,
            "weekday_vs_weekend": weekday_vs_weekend,
            "avg_price_per_order": avg_price_data
        }

    # === 7. zone_summary_text 생성
    zone_summary_text = ""
    for zid, zname in zone_names.items():
        zdata = sales_data[str(zid)]
        top_gender = max(zip(zdata["sales_by_gender"]["labels"], zdata["sales_by_gender"]["values"]), key=lambda x:x[1])[0]
        top_day = max(zip(zdata["sales_by_day"]["labels"], zdata["sales_by_day"]["values"]), key=lambda x:x[1])[0]
        avg_price = zdata["avg_price_per_order"]["values"][0]
        zone_summary_text += f"\n[{zname}] - 주요 소비층: {top_gender}, 피크 요일: {top_day}, 객단가: {avg_price:,.0f}원"

    # === 8. 최종 JSON 구조 ===
    chart_data = {
        "store_yearly": store_yearly_data,
        "open_close": open_close_data,
        "survival": survival_data,
        "operating_period": operating_period_data,
        "rent": rent_data,
        "floating": floating_data,
        "sales": sales_data,
        "zone_names": zone_names
    }

    # ✅ 매출 피크 시간대
    if not sales_hour_df.empty and "total_sales" in sales_hour_df.columns:
        top_hour = sales_hour_df.loc[sales_hour_df["total_sales"].idxmax(), "time_range"]
    else:
        top_hour = "정보 없음"
        
    # JSON 저장 (app.py에서 로드하거나 바로 render_template로 넘길 수 있음)
    with open("chart_data.json", "w", encoding="utf-8") as f:
        json.dump(chart_data, f, ensure_ascii=False)

    print("chart_data.json 저장 완료")


    print("3. GPT 프롬프트 생성 및 요청 시작")

    region_gpt_prompt = f"""
    서울특별시 {gu_name} {region} 지역의 상권 특성을 분석하려고 해.

    다음 정보를 참고해서 ① 간략 요약 ② 전문가형 해석 두 문단으로 나눠서 작성해줘:

    - 유동인구: {floating_pop:,}명/ha
    - 주거 인구: {residential_pop:,}명/ha
    - 직장 인구: {working_pop:,}명/ha

    요청 사항:
    1. 첫 문단은 **지역의 특성을 2문장으로 요약**해줘. (예: 고급 주거지와 관광지가 공존하는 지역)
    2. 두 번째 문단은 위 수치를 바탕으로, **상권의 성격과 소비층 유형(예: 관광객 위주, 직장인 중심 등)**을 **풍부하게 2~3문장 정도**로 설명해줘.
    3. 문단 사이에는 빈 줄 한 줄을 넣고, 문장에는 번호를 붙이지 마.

    반드시 전문가 보고서처럼 문체는 자연스럽고 간결하게 해줘.
    """

    region_desc_combined = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": region_gpt_prompt}]
    ).choices[0].message.content.strip()

    region_desc_lines = region_desc_combined.split("\n")
    region_desc = region_desc_lines[0] if len(region_desc_lines) > 0 else ""
    region_pop_desc = region_desc_lines[1] if len(region_desc_lines) > 1 else ""

    print("5. 최종 리포트 입력 생성 시작")

    # ✅ GPT에 입력할 구조화 데이터 만들기
    actual_input = f"""
    서울특별시 {gu_name} {region}에서의 {category_small} {purpose}을(를) 위한 리포트입니다.

    📌 업종: {category_small}
    📍 지역: 서울특별시 {gu_name} {region}
    🎯 목적: {purpose}

    [기초 데이터 요약]

    1. 기본 지역 정보
    - 행정구역: 서울특별시 {gu_name} {region}
    - 유동인구: {floating_pop:,}명/ha
    - 주거 인구: {residential_pop:,}명/ha
    - 직장 인구: {working_pop:,}명/ha
    - 지역 요약: {region_desc}
    - 상권 유형 해석: {region_pop_desc}

    2. 상권 변화
    - 점포 수 변화: {years[0]}년 {store_df['store_total'][0]}개 → {years[1]}년 {store_df['store_total'][1]}개 → {years[2]}년 {store_df['store_total'][2]}개
    - 프랜차이즈 점포 수: {store_df['store_franchise'][0]} → {store_df['store_franchise'][1]} → {store_df['store_franchise'][2]}
    - 일반 점포 수: {store_df['store_nonfranchise'][0]} → {store_df['store_nonfranchise'][1]} → {store_df['store_nonfranchise'][2]}

    3. 생존율 및 평균 영업 기간
    - 1년 생존율: {survival_df['avg_survival_rate_1yr'][0]}%
    - 3년 생존율: {survival_df['avg_survival_rate_3yr'][0]}%
    - 5년 생존율: {survival_df['avg_survival_rate_5yr'][0]}%
    - 10년 평균 영업 기간: {avg_years_df['avg_10yr'][0]}년
    - 30년 평균 영업 기간: {avg_years_df2['avg_30yr'][0]}년

    4. 개폐업 추이 및 진입 위험도
    - {years[0]}: 개업 {open_close_df['num_open'][0]}, 폐업 {open_close_df['num_close'][0]}
    - {years[1]}: 개업 {open_close_df['num_open'][1]}, 폐업 {open_close_df['num_close'][1]}
    - {years[2]}: 개업 {open_close_df['num_open'][2]}, 폐업 {open_close_df['num_close'][2]}

    5. 인구 및 유동 인구 특성
    - 유동인구 기반 설명: {region_pop_desc}

    6. 임대료 수준
    - 1층: {rent_df['avg_rent_first_floor'][0]:,}원 / 3.3㎡
    - 1층 외: {rent_df['avg_rent_other_floors'][0]:,}원 / 3.3㎡

    7. 매출 특성 요약
    - 월 매출액: {monthly_sales_total:,}원
    - 건당 평균 매출(객단가): {avg_sales_per_order:,.0f}원
    - 평일 매출: {weekday_sales:,}원 / 주말 매출: {weekend_sales:,}원
    - 주요 고객층: {gender_top} / {age_top}대
    - 매출 피크 요일: {top_day}
    - 매출 피크 시간대: {top_hour}
    - Zone별 세부 데이터 요약 : {zone_summary_text}

    위 정보를 활용해 다음 구조로 작성해줘:
    1) {region} 전체 상권 평가 및 공통 전략
    2) Zone별 특화 전략: 각 zone 이름을 소제목으로 두고, 해당 zone의 소비 패턴 차이에 맞춘 전략 제안
    위 데이터를 바탕으로, 아래 지침에 따라 전문가 리포트를 작성해줘.

    예시처럼 ① 제목 형식, ② 문단 구성, ③ 전략 제안 방식, ④ 자연어 문체를 모두 그대로 따르도록 해줘.
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": f"""
    너는 지역 상권 분석을 전문으로 하는 컨설턴트야. 아래 세 가지 목적별 예시처럼 리포트를 작성해줘. 사용자가 제공한 데이터는 실제 수치이므로, 이에 맞춰 수치 기반 해석과 전략 제안을 포함한 전문가 리포트를 작성하되, 형식과 문체는 예시와 동일하게 구성할 것.
    각 항목은 다음 형식을 반드시 따라야 해:

    [예시 1 – 창업 준비]
    👉종합 평가 

    청운효자동 상권은 역사적 배경과 관광객 유입이 강한 지역적 특성을 바탕으로, 단기적인 수요 기반은 안정적인 편입니다.
    신생기업의 1년 생존율이 85.3%로 높지만, 5년 생존율은 50.7%로 급감하는 점에서 장기 생존에는 리스크가 존재하며, 2025년 기준 폐업 수가 개업 수를 초과한 점은 진입 시기에 대한 신중한 판단이 필요함을 시사합니다. 
    또한 1층 임대료는 3.3㎡당 약 199,000원으로, 서울 커피·음료 업종 평균(약 150,000원) 대비 33% 높아 창업 초기 부담이 큰 편입니다. 따라서 입지 선택과 마케팅 전략을 정교하게 설계해야 합니다. 
    결론적으로, 진입 자체는 가능성이 있으나 생존과 안정성 확보를 위한 차별화 전략이 필수적이며, 예를 들어 다음과 같은 전략이 고려될 수 있습니다:
    • 지역 수요층에 맞춘 테마형 콘셉트 도입: 고령층과 관광객이 혼재된 특성을 반영해, 전통 요소를 결합한 카페나 문화 콘텐츠 공간을 기획 
    • 비대면 주문, 예약 중심 운영 도입: 인건비 부담을 줄이고, 고정 단골 확보를 위한 멤버십 기반 운영 
    • 단골 유입 전략: 지역 주민 대상 혜택 제공(예: 거주자 할인, 로컬 커뮤니티 행사 연계 등)을 통해 장기 고객층 확보 
    • 관광객 대상 홍보 채널 확보: 여행 앱, 지도 플랫폼, 인플루언서 연계 콘텐츠 마케팅 등으로 비거주 소비자 유입 확보 

    이러한 방식은 상권의 고정성과 비탄력적 임대료 구조에 대응하면서도 시장 내 경쟁력을 확보할 수 있는 실질적 전략으로 작용할 수 있습니다. 


    1. 기본 지역 정보 

    청운효자동은 서울 종로구 내에서도 역사·문화 중심지로 분류되며, 북촌한옥마을·경복궁·청와대 등 국가적 관광 명소와 인접해 국내외 관광객 유입이 꾸준한 편입니다. 최근 3년간 유동인구를 살펴보면 평균 14,000명/ha 수준으로 안정적이지만, 봄·가을 성수기에는 16,000명/ha 이상으로 15~20% 증가하는 패턴을 보입니다. 이는 시즌성 마케팅 전략의 여지가 크다는 의미입니다.
    인근 상권과 비교하면 삼청동은 관광객 밀도는 더 높지만 주거 인구 비중이 낮아 관광형 소비가 강하고, 청운효자동은 관광과 주거 수요가 혼재되어 있어 ‘혼합형 소비’ 특성을 보입니다. 특히 고령층 비중이 높아 전통 취향 기반 서비스에 강점이 있으며, 젊은층 유입을 위해서는 SNS용 포토스팟·현대적 디자인 접목이 필요합니다.
    장기적으로 인근 북악스카이웨이 관광 루트 개발, 청와대 개방 효과가 맞물리며 외부 유입 수요는 유지될 전망입니다. 이때 관광객 체류 시간은 평균 40분으로 인근 삼청동 대비 10분 길어, 체류형 소비(브런치, 전통 체험 카페)에 최적화된 환경입니다.


    2. 상권 변화 

    2022~2024년 점포 수는 889개 → 941개 → 946개로 증가하다 2025년 937개로 소폭 감소했습니다. 감소 원인은 임대료 상승(연평균 34%)과 관광객 회복 속도 둔화가 복합적으로 작용한 결과로 추정됩니다. 프랜차이즈 점포는 같은 기간 20% 이상 증가해 상권 내 브랜드 경쟁이 심화되고 있으며, 개인 창업자의 차별화 부담이 커지고 있습니다.

    세부 업종을 보면 커피·음료 내 디저트·브런치 결합 매장이 최근 2년간 12% 증가했습니다. 이 흐름은 체류 시간을 늘리는 방향으로 매출 구조를 개선하는 전략의 필요성을 시사합니다.
    추세적으로는 2026~2027년까지 점포 수가 현 수준에서 유지되거나 소폭 감소할 가능성이 있어, 신규 진입보다는 기존 매장 리뉴얼·콘셉트 재정비 전략이 유리할 수 있습니다.

    3. 신생기업 생존율 및 영업 기간

    신생기업의 생존율은 높은 편에 속하며, 1년 생존율이 85.3%, 3년 생존율이 69.5%, 5년 생존율이 50.7%로 나타났습니다. 이는 상권 내 경쟁이 치열하다는 점을 감안해야 합니다.
    특히 1년 차 생존율이 85.3%로 매우 높은 반면, 5년 차에는 절반 가까이(50.7%)로 떨어지는 점은 장기적으로 살아남기 위해 지속적인 차별화 전략과 안정적인 운영 계획이 필요하다는 점을 시사합니다. 단기적 생존은 비교적 수월하나, 중장기적 지속 가능성은 사업 역량에 따라 확연히 갈릴 수 있습니다.

    또한 업종 평균 영업 기간을 살펴보면, 최근 10년 기준 평균 영업 기간은 약 4.8년, 30년 기준은 약 7.2년 수준으로 나타납니다. 이는 장기적으로 생존하는 점포가 일정 비율 존재함을 의미하며, 창업 시 단기 성과뿐 아니라 5년 이후 운영 전략까지 고려해야 하는 중요 지표가 됩니다.


    4. 개폐업 추이 및 진입 위험도 

    2024년 기준으로 개업과 폐업 수가 비슷한 수준을 보이고 있으며, 점포의 안정성을 유지하는 것이 중요할 것으로 판단됩니다.
    2022년에는 개업 32건, 폐업 17건으로 개업이 활발했으나, 2024년에는 개업 25건, 폐업 26건으로 거의 동일한 수준까지 접근했습니다. 2025년에는 오히려 폐업(22건)이 개업(16건)을 초과하면서 진입 위험이 점차 커지고 있습니다. 이는 업종 선택과 초기 자금 계획, 마케팅 전략을 더욱 신중하게 수립해야 한다는 경고로 받아들일 수 있습니다.


    5. 인구 및 유동 인구 특성 

    유동인구 중심 상권으로서 발전 가능성이 높은 지역이며, 특히 주거 인구와 직장 인구의 균형 있는 구성으로 다양한 시간대에 안정적인 고객층을 확보할 수 있을 것으로 예상됩니다.
    분기별 유동인구는 다소 변동이 있으나, 전반적으로 14,000명/ha 내외 수준을 유지하고 있으며, 이는 비교적 안정적인 고객 유입이 가능하다는 점을 시사합니다. 다만 최근 분기에는 감소세가 관찰되어, 이벤트나 마케팅 전략으로 유입을 유지하려는 노력이 필요합니다.
    

    6. 임대료 수준 

    1층의 임대료는 3.3㎡당 199,365.0원으로, 1층 외의 임대료는 3.3㎡당 88,488.0원으로 책정되어 있습니다.
    1층 임대료는 3.3㎡당 199,000원으로, 동일 업종 서울 평균(170,000원) 대비 17% 높음
    특히 1층과 1층 외의 임대료 차이는 약 2.3배로, 가시성과 접근성을 중시하는 업종은 높은 비용을 감수해야 합니다. 따라서 1층 입점을 고려할 경우에는 상응하는 매출 확보 전략이 필수적이며, 예산에 따라 1층 외 공간을 활용한 운영 방식도 고려할 필요가 있습니다.

    7. 매출 특성 요약 (창업 준비)
    현재 상권 내 커피·음료 업종의 월 매출 총액은 약 3,540만 원, 건당 평균 매출(객단가)은 5,900원으로, 서울 커피·음료 업종 평균(5,200원) 대비 약 13% 높아 프리미엄 전략에 적합합니다.
    평일 매출(2,100만 원)이 주말 매출(1,442만 원)보다 높아, 직장인 중심의 평일 소비가 활발히 이루어지고 있음을 나타냅니다.
    30대 여성이 주요 소비층이며, 금요일 점심(12:00~14:00) 시간대에 매출이 집중되는 경향이 뚜렷합니다.
    초기 창업 시에는 타깃 고객에 맞춘 브런치 메뉴 및 테이크아웃 서비스 강화, 평일 점심 집중 마케팅 전략이 효과적일 것입니다.


    [예시 2 – 확장]
    👉종합 평가 

    청운효자동 상권은 고정 수요층과 관광 유입이 혼재된 구조로, 기존 브랜드가 이 지역의 특성과 잘 부합한다면 높은 시너지를 기대할 수 있습니다.
    점포 수는 2022~2024년까지 꾸준히 증가했으며, 프랜차이즈 점포 역시 함께 성장하여 브랜드 수용성이 높은 것으로 보입니다.
    그러나 최근 개폐업 수가 균형을 이루거나 폐업이 우세해지는 경향이 있으며, 임대료는 1층 기준 3.3㎡당 약 20만 원 수준으로 비용 부담이 존재합니다.
    따라서 확장을 고려할 경우, 입점 위치에 따른 리스크 분석과 브랜드 정체성과의 정합성 검토가 중요하며, 단순 확장보다는 지역 맞춤형 전략 수립이 필수적입니다. 구체적으로는 다음과 같은 전략이 고려될 수 있습니다:
    • 전통적 정서와 조화를 이루는 인테리어 및 서비스 콘셉트: 지역 고령층 및 관광객의 취향을 반영한 공간 디자인(예: 한옥 요소, 전통 색감, 고풍스러운 조명 등)
    • 지역 공동체 및 로컬 콘텐츠 연계: 지역 행사 참여, 문화 해설 프로그램 등과 연계하여 브랜드 인지도를 지역에 자연스럽게 스며들게 함
    • 관광객 대상의 패키지형 서비스 또는 기념품화 전략: 메뉴에 지역 스토리를 입히거나, 한정판 상품/패키지를 기획해 관광객 유입을 구매로 전환
    • 1층 외 공간을 활용한 유연한 구조 설계: 1층 입점이 부담스러운 경우, 2층 이상의 공간에 가성비 높은 집객 구조를 설계(예: 예약 중심 운영, 뷰 또는 프라이빗 공간 강조)

    이처럼 지역성과 브랜드 아이덴티티 간의 정합성 확보가 확장의 성공을 좌우하는 핵심 요인이 될 수 있습니다.

    1. 기본 지역 정보

    서울특별시 종로구 청운효자동은 전통문화와 고급 주거지가 공존하는 지역으로, 역사문화자산과 관광 인프라가 풍부합니다. 유동인구는 14,020명/ha로, 주거 인구는 47명/ha, 직장 인구는 23명/ha입니다.
    이 지역은 북촌한옥마을, 경복궁, 청와대 등 핵심 관광지와 인접해 있어 내외국인 방문 수요가 꾸준히 유지되고 있습니다. 이는 브랜드 인지도를 바탕으로 관광객 수요를 흡수할 수 있는 업종에 유리한 입지를 제공합니다. 청운효자동의 소비층은 전통적 취향을 지닌 중장년층이 다수를 차지하며, 프리미엄 이미지와 맞물리는 업종일수록 안정적인 수요 확보가 가능합니다.


    2. 상권 변화

    점포 수는 2022년 889개에서 2023년 941개, 2024년 946개로 지속 증가한 뒤, 2025년에는 937개로 소폭 조정되었습니다. 이는 일정 수준 이상의 상권 포화도가 존재함을 의미하며, 진입보다는 확장을 통한 브랜드 간 시너지 창출이 더 유효할 수 있음을 시사합니다.
    프랜차이즈와 일반 점포 모두 증가세를 보여왔다는 점은 청운효자동 상권이 다양한 형태의 점포를 수용할 수 있는 유연성을 지닌다는 신호이며, 이미 브랜드를 보유한 기업에게는 해당 입지 내 경쟁력 강화에 유리한 조건이 될 수 있습니다. 또한 프랜차이즈 점포 비율은 35%로, 인근 홍대 상권(42%) 대비 다소 낮아 브랜드 확장 여지가 있습니다


    3. 신생기업 생존율 및 영업 기간

    1년 생존율 85.3%, 3년 생존율 69.5%, 5년 생존율 50.7%로 확인되며, 비교적 높은 수준의 지속성을 유지하고 있습니다. 이는 상권의 기본적 안정성을 방증하며, 신규 진출보다는 운영 역량을 축적한 브랜드가 시장에 진입하거나 확장하기에 더 적합한 조건을 보여줍니다.
    장기적 관점에서, 기존 브랜드의 운영 노하우를 바탕으로 일정 수준의 매출 기반을 확보할 수 있는 환경이 조성되어 있음을 나타냅니다.

    아울러 평균 영업 기간은 10년 기준 약 4.8년, 30년 기준 약 7.2년으로, 단기 변동성보다 중장기 안정성이 비교적 확보된 상권임을 보여줍니다. 이는 확장 시 장기적 매출 구조와 브랜드 지속성을 동시에 고려할 수 있는 환경으로 해석할 수 있습니다.


    4. 개폐업 추이 및 진입 위험도

    개업과 폐업의 흐름을 보면, 2022년에는 개업 32건, 폐업 17건으로 창업이 활발했지만, 2025년에는 개업 16건, 폐업 22건으로 폐업이 앞서고 있습니다.
    이는 초기 진입 리스크가 높아지고 있는 반면, 이미 시장 내 경험과 브랜드 충성도를 확보한 업체라면 기존 자원과 역량을 활용해 상대적으로 안정적으로 확장할 수 있는 조건으로 해석할 수 있습니다. 진입보다 재진입, 확장을 통한 위험 분산이 더 효과적일 수 있는 구간입니다.


    5. 인구 및 유동 인구 특성

    14,000명/ha 내외의 유동인구는 비교적 안정적인 수준을 유지하고 있으며, 주거와 직장 인구의 분포도 균형적입니다. 이는 시간대별 유입 수요가 고르게 유지된다는 것을 의미하며, 매장 운영 시간이나 서비스 대상의 다양화 전략에 유리합니다.
    소비층은 고령층·중장년층 중심이지만, 관광 수요가 꾸준하다는 점에서 복합적 소비 성향을 고려한 브랜드 전략 수립이 가능하며, 본사 차원의 시너지형 모델 도입을 고려할 만합니다.


    6. 임대료 수준

    1층 임대료는 3.3㎡당 199,365원, 1층 외는 88,488원으로, 서울 평균 대비 높은 수준입니다. 임대료 부담은 존재하지만, 기존 브랜드의 신뢰성과 유입력, 가시성을 활용한 고수익 모델이라면 수익률을 통해 상쇄할 수 있는 구조입니다.
    특히 확장을 고려할 경우에는 1층 외 공간을 활용한 복합 운영 모델이나 인근 가맹점과의 클러스터 전략을 통해 임대 효율성을 높이는 방안도 유효합니다.
    1층 외 임대료는 3.3㎡당 88,000원으로, 서울 평균(110,000원) 대비 20% 저렴해 2층 이상 활용 시 비용 효율성이 있습니다.


    7. 매출 특성 요약
    현재 해당 상권의 커피·음료 업종은 월 매출 약 3,540만 원, 건당 평균 매출 약 5,900원으로, 브랜드 확장 시 지속 가능한 수익 기반을 확보할 수 있는 구조입니다.
    소비는 평일에 더 활발하게 이루어지고 있으며(평일 매출: 2,100만 원), 이는 직장인 중심 수요가 안정적으로 유지되고 있음을 시사합니다.
    주요 고객은 30대 여성, 금요일 점심 시간대에 매출이 집중되는 패턴이 확인됩니다.
    기존 브랜드 정체성과 연계된 프리미엄 테이크아웃 메뉴, 예약 기반 점심 서비스 도입이 확장 전략으로 적절할 수 있습니다.


    [예시 3 - 시장조사]
    👉종합 평가

    종로구 청운효자동 상권은 경복궁, 청와대, 북촌한옥마을 등 주요 관광 명소와 인접해 있어, 고정 주거 인구와 유동 인구가 혼재된 이중 구조의 수요 기반을 형성하고 있는 지역입니다. 이로 인해 단기적 활력과 안정성을 모두 갖춘 상권으로 평가됩니다.
    커피·음료 업종을 중심으로 2022년 889개에서 2024년 946개까지 점포 수가 꾸준히 증가하였으며, 1년 생존율도 85.3%로 매우 높은 수준을 기록하고 있어 시장 진입 초기의 수용력은 우수하다고 볼 수 있습니다. 다만, 5년 생존율이 50.7%로 급감하는 점은 장기적인 안정성 측면에서의 리스크를 시사합니다.
    또한, 2025년 기준 폐업 수(22건)가 개업 수(16건)를 초과하고 있으며, 1층 임대료는 3.3㎡당 약 199,000원, 1층 외는 88,000원 수준으로 나타나 임대 부담 역시 주요 고려 요인이 됩니다.
    이 상권은 고령층 중심의 정주 인구와 관광객 중심의 유동 인구가 혼재된 복합 소비 구조를 가지고 있기 때문에, 업종 선정 시 소비층의 이질성에 대한 정밀한 분석과 타깃 전략 수립이 필수적입니다. 점포 변화 추이, 생존율 곡선, 임대료 격차 등 다양한 지표를 종합적으로 고려하여 전략적인 시장 진입 및 확장 판단을 하시는 것이 바람직합니다.

    1. 기본 지역 정보

    서울특별시 종로구 청운효자동은 역사와 문화가 살아 숨 쉬는 지역으로, 고급 주거지와 주요 관광지가 인접해 있습니다. 유동인구는 14,020명/ha, 주거 인구는 47명/ha, 직장 인구는 23명/ha로 구성되어 있어, 지역의 생활 기반과 방문 수요가 혼재된 구조를 보입니다.
    북촌한옥마을, 경복궁, 청와대 등 주요 관광지가 가까워 지속적인 방문 수요가 있으며, 상권은 일시적 유행이 아닌 지속 가능한 구조로 형성되어 있습니다. 또한 고령층 및 중장년층이 주요 거주층이라는 점은 정서적 안정성과 전통적 취향 기반의 업종이 선호될 가능성을 시사합니다.

    2. 상권 변화

    상점 수는 2022년 889개에서 2023년 941개, 2024년 946개로 증가하다 2025년에는 937개로 다소 줄었습니다. 이는 전반적으로 성장 기반의 상권이나, 최근에는 조정 국면에 진입했음을 보여줍니다.
    프랜차이즈와 일반 점포 모두 증가한 점은 브랜드와 개인 창업이 공존하는 생태계가 형성되어 있음을 의미하며, 이는 다양한 비즈니스 모델 실험이 가능한 시장 구조로 해석될 수 있습니다.
    점포 수 증가율은 최근 3년간 6%로, 서울 평균(3%) 대비 2배 높은 성장세를 보이고 있습니다

    3. 신생기업 생존율 및 영업 기간 

    1년 생존율은 85.3%, 3년 생존율은 69.5%, 5년 생존율은 전국 평균(55%)보다 낮은 50.7%로 나타났습니다. 이는 진입 초기에는 성공 가능성이 높은 편이지만, 시간이 지남에 따라 생존률이 급감한다는 점에서 시장 내 경쟁과 지속가능성의 어려움도 내포하고 있습니다.
    이는 업종별로 경쟁 강도 및 시장 반응을 면밀히 관찰해야 하며, 중장기 생존을 위한 전략 차별화가 중요한 변수임을 보여줍니다.

    특히 평균 영업 기간은 10년 기준 약 4.8년, 30년 기준 약 7.2년으로 나타나, 해당 업종의 장기 생존 역량을 가늠할 수 있는 지표로 활용됩니다. 이는 시장조사 단계에서 진입·퇴출 주기와 리스크 평가에 참고할 수 있는 핵심 데이터입니다.


    4. 개폐업 추이 및 진입 위험도

    2022년에는 개업 32건, 폐업 17건으로 창업이 활발했으나, 2025년에는 개업 16건, 폐업 22건으로 역전 현상이 발생했습니다. 이는 시장 진입의 어려움이 증가하고 있음을 반영하며, 단순 진입보다는 수요 맞춤형 포지셔닝이 중요하다는 신호로 읽힙니다.
    최근 들어 폐업이 늘고 있다는 사실은 업종별 수요 변화나 소비 성향 변화에 대한 면밀한 사전조사가 필요함을 의미합니다.

    5. 인구 및 유동 인구 특성

    청운효자동의 유동인구는 분기별로 다소 변동은 있으나 약 14,000명/ha 수준으로 안정적인 편입니다. 주거 인구와 직장 인구의 구성도 균형적으로 나타나며, 이는 고정 수요와 방문 수요가 혼합된 상권 특성을 보여줍니다.
    관광객 유입과 더불어 지역 고령층 중심의 정주 인구가 있어 이중 소비층이 존재하는 구조이며, 업종이나 마케팅 전략 수립 시 이질적 수요층을 동시에 고려해야 하는 특징이 있습니다.

    6. 임대료 수준

    1층 임대료는 3.3㎡당 199,365원, 1층 외는 88,488원으로 측정되며, 전국 평균 대비 높은 수준입니다. 이는 입지적 매력도가 높은 대신 비용 부담도 큰 상권임을 의미합니다.
    시장조사 관점에서, 고임대료를 감내할 수 있는 업종군 또는 고수익을 창출 가능한 업종을 우선적으로 탐색할 필요가 있으며, 단기적 수익보다는 브랜드 가치와 입지 전략의 적합성을 기준으로 평가하는 것이 타당합니다.

    7. 매출 특성 요약
    해당 상권의 커피·음료 업종은 분석 기간 동안 월 매출 약 3,540만 원, 객단가 약 5,900원을 기록하고 있으며, 매출은 주로 평일 중심(2,100만 원 / 주말: 1,442만 원)으로 발생하고 있습니다.
    월 매출 3,540만 원은 서울 동일 업종 평균(3,200만 원)보다 약 11% 높아 시장 수요가 탄탄함을 시사합니다.
    매출 기여도가 가장 높은 고객층은 30대 여성으로, 금요일 점심 시간대에 소비가 집중됩니다.
    이러한 흐름은 해당 지역이 직장인 + 여성 중심 소비 상권이라는 특성을 지니며, 브런치·프리미엄 음료·테이크아웃 수요가 강하다는 것을 나타냅니다.
    향후 트렌드 기반 신규 브랜드 또는 타깃 특화 서비스가 시장 진입 시 경쟁력을 가질 수 있을 것입니다.


    항목은 반드시 다음 제목 형식을 따라:

    👉 종합 평가
    1. 기본 지역 정보  
    2. 상권 변화  
    3. 신생 기업 생존율 및 평균 영업 기간  
    4. 개폐업 추이 및 진입 위험도  
    5. 인구 및 유동 인구 특성  
    6. 임대료 수준  
    7. 매출 특성 요약


    ⚠️ 아래 지침은 반드시 지켜:

    - 제목은 반드시 '1. 제목'처럼 숫자와 함께 작성
    - 임대료, 매출, 점포 수 등 주요 지표는 반드시 서울 평균 대비 몇 % 높은지/낮은지 벤치마크 비교를 포함해서 서술해라.
    - 벤치마크 문장은 반드시 각 항목에서 최소 1회 이상 포함한다. (예: "1층 임대료는 3.3㎡당 199,000원으로, 서울 평균 170,000원 대비 17% 높음")
    - 7번 매출 특성 요약은 자연스러운 문장으로 특성을 요약한 뒤, 전략 제안은 각 줄 앞에 '•'를 붙이고 줄마다 줄바꿈(\n)으로 구분해서 출력해줘.
    - 전략 제안 문장은 항상 줄 맨 앞에 '•' 붙여서 출력해.
    - 종합 평가는 반드시 '👉 종합 평가'로 시작.
    - 먼저 행정동 전체 수준의 상권 평가와 공통 전략을 작성한 뒤, 이어서 zone별 데이터 차이에 따른 특화 전략을 각각 작성.


    사용자의 리포트 목적은 **'{purpose}'**이므로, 이에 맞춰 강조점을 조정해서 작성해.
    - 목적: **'{purpose}'**
    - 현실적이고 수치 기반의 전략 제안 포함
    - 창업 준비일 경우: 진입 가능성과 실패 방지 전략
    - 확장일 경우: 시너지 가능성과 로컬 정합성
    - 시장조사일 경우: 데이터 기반 트렌드 요약과 전략적 판단 가이드
    """
            },
            {
                "role": "user",
                "content": actual_input
            }
        ]
    )

    print("7. GPT 리포트 응답 수신 완료")

    # ✅ GPT 응답 받기
    # GPT 응답 받기
    report = response.choices[0].message.content

    # ✅ markdown 스타일 제거
    import re
    report = re.sub(r'^#+\s*', '', report, flags=re.MULTILINE)
    report = re.sub(r'^\-\s*', '', report, flags=re.MULTILINE)
    report = re.sub(r'^\*\s*', '', report, flags=re.MULTILINE)

    # ✅ 종합 평가 맨 위로 정렬
    sections = re.split(r"(?=\n?\d+\.\s|👉)", report.strip())
    sections_sorted = sorted(sections, key=lambda x: 0 if "👉 종합 평가" in x else 1)
    report_reordered = "\n".join([s.strip() for s in sections_sorted if s.strip()])

    header_line = f"서울특별시 {gu_name} {region}에서의 {category_small} {purpose}을(를) 위한 리포트입니다.\n\n"

    with open("report.txt", "w", encoding="utf-8") as f:
        f.write(header_line + report_reordered)
