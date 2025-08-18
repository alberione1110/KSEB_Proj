import os
import time
import json
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.preprocessing import MinMaxScaler
import google.generativeai as genai
# from openai import OpenAI   # 필요 시 사용
import pymysql

from config.settings import get_engine  # ✅ DB URL/Engine은 환경변수에서 로드


def run_recommendation(category_small, gu_name):
    """
    - 민감정보(호스트/계정/비번/API키) 제거: config.settings / .env 사용
    - SQL 인젝션 방지: 모든 쿼리 파라미터 바인딩
    - 캐시는 ./cache 폴더에 저장
    """
    # ── DB 엔진 (환경변수 로드) ──────────────────────────────────────────────
    engine = get_engine()

    # ── (선택) 연결 확인 ────────────────────────────────────────────────────
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print("✅ DB 연결 확인")
    except Exception as e:
        print("❌ DB 연결 실패:", e)
        raise

    # ── 구(region_code) 조회: 파라미터 바인딩 ───────────────────────────────
    sql_gu_code = """
        SELECT DISTINCT region_code
        FROM floating_population_stats
        WHERE region_name = %s
        LIMIT 1
    """
    gu_code_df = pd.read_sql_query(sql_gu_code, engine, params=(gu_name,))
    if gu_code_df.empty:
        raise ValueError(f"region_name '{gu_name}'에 해당하는 region_code를 찾지 못했습니다.")
    gu_code = str(gu_code_df.iloc[0]['region_code'])

    print(f"선택한 구 '{gu_name}'의 지역 코드: {gu_code}")
    print(f"선택한 업종: {category_small}")

    # ── 캐시 디렉터리 ───────────────────────────────────────────────────────
    os.makedirs("cache", exist_ok=True)

    # ── 캐시/조회 유틸 ─────────────────────────────────────────────────────
    def load_or_cache_query(name, table_name):
        path = f"cache/{name}.feather"
        if os.path.exists(path):
            print(f"📂 캐시 불러옴(원본 전체): {name}")
            return pd.read_feather(path)

        print(f"💾 원본 전체 데이터 저장: {name}")
        df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
        df.to_feather(path)
        return df

    def query_table(
        table_name,
        extra_condition="",
        category_col='category_small',
        indicator_col='indicator',
        indicator_val=None,
        columns='*'
    ):
        # ⚠️ 문자열 이어붙이기 대신 파라미터 바인딩 사용
        base = f"SELECT {columns} FROM {table_name} WHERE region_code LIKE %s"
        params = [f"{gu_code}%"]

        if category_small and category_col:
            base += f" AND {category_col} = %s"
            params.append(category_small)

        if indicator_val and indicator_col:
            base += f" AND {indicator_col} = %s"
            params.append(indicator_val)

        if extra_condition:
            base += f" AND {extra_condition}"

        base += " ORDER BY region_code, year, quarter"
        return pd.read_sql_query(base, engine, params=tuple(params))

    def load_table(table_name):
        try:
            return pd.read_sql(f"SELECT * FROM {table_name}", engine)
        except Exception as e:
            print(f"❌ [ERROR] 테이블 {table_name} 로딩 실패:", e)
            engine.dispose()
            raise

    def add_region_service_names(df, zone_df, service_df, rent_df):
        df['zone_id'] = df['zone_id'].astype(str)
        zone_df['zone_id'] = zone_df['zone_id'].astype(str)

        df = df.merge(zone_df[['zone_id', 'region_name']], on='zone_id', how='left')
        rent_test_df = rent_df[['region_name', 'region_code']].drop_duplicates(subset=['region_name', 'region_code'])
        df = df.merge(rent_test_df[['region_name', 'region_code']], on='region_name', how='left')
        df = df[df['region_code'].notna()]
        df = df.merge(service_df[['service_code', 'service_name']], on='service_code', how='left')

        # 원래 코드에 category_small+'\r' 비교가 있었는데, 데이터 정합성 이슈 가능.
        # 개행/캐리지리턴 제거 후 비교로 보수적으로 변경.
        df['service_name'] = df['service_name'].astype(str).str.replace(r'[\r\n]+', '', regex=True)
        return df[df['service_name'] == category_small]

    # ── 풀테이블 1회 캐싱 ───────────────────────────────────────────────────
    t0 = time.time()
    pop_full_df     = load_or_cache_query("pop_df",      "floating_population_stats")
    rent_full_df    = load_or_cache_query("rent_df",     "rental_price_stats")
    age_full_df     = load_or_cache_query("age_df",      "subcategory_avg_operating_period_stats")
    store_full_df   = load_or_cache_query("store_df",    "subcategory_store_count_stats")
    survive_full_df = load_or_cache_query("survive_df",  "subcategory_startup_survival")
    openclose_full_df = load_or_cache_query("openclose_df", "subcategory_openclose_stats")

    zone_df    = load_table('zone_table')
    zone_df['zone_id']= zone_df['zone_id'].astype(str)
    service_df = load_table('service_type')

    # ── 최근 4개 분기 필터 ─────────────────────────────────────────────────
    recent_periods = (
        pop_full_df[['year', 'quarter']]
        .drop_duplicates()
        .sort_values(['year', 'quarter'], ascending=False)
        .head(4)
        .sort_values(['year', 'quarter'])
    )
    recent_period_tuples = set(map(tuple, recent_periods.to_numpy()))

    def filter_recent_quarters(df):
        return df[df[['year', 'quarter']].apply(tuple, axis=1).isin(recent_period_tuples)]

    def get_pop_df(full_df, gu_code):
        full_df['region_code'] = full_df['region_code'].astype(str)
        return full_df[full_df['region_code'].str.startswith(str(gu_code))]

    def get_rent_df(full_df, gu_code):
        full_df['region_code'] = full_df['region_code'].astype(str)
        return full_df[full_df['region_code'].str.startswith(str(gu_code))]

    def get_age_df(full_df, gu_code, category_small):
        full_df['region_code'] = full_df['region_code'].astype(str)
        return full_df[
            full_df['region_code'].str.startswith(str(gu_code)) &
            (full_df['category_small'] == category_small) &
            (full_df['indicator'] == 'avg_operating_years_30')
        ]

    def get_store_df(full_df, gu_code, category_small):
        full_df['region_code'] = full_df['region_code'].astype(str)
        return full_df[
            full_df['region_code'].str.startswith(str(gu_code)) &
            (full_df['category_small'] == category_small) &
            (full_df['indicator'] == 'store_total')
        ]

    def get_survive_df(full_df, gu_code, category_small):
        full_df['region_code'] = full_df['region_code'].astype(str)
        return full_df[
            full_df['region_code'].str.startswith(str(gu_code)) &
            (full_df['category_small'] == category_small)
        ]

    def get_openclose_df(full_df, gu_code, category_small):
        full_df['region_code'] = full_df['region_code'].astype(str)
        return full_df[
            full_df['region_code'].str.startswith(str(gu_code)) &
            (full_df['category_small'] == category_small)
        ]

    pop_filtered     = filter_recent_quarters(get_pop_df(pop_full_df, gu_code))
    rent_filtered    = filter_recent_quarters(get_rent_df(rent_full_df, gu_code))
    age_filtered     = filter_recent_quarters(get_age_df(age_full_df, gu_code, category_small))
    store_filtered   = filter_recent_quarters(get_store_df(store_full_df, gu_code, category_small))
    survive_filtered = filter_recent_quarters(get_survive_df(survive_full_df, gu_code, category_small))
    openclose_filtered = filter_recent_quarters(get_openclose_df(openclose_full_df, gu_code, category_small))

    # ── 매출 테이블(연도별) 캐시 ────────────────────────────────────────────
    years = [2022, 2023, 2024]
    def load_or_cache_table(table_name, year):
        filename = f"cache/{table_name}_{year}.feather"
        if os.path.exists(filename):
            return pd.read_feather(filename)
        df = pd.read_sql(f"{'SELECT * FROM ' + table_name + '_' + str(year)}", engine)
        df.to_feather(filename)
        return df

    zone_store_count_all   = pd.concat([load_or_cache_table("zone_store_count", year).assign(year=year) for year in years])
    sales_by_gender_age_all= pd.concat([load_or_cache_table("sales_by_gender_age", year).assign(year=year) for year in years])
    summary_sales_all      = pd.concat([load_or_cache_table("sales_summary", year).assign(year=year) for year in years])

    # ── 공통 전처리 ────────────────────────────────────────────────────────
    for df in (sales_by_gender_age_all, summary_sales_all, zone_store_count_all):
        df['zone_id'] = df['zone_id'].astype(str)

    gender_known_all   = sales_by_gender_age_all[sales_by_gender_age_all['gender'].isin(['여성', '남성'])]
    gender_unknown_all = sales_by_gender_age_all[~sales_by_gender_age_all['gender'].isin(['여성', '남성'])]

    gender_known_all   = add_region_service_names(gender_known_all, zone_df, service_df, rent_full_df)
    gender_unknown_all = add_region_service_names(gender_unknown_all, zone_df, service_df, rent_full_df)

    def merge_sales_with_store(df, group_cols, sales_col='sales_amount'):
        df = df.merge(
            zone_store_count_all[['zone_id', 'service_code', 'year', 'quarter', 'count']],
            on=['zone_id', 'service_code', 'year', 'quarter'],
            how='inner'
        )
        df['avg_sales_per_store'] = df[sales_col] / df['count']
        return df

    # 성별별
    gender_all = merge_sales_with_store(gender_known_all, ['zone_id', 'service_code', 'year', 'quarter'])
    gender_all = gender_all[gender_all['region_code'].astype(str).str.startswith(gu_code)]
    gender_all = gender_all[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "gender", "avg_sales_per_store", "count"]]
    gender_sales = {year: gender_all[gender_all['year'] == year].reset_index(drop=True) for year in years}

    # 연령대별
    age_all = merge_sales_with_store(gender_unknown_all, ['zone_id', 'service_code', 'year', 'quarter'])
    age_all = age_all[age_all['region_code'].astype(str).str.startswith(gu_code)]
    age_all = age_all[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "age_group", "avg_sales_per_store", "count"]]
    age_sales = {year: age_all[age_all['year'] == year].reset_index(drop=True) for year in years}

    # 전체 요약
    summary_sales_all = summary_sales_all[summary_sales_all['service_name'] == category_small]
    summary_sales_all = merge_sales_with_store(summary_sales_all, ['zone_id', 'service_code', 'year', 'quarter'], sales_col='monthly_sales')
    summary_sales_all = summary_sales_all[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "avg_sales_per_store", "count"]]
    summary_sales = {year: summary_sales_all[summary_sales_all['year'] == year].reset_index(drop=True) for year in years}

    # ── 통계/점수 계산(기존 로직 유지) ───────────────────────────────────────
    def get_avg_fast(df, group_col='region_code', val_col=None, rename_col=None):
        df = df[[group_col, 'region_name', val_col]].copy()
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        df = df[df[val_col].notna()]
        grouped = df.groupby(group_col, sort=False).agg({val_col: 'mean', 'region_name': 'first'}).reset_index()
        if rename_col:
            grouped = grouped.rename(columns={val_col: rename_col})
        return grouped

    def get_group_avg(df, group_col, rename_map: dict, round_digits=2):
        agg_dict = {col: 'mean' for col in rename_map.keys()}
        agg_dict['region_name'] = 'first'
        grouped = df.groupby(group_col, sort=False).agg(agg_dict).reset_index()
        grouped = grouped.rename(columns=rename_map)
        return grouped.round(round_digits)

    pop_avg   = get_avg_fast(pop_filtered,   val_col='floating_population', rename_col='유동인구')
    rent_avg  = get_avg_fast(rent_filtered,  val_col='rent_total',          rename_col='임대시세')
    age_avg   = get_avg_fast(age_filtered,   val_col='value',               rename_col='평균영업기간(년)')
    store_avg = get_avg_fast(store_filtered, val_col='value',               rename_col='점포수')

    survive_avg   = get_group_avg(survive_filtered, 'region_code', {'survival_1yr': '1년 생존율(%)','survival_3yr': '3년 생존율(%)','survival_5yr': '5년 생존율(%)'})
    openclose_avg = get_group_avg(openclose_filtered, 'region_code', {'num_open': '평균 개업수','num_close': '평균 폐업수'})

    from functools import reduce
    dfs = [pop_avg, rent_avg, age_avg, store_avg, survive_avg, openclose_avg]
    merged_df = reduce(lambda L, R: pd.merge(L, R, on=['region_code', 'region_name'], how='inner', sort=False), dfs)
    merged_df = merged_df.rename(columns={'region_code': '행정동코드', 'region_name': '행정동명'}).sort_values(by='유동인구', ascending=False, ignore_index=True)

    # 매출 평균들
    def get_avg_sales_fast(sales_df, group_col):
        sales_df = sales_df[['region_name', 'service_name', 'service_code', group_col, 'avg_sales_per_store']].copy()
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])
        out = (
            sales_df.groupby(['region_name', group_col], sort=False)
            .agg({'avg_sales_per_store':'mean','service_name':'first','service_code':'first'})
            .reset_index()
        )
        out['avg_sales_per_store'] = (out['avg_sales_per_store'] / 3).round(2)
        return out

    def get_avg_sales_sum_fast(sales_df):
        sales_df = sales_df[['region_name', 'service_name', 'service_code', 'avg_sales_per_store']].copy()
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])
        out = (
            sales_df.groupby('region_name', sort=False)
            .agg({'avg_sales_per_store':'mean','service_name':'first','service_code':'first'})
            .reset_index()
        )
        out['avg_sales_per_store'] = (out['avg_sales_per_store'] / 3).round(2)
        return out

    gender_list, age_list, summary_list = [], [], []
    for year in years:
        g = get_avg_sales_fast(gender_sales[year], group_col='gender'); g['year'] = year; gender_list.append(g)
        a = get_avg_sales_fast(age_sales[year],   group_col='age_group'); a['year'] = year; age_list.append(a)
        s = get_avg_sales_sum_fast(summary_sales[year]); s['year'] = year; summary_list.append(s)

    gender_df  = pd.concat(gender_list, ignore_index=True).rename(columns={'region_name':'행정동명','service_name':'업종명','service_code':'업종코드','gender':'성별','avg_sales_per_store':'성별별 평균 월 매출'})
    age_df     = pd.concat(age_list,    ignore_index=True).rename(columns={'region_name':'행정동명','service_name':'업종명','service_code':'업종코드','age_group':'연령대','avg_sales_per_store':'연령대별 평균 월 매출'})
    summary_df = pd.concat(summary_list, ignore_index=True).rename(columns={'region_name':'행정동명','service_name':'업종명','service_code':'업종코드','avg_sales_per_store':'평균 월 매출'})

    gender_df.to_json('gender_avg_sales_dong.json',  orient='records', force_ascii=False, indent=4)
    age_df.to_json('age_avg_sales_dong.json',       orient='records', force_ascii=False, indent=4)
    summary_df.to_json('summary_avg_sales_dong.json',orient='records', force_ascii=False, indent=4)

    pivot_summary = (
        summary_df
        .pivot_table(index=['행정동명','업종명'], columns='year', values='평균 월 매출', aggfunc='mean')
        .rename(columns={2022:'2022_평균매출', 2023:'2023_평균매출', 2024:'2024_평균매출'})
        .reset_index()
    )

    merged_df = merged_df.merge(pivot_summary[['행정동명','2022_평균매출','2023_평균매출','2024_평균매출']], on='행정동명', how='left')
    merged_df.to_json('merged_dong.json', orient='records', force_ascii=False, indent=4)

    score_columns   = ['유동인구','임대시세','평균영업기간(년)','점포수','1년 생존율(%)','3년 생존율(%)','5년 생존율(%)','평균 개업수','평균 폐업수']
    score_columns_2 = ['2022_평균매출','2023_평균매출','2024_평균매출']
    all_score_columns = score_columns + score_columns_2

    weights = {
        '유동인구': 0.2422, '임대시세': -0.1453, '평균영업기간(년)': 0.0484, '점포수': 0.3897,
        '1년 생존율(%)': 0.0182, '3년 생존율(%)': 0.0303, '5년 생존율(%)': 0.0484,
        '평균 개업수': 0.0606, '평균 폐업수': -0.0347,
        '2022_평균매출': 0.0870, '2023_평균매출': 0.1275, '2024_평균매출': 0.1275
    }

    norm_input = merged_df[all_score_columns].replace([np.inf,-np.inf], np.nan).fillna(0)
    scaler = MinMaxScaler()
    normalized_values = scaler.fit_transform(norm_input)
    normalized_df = pd.DataFrame(normalized_values, columns=[f'norm_{c}' for c in all_score_columns])

    merged_with_norm = pd.concat([merged_df.reset_index(drop=True), normalized_df], axis=1)
    weight_array = np.array([weights[c] for c in all_score_columns])
    norm_cols = [f'norm_{c}' for c in all_score_columns]
    merged_with_norm['행정동_추천점수'] = merged_with_norm[norm_cols].values.dot(weight_array)

    final_result = (
        merged_with_norm
        .drop(columns=norm_cols + ['업종명'])
        .loc[merged_with_norm['행정동코드'].astype(str).str.len() != 5]
        .replace([np.inf,-np.inf], np.nan)
        .dropna(subset=score_columns_2)
        .sort_values(by='행정동_추천점수', ascending=False)
        .reset_index(drop=True)
    )

    final_result.to_csv('filtered_result_dong.csv', index=False, encoding='utf-8-sig')
    final_result.to_json('filtered_result_dong.json', orient='records', force_ascii=False, indent=4)

    # ── LLM 설정 (환경변수) ────────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 필요합니다.")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

    few_shot_examples = """
    [예시 1]
    서교동은 압도적인 유동인구와 매우 높은 월매출을 바탕으로 커피-음료 수요가 풍부한 핵심 상권입니다.
    주변 상주 인구 및 직장인이 많아 테이크아웃과 휴식 수요가 꾸준하며, 높은 잠재 수익을 기대할 수 있습니다.
    특히, 타 지역 대비 낮은 임대시세는 안정적인 운영 환경을 제공하여 창업 부담을 줄여줍니다.

    [예시 2]
    행당동은 매우 높은 유동인구와 풍부한 미용실 점포수로 미용 서비스에 대한 탄탄한 수요가 형성되어 있습니다.
    특히 지속적으로 상승하는 높은 평균 월매출은 압도적인 수익성을 기대하게 합니다.
    이는 활발한 소비력과 업종 특성을 고려할 때, 미용실 창업에 매우 유리한 환경을 제공합니다.
    """

    def generate_region_summary(row, gu_name, category_small):
        weights_info = "가중치는 유동인구(0.24), 점포수(0.39), 2024 평균 매출(0.13) 등이 큽니다."
        prompt = f"""
        당신은 상권 분석 전문가입니다.
        아래는 '{gu_name}' 지역 '{category_small}' 업종의 특정 행정동 핵심 상권 지표입니다:

        참고용 예시를 확인하세요:
        {few_shot_examples}

        아래 지표를 바탕으로 수치는 최소화하고, '{category_small}' 업종에 왜 적합한지
        지역 특성과 업종 수요의 연관성을 들어
        핵심 장점 2~3개를 3줄 이내로 간결하고 긍정적으로 작성하세요.

        - 행정동명: {row['행정동명']}
        - 유동인구: {int(row['유동인구']):,}명
        - 임대시세: {int(row['임대시세']):,}원/평
        - 평균영업기간: {row['평균영업기간(년)']}년
        - 점포수: {row['점포수']}개
        - 3년 생존율: {row['3년 생존율(%)']}%
        - 5년 생존율: {row['5년 생존율(%)']}%
        - 평균 개업수: {row['평균 개업수']}개
        - 평균 폐업수: {row['평균 폐업수']}개
        - 2022 평균 월매출: {int(row['2022_평균매출']):,}원
        - 2023 평균 월매출: {int(row['2023_평균매출']):,}원
        - 2024 평균 월매출: {int(row['2024_평균매출']):,}원

        {weights_info}
        """
        response = model.generate_content(prompt)
        return response.text.strip()

    top_n = 5
    recommendation_list = []
    for _, row in final_result.head(top_n).iterrows():
        full_district_name = f"{gu_name} {row['행정동명']}"
        reason = generate_region_summary(row, gu_name, category_small)
        recommendation_list.append({'district': full_district_name, 'reason': reason})

    recommendation_dict = {category_small: recommendation_list}
    with open('recommendation_dong.json', 'w', encoding='utf-8') as f:
        json.dump(recommendation_dict, f, ensure_ascii=False, indent=4)

    print("✅ JSON 저장 완료")
    print(json.dumps(recommendation_dict, ensure_ascii=False, indent=4))

    # 함수 반환(필요 시)
    return recommendation_dict
