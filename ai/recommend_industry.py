import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from functools import reduce
from sklearn.preprocessing import MinMaxScaler
import google.generativeai as genai
import pymysql
import json

def run_industry_recommendation(region, gu_name) :
    # RDS 정보
    host = 'daktor-commercial-prod.czig88k8s0e8.ap-northeast-2.rds.amazonaws.com'
    port = 3306
    user = 'oesnue'
    password = 'gPwls0105!' #안되면 gPwls0105
    database = 'daktor_db'

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


    # SQLAlchemy 엔진 생성
    engine = create_engine(
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
        connect_args={'charset':'utf8mb4'}
    )

    # 공통 유틸 함수
    def get_recent_quarters_by_category(df, group_cols=['category_small'], num_quarters=4):
        df_sorted = df.sort_values(by=group_cols + ['year', 'quarter'])
        return df_sorted.groupby(group_cols, group_keys=False).tail(num_quarters)

    def load_table(table_name):
        try:
            return pd.read_sql(f"SELECT * FROM {table_name}", engine)
        except Exception as e:
            print(f"❌ [ERROR] 테이블 {table_name} 로딩 실패:", e)
            # 롤백 강제 실행
            engine.dispose()  # 현재 연결 완전히 초기화
            raise e
        
    def query_table(table_name, extra_condition="", category_col=None, indicator_col='indicator', indicator_val=None):
        use_region_code = 'region_code' in pd.read_sql(f"SHOW COLUMNS FROM {table_name}", engine)['Field'].values
        conditions = []

        if use_region_code:
            conditions.append(f"region_code LIKE '{dong_code}%%'")
        elif target_dong and category_col:
            conditions.append(f"{category_col} = '{target_dong}'")
        if indicator_val and indicator_col:
            conditions.append(f"{indicator_col} = '{indicator_val}'")
        if extra_condition:
            conditions.append(extra_condition)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM {table_name} WHERE {where_clause} ORDER BY year, quarter"
        return pd.read_sql(sql, engine)

    def query_sales(table, service_code=None):
        cond = f"region_name = '{target_dong}'"
        if service_code:
            cond += f" AND service_code = '{service_code}'"
        sql = f"SELECT * FROM {table} WHERE {cond} ORDER BY service_code, zone_id, year, quarter"
        df = pd.read_sql(sql, engine)
        return df.drop_duplicates(subset=["region_name", "year", "quarter", "service_code", "monthly_sales"])

    def add_region_service_names(df, zone_df, service_df, target_dong=None):
        df['zone_id'] = df['zone_id'].astype(str)
        zone_df['zone_id'] = zone_df['zone_id'].astype(str)

        df = df.merge(zone_df, on='zone_id', how='left')
        df = df.merge(service_df, on='service_code', how='left')
        if target_dong:
            df = df[df['region_name'] == target_dong]
        return df

    # 사용자 입력
    target_gu = '{gu_name}'
    target_dong = '{region}'

    # 구/동 코드 조회
    dong_query = f"SELECT DISTINCT region_code FROM subcategory_avg_operating_period_stats WHERE region_name = '{target_dong}' LIMIT 1"
    dong_code = pd.read_sql(dong_query, engine).iloc[0]['region_code']
    print(f"선택한 동 '{target_dong}'의 지역 코드: {dong_code}")

    # 기본 테이블 불러오기
    zone_df = load_table('zone_table')
    zone_df['zone_id'] = zone_df['zone_id'].astype(str)
    service_df = load_table('service_type')

    # 지표 테이블 로딩 및 최근 4분기 필터링
    indicators = {
        'age': ('subcategory_avg_operating_period_stats', 'avg_operating_years_30'),
        'store': ('subcategory_store_count_stats', 'store_total'),
        'survive': ('subcategory_startup_survival', None),
        'openclose': ('subcategory_openclose_stats', None)
    }
    filtered_data = {}
    for key, (table, indicator) in indicators.items():
        df = query_table(table, indicator_val=indicator)
        if key in ['age', 'store']:
            filtered_data[key] = get_recent_quarters_by_category(df)[["category_small", "region_name", "region_code", "year", "quarter", "indicator", "value"]]
        elif key == 'survive':
            filtered_data[key] = get_recent_quarters_by_category(df)[["category_small", "region_name", "region_code", "year", "quarter",
                                                                      "survival_1yr", "survival_3yr", "survival_5yr"]]
        else:  # openclose
            filtered_data[key] = df[["category_small", "region_name", "region_code", "year", "quarter",
                                     "num_open", "num_close"]]

    # 매출 관련 데이터 처리
    years = [2022, 2023, 2024]
    gender_sales = {}
    gender_sales_test ={}
    age_sales = {}
    summary_sales = {}

    for year in years:
        st_ct_df = load_table(f"zone_store_count_{year}")
        gender_df = load_table(f"sales_by_gender_age_{year}")
        gender_known = gender_df[gender_df['gender'].isin(['여성', '남성'])]
        gender_unknown = gender_df[~gender_df['gender'].isin(['여성', '남성'])]

        gender_known = add_region_service_names(gender_known, zone_df, service_df, target_dong)
        gender_unknown = add_region_service_names(gender_unknown, zone_df, service_df, target_dong)

        #----gender
        gender_sales[year] = gender_known[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "gender", "sales_amount"]] \
            .sort_values(by=["service_name", "gender", "year", "quarter"]).reset_index(drop=True)

        gender_sales[year] = gender_sales[year].merge(st_ct_df[['zone_id', 'service_code', 'year', 'quarter','count']],on=['zone_id', 'service_code', 'year', 'quarter'],how='inner')
        gender_sales[year].loc[:, 'avg_sales_per_store'] = gender_sales[year]['sales_amount'] / gender_sales[year]['count']

        gender_sales[year] = gender_sales[year][["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "gender", "avg_sales_per_store","count"]] \
            .sort_values(by=["service_name", "gender", "year", "quarter"]).reset_index(drop=True)

        #----age-group
        age_sales[year] = gender_unknown[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "age_group", "sales_amount"]] \
            .sort_values(by=["service_name", "age_group", "year", "quarter"]).reset_index(drop=True)
        
        age_sales[year] = age_sales[year].merge(st_ct_df[['zone_id', 'service_code', 'year', 'quarter','count']],on=['zone_id', 'service_code', 'year', 'quarter'],how='inner')
        age_sales[year].loc[:, 'avg_sales_per_store'] = age_sales[year]['sales_amount'] / age_sales[year]['count']

        age_sales[year] = age_sales[year][["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "age_group", "avg_sales_per_store","count"]] \
            .sort_values(by=["service_name", "age_group", "year", "quarter"]).reset_index(drop=True)

        #----summary
        sales_df = query_sales(f"sales_summary_{year}")
        summary_sales[year] = sales_df[["region_name", "service_name", "zone_id", "service_code", "year", "quarter", "monthly_sales"]]
        summary_sales[year].loc[:, 'zone_id'] = summary_sales[year]['zone_id'].astype(str)

        summary_sales[year] = summary_sales[year].merge(st_ct_df[['zone_id', 'service_code', 'year', 'quarter','count']],on=['zone_id', 'service_code', 'year', 'quarter'],how='inner')
        summary_sales[year].loc[:, 'avg_sales_per_store'] = summary_sales[year]['monthly_sales'] / summary_sales[year]['count']

        summary_sales[year] = summary_sales[year][["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "avg_sales_per_store","count"]] \
            .sort_values(by=["service_name", "year", "quarter"]).reset_index(drop=True)

    # 출력 예시
    for year in years:
        print(f"\n📊 업종 성별 매출 점포 평균{year}\n", gender_sales[year])
        print(f"\n📊 업종 연령대 매출 {year}\n", age_sales[year])
        print(f"\n📊 업종 분기별 월매출{year}\n", summary_sales[year])


    # 평균값 계산 함수
    def get_avg(df, group_col='category_small', val_col=None, rename_col=None):
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        df = df.dropna(subset=[val_col])
        avg = df.groupby(group_col).agg({
            val_col: 'mean',
            'region_name': 'first'
        }).round(2).reset_index()
        if rename_col:
            avg = avg.rename(columns={val_col: rename_col})
        return avg

    # 평균 계산
    age_avg = get_avg(filtered_data['age'], val_col='value', rename_col='평균영업기간(년)')
    store_avg = get_avg(filtered_data['store'], val_col='value', rename_col='점포수')

    survive_avg = filtered_data['survive'].groupby('category_small').agg({
        'survival_1yr': 'mean',
        'survival_3yr': 'mean',
        'survival_5yr': 'mean',
        'region_name': 'first'
    }).round(2).reset_index().rename(columns={
        'survival_1yr': '1년 생존율(%)',
        'survival_3yr': '3년 생존율(%)',
        'survival_5yr': '5년 생존율(%)'
    })

    openclose_avg = filtered_data['openclose'].groupby('category_small').agg({
        'num_open': 'mean',
        'num_close': 'mean',
        'region_name': 'first'
    }).round(2).reset_index().rename(columns={
        'num_open': '평균 개업수',
        'num_close': '평균 폐업수'
    })

    # 병합
    dfs = [age_avg, store_avg, survive_avg, openclose_avg]
    from functools import reduce
    merged_df = reduce(lambda left, right: pd.merge(left, right, on=['category_small', 'region_name']), dfs)

    # 컬럼 정리
    merged_df = merged_df.rename(columns={
        'category_small': '업종명',
        'region_name': '행정동명'
    }).sort_values(by='점포수', ascending=False).reset_index(drop=True)

    # 출력
    pd.set_option('display.float_format', '{:,.2f}'.format)
    print("📊 종합 지역 상권 요약 리포트")
    print(merged_df)


    def get_avg_sales(sales_df, group_col):
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])
        
        avg_df = sales_df.groupby(['service_code', group_col]).agg({
            'avg_sales_per_store': 'mean',
            'region_name': 'first',
            'service_name': 'first'
        }).round(2).reset_index()

        avg_df['avg_sales_per_store'] = (avg_df['avg_sales_per_store'] / 3).round(2)

        return avg_df

    def get_avg_sales_sum(sales_df, group_col=None):
        # 매출 데이터를 숫자로 변환, 결측치 제거
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])

        # 기본 그룹핑 컬럼: 업종 코드
        group_cols = ['service_code']
        #if group_col:
        #    group_cols.append(group_col)  # 추가 그룹핑 컬럼 (예: 지역코드 등)

        # 그룹별 평균 매출 계산
        avg_df = sales_df.groupby(group_cols).agg({
            'avg_sales_per_store': 'mean',     # 분기별 평균 매출
            'region_name': 'first',            # 대표 지역명 (group_col이 지역일 경우)
            'service_name': 'first'            # 업종명
        })

        # 분기 매출 → 월평균 매출로 환산
        avg_df['avg_sales_per_store'] = (avg_df['avg_sales_per_store'] / 3).round(2)

        return avg_df


    # 결과 저장 리스트
    gender_list = []
    age_list = []
    summary_list = []

    for year in years:
        # 성별별 평균
        gender_avg_df = get_avg_sales(gender_sales[year], group_col='gender')
        gender_avg_df['year'] = year
        gender_list.append(gender_avg_df)

        # 연령대별 평균
        age_avg_df = get_avg_sales(age_sales[year], group_col='age_group')
        age_avg_df['year'] = year
        age_list.append(age_avg_df)

        # 전체 업종 평균
        summary_avg_df = get_avg_sales_sum(summary_sales[year], group_col='service_code')
        summary_avg_df['year'] = year
        summary_list.append(summary_avg_df)

    # 데이터프레임으로 합치기
    gender_df = pd.concat(gender_list).reset_index(drop=True)
    age_df = pd.concat(age_list).reset_index(drop=True)
    summary_df = pd.concat(summary_list).reset_index(drop=True)

    # 컬럼명 정리
    gender_df.rename(columns={
        'region_name': '행정동명',
        'service_name': '업종명',
        'service_code': '업종코드',
        'gender': '성별',
        'avg_sales_per_store': '성별별 평균 월 매출'
    }, inplace=True)

    age_df.rename(columns={
        'region_name': '행정동명',
        'service_name': '업종명',
        'service_code': '업종코드',
        'age_group': '연령대',
        'avg_sales_per_store': '연령대별 평균 월 매출'
    }, inplace=True)

    summary_df.rename(columns={
        'region_name': '행정동명',
        'service_name': '업종명',
        'service_code': '업종코드',
        'avg_sales_per_store': '평균 월 매출'
    }, inplace=True)

    gender_df.to_json('gender_avg_sales_industry.json', orient='records', force_ascii=False, indent=4)
    age_df.to_json('age_avg_sales_industry.json', orient='records', force_ascii=False, indent=4)
    summary_df.to_json('summary_avg_sales_industry.json', orient='records', force_ascii=False, indent=4)

    # JSON 문자열 변수에 저장
    gender_industry_json = gender_df.to_json(orient='records', force_ascii=False, indent=4)
    age_industry_json = age_df.to_json(orient='records', force_ascii=False, indent=4)
    summary_industry_json = summary_df.to_json(orient='records', force_ascii=False, indent=4)

    # ------------------------
    # 정규화 대상 컬럼 정의
    # ------------------------
    score_columns = [
        '평균영업기간(년)', '점포수',
        '1년 생존율(%)', '3년 생존율(%)', '5년 생존율(%)',
        '평균 개업수', '평균 폐업수'
    ]
    score_columns_2 = ['2022_평균매출', '2023_평균매출', '2024_평균매출']

    # ------------------------
    # 가중치 정의 (수정 가능)
    # ------------------------
    weights = {
        '평균영업기간(년)': 0.05,
        '점포수': 0.15,
        '1년 생존율(%)': 0.05,
        '3년 생존율(%)': 0.07,
        '5년 생존율(%)': 0.10,
        '평균 개업수': 0.04,
        '평균 폐업수': -0.04,
        '2022_평균매출': 0.15,
        '2023_평균매출': 0.17,
        '2024_평균매출': 0.22
    }

    # ------------------------
    # 정규화 수행
    # ------------------------
    # summary_df에서 연도별 평균 매출 피벗 (업종/행정동 기준으로 wide format 만들기)
    pivot_summary = summary_df.pivot_table(
        index=['행정동명', '업종명'],
        columns='year',
        values='평균 월 매출',
        aggfunc='mean'
    ).reset_index()

    # 컬럼명 정리 (2022, 2023, 2024 → '2022_평균매출' 형태로)
    pivot_summary.columns.name = None
    pivot_summary.rename(columns={
        2022: '2022_평균매출',
        2023: '2023_평균매출',
        2024: '2024_평균매출'
    }, inplace=True)

    # merged_df에 평균 매출 병합
    merged_df = merged_df.merge(pivot_summary, on=['업종명','행정동명'], how='left')
    merged_df.to_json('merged_industry.json', orient='records', force_ascii=False, indent=4)

    # JSON 문자열 변수에 저장
    merged_industry_json = merged_df.to_json(orient='records', force_ascii=False, indent=4)

    # 정규화 대상 컬럼
    all_score_columns = score_columns + score_columns_2

    # 정규화 수행
    clean_df = merged_df[all_score_columns].replace([np.inf, -np.inf], np.nan).fillna(0)

    scaler = MinMaxScaler()
    normalized = scaler.fit_transform(clean_df)
    normalized_df = pd.DataFrame(normalized, columns=[f'norm_{col}' for col in all_score_columns])
    # 병합
    merged_with_norm = pd.concat([merged_df, normalized_df], axis=1)

    # 점수 계산
    merged_with_norm['업종_추천점수'] = sum(
        merged_with_norm[f'norm_{col}'] * weight
        for col, weight in weights.items()
    )

    # 불필요한 정규화 컬럼 제거, 정렬
    norm_cols = [f'norm_{col}' for col in all_score_columns]
    final_result = merged_with_norm.drop(columns=norm_cols).sort_values(by='업종_추천점수', ascending=False).reset_index(drop=True)
    final_result = final_result.replace([np.inf, -np.inf], np.nan)
    final_result = final_result.dropna(subset=['2022_평균매출', '2023_평균매출', '2024_평균매출'])

    # 저장
    final_result.to_csv('filtered_result_industry.csv', index=False, encoding='utf-8-sig')
    final_result.to_json('filtered_result_industry.json', orient='records', force_ascii=False, indent=4)
    filtered_result_industry_json = final_result.to_json(orient='records', force_ascii=False, indent=4)

    # 출력
    print("🏆 최종 업종 추천 결과 (지역+업종 기준)")
    print(final_result[['행정동명', '업종명', '업종_추천점수']].head(10))

    #----LLM----
    # API 키 설정
    genai.configure(api_key="AIzaSyCiEbjep2f6PRLqTr1JKYE2vMlbrAHvr-E")

    # 모델 선택
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    def generate_business_summary(row, target_dong):
        업종명 = row['업종명']
        행정동명 = row['행정동명']

        few_shot_examples ="""
    [예시 1]
    - 업종명: 커피 전문점
    - 평균영업기간: 4.2년
    - 점포수: 180개
    - 3년 생존율: 72%
    - 5년 생존율: 55%
    - 평균 개업수: 14개
    - 평균 폐업수: 8개
    - 2022 평균 월매출: 8,400,000원
    - 2023 평균 월매출: 8,800,000원
    - 2024 평균 월매출: 9,200,000원

    꾸준한 매출 상승과 높은 생존율이 돋보이며, 창업에 안정적인 업종으로 평가됩니다.

    [예시 2]
    - 업종명: 분식 전문점
    - 평균영업기간: 3.6년
    - 점포수: 90개
    - 3년 생존율: 69%
    - 5년 생존율: 51%
    - 평균 개업수: 12개
    - 평균 폐업수: 6개
    - 2022 평균 월매출: 6,100,000원
    - 2023 평균 월매출: 6,400,000원
    - 2024 평균 월매출: 6,900,000원

    매출이 지속적으로 증가하고 있으며, 비교적 낮은 폐업률로 안정적인 창업이 가능합니다.
    """

        # 프롬프트 완성
        prompt = f"""
    당신은 업종 추천 전문가입니다.
    아래는 '{target_dong}' 지역에서 '{업종명}' 업종을 '{행정동명}' 내에 창업했을 때의 주요 지표입니다:

    먼저 참고용 예시를 확인하세요:
    {few_shot_examples}

    ---

    이제 아래 지표를 바탕으로 업종 추천 사유를 긍정적으로 **3줄 이내로 작성**해 주세요:


    - 평균영업기간: {row['평균영업기간(년)']}년
    - 점포수: {row['점포수']}개
    - 3년 생존율: {row['3년 생존율(%)']}%
    - 5년 생존율: {row['5년 생존율(%)']}%
    - 평균 개업수: {row['평균 개업수']}개
    - 평균 폐업수: {row['평균 폐업수']}개
    - 2022 평균 월매출: {int(row['2022_평균매출']):,}원
    - 2023 평균 월매출: {int(row['2023_평균매출']):,}원
    - 2024 평균 월매출: {int(row['2024_평균매출']):,}원

    """
        response = model.generate_content(prompt)
        return response.text.strip()

    # ----추천 결과 생성----
    recommendation_list = []

    subcategory_df = pd.read_sql("SELECT DISTINCT category_large, category_small FROM subcategory_store_count_stats", engine)

    # 상위 5개만 추출
    top_n = 5

    for idx, row in final_result.head(top_n).iterrows():
        label = row['업종명']

        # 대분류(category_large) 찾기
        match_row = subcategory_df[subcategory_df['category_small'] == label]
        if not match_row.empty:
            large_label = match_row.iloc[0]['category_large']
        else:
            large_label = '기타'  # 혹은 None 등 기본값 설정

        reason = generate_business_summary(row, target_dong)
        recommendation_list.append({
            'category_large': large_label,
            'category_small': label,
            'reason': reason
        })

    # ----JSON 저장----
    recommendation_dict = {
        target_dong: recommendation_list
    }

    # JSON 파일로 저장
    with open('recommendation_industry.json', 'w', encoding='utf-8') as f:
        json.dump(recommendation_dict, f, ensure_ascii=False, indent=4)

    # JSON 문자열로 변수에 저장
    recommendation_industry_json = json.dumps(recommendation_dict, ensure_ascii=False, indent=4)

    # 출력
    print(recommendation_industry_json)
