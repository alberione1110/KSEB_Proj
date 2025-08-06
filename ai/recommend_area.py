import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.preprocessing import MinMaxScaler
import google.generativeai as genai
import pymysql
import json

def get_recommendation(gu_name, category_small) :
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

    # 공통 함수: 최근 N개 분기 데이터 가져오기 (region_code, year, quarter 필드 기준)
    def get_recent_rows(df, group_col='region_code', num_quarters=4):
        df_sorted = df.sort_values(by=[group_col, 'year', 'quarter'])
        return df_sorted.groupby(group_col, group_keys=False).tail(num_quarters)

    # get_same_quarter_rows 함수는 필요하면 추가 가능

    # 4. 구 코드(지역 코드) 조회 (floating_population_stats 테이블 사용 예시)
    sql_gu_code = f"""
        SELECT DISTINCT region_code
        FROM floating_population_stats
        WHERE region_name = '{gu_name}'
        LIMIT 1
    """

    gu_code_df = pd.read_sql(sql_gu_code, engine)
    gu_code = str(gu_code_df.iloc[0]['region_code'])
    print(f"선택한 구 '{gu_name}'의 지역 코드: {gu_code}")
    print(f"선택한 업종: {category_small}")

    # 5. 각 테이블별 데이터 조회 쿼리 함수
    def query_table(table_name, extra_condition="", category_col='category_small', indicator_col='indicator', indicator_val=None):
        # 기본 조건: region_code가 구 코드로 시작
        condition = f"region_code LIKE '{gu_code}%%'"

        # 업종 필터링 조건 추가
        if category_small and category_col:
            condition += f" AND {category_col} = '{category_small}'"
        
        # indicator 필터링 조건 추가
        if indicator_val and indicator_col:
            condition += f" AND {indicator_col} = '{indicator_val}'"
        
        # 기타 조건이 있으면 추가
        if extra_condition:
            condition += f" AND {extra_condition}"
        
        sql = f"""
            SELECT *
            FROM {table_name}
            WHERE {condition}
            ORDER BY region_code, year, quarter
        """
        df = pd.read_sql(sql, engine)
        return df

    def load_table(table_name):
        try:
            return pd.read_sql(f"SELECT * FROM {table_name}", engine)
        except Exception as e:
            print(f"❌ [ERROR] 테이블 {table_name} 로딩 실패:", e)
            # 롤백 강제 실행
            engine.dispose()  # 현재 연결 완전히 초기화
            raise e

    def query_sales(table):
        df = pd.read_sql(f"SELECT * FROM {table}", engine)
        df = df[['year','quarter','zone_id','zone_name','region_name','service_code','service_name','monthly_sales']]
        df['zone_id'] = df['zone_id'].astype(str)

        rent_test_df = rent_df[['region_name','region_code']].drop_duplicates(subset=['region_name', 'region_code'])
        df = df.merge(rent_test_df[['region_name', 'region_code']], on='region_name', how='left')
        df = df[df['region_code'].notna()]
        df = df[df['service_name'] == category_small]
        return df
        

    def add_region_service_names(df, zone_df, service_df, rent_df):

        # zone_df 기준 행정동 이름 붙이기
        df['zone_id'] = df['zone_id'].astype(str)
        zone_df['zone_id'] = zone_df['zone_id'].astype(str)
        print("타입확인",zone_df['zone_id'].dtype)
        df = df.merge(zone_df[['zone_id', 'region_name']], on='zone_id', how='left')
        rent_test_df = rent_df[['region_name','region_code']].drop_duplicates(subset=['region_name', 'region_code'])
        df = df.merge(rent_test_df[['region_name', 'region_code']], on='region_name', how='left')
        df = df[df['region_code'].notna()]
        df = df.merge(service_df[['service_code', 'service_name']], on='service_code', how='left')
        df = df[df['service_name'] == category_small+'\r']
        return df



    # 6. 각 데이터 조회
    pop_df = query_table('floating_population_stats', category_col=None)  # 유동인구 테이블에는 업종 없음 가정
    rent_df = query_table('rental_price_stats', category_col=None)
    age_df = query_table('subcategory_avg_operating_period_stats', indicator_val='avg_operating_years_30')
    store_df = query_table('subcategory_store_count_stats', indicator_val='store_total')
    survive_df = query_table('subcategory_startup_survival')
    openclose_df = query_table('subcategory_openclose_stats')

    # 기본 테이블 불러오기
    zone_df = load_table('zone_table')
    zone_df['zone_id']= zone_df['zone_id'].astype(str)
    service_df = load_table('service_type')


    # 7. 최근 4개 분기 필터링
    pop_filtered = get_recent_rows(pop_df)[["region_name", "region_code", "year", "quarter", "floating_population"]]
    rent_filtered = get_recent_rows(rent_df)[["region_name", "region_code", "year", "quarter", "rent_total"]]

    age_filtered = get_recent_rows(age_df)[["category_small", "region_name", "region_code", "year", "quarter", "indicator", "value"]]
    store_filtered = get_recent_rows(store_df)[["category_small", "region_name", "region_code", "year", "quarter", "indicator", "value"]]

    survive_filtered = get_recent_rows(survive_df)[["category_small", "region_name", "region_code", "year", "quarter",
                                   "survival_1yr", "survival_3yr", "survival_5yr"]]
    openclose_filtered = openclose_df[["category_small", "region_name", "region_code", "year", "quarter",
                                       "num_open", "num_close"]]

    years = [2022, 2023, 2024]
    gender_sales = {}
    gender_sales_test ={}
    age_sales = {}
    summary_sales = {}
    # 매출 관련 데이터 처리
    for year in years:
        st_ct_df = load_table(f"zone_store_count_{year}") #zone 업종당 점포수
        gender_df = load_table(f"sales_by_gender_age_{year}")
        gender_known = gender_df[gender_df['gender'].isin(['여성', '남성'])]
        gender_unknown = gender_df[~gender_df['gender'].isin(['여성', '남성'])]

        gender_known = add_region_service_names(gender_known, zone_df, service_df, rent_df)
        gender_unknown = add_region_service_names(gender_unknown, zone_df, service_df, rent_df)
        
        #--gender
        gender_sales[year] = gender_known[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "gender", "sales_amount"]] \
            .sort_values(by=["service_name", "gender", "year", "quarter"]).reset_index(drop=True)

        gender_sales[year] = gender_sales[year].merge(st_ct_df[['zone_id', 'service_code', 'year', 'quarter','count']],on=['zone_id', 'service_code', 'year', 'quarter'],how='inner')
        gender_sales[year].loc[:, 'avg_sales_per_store'] = gender_sales[year]['sales_amount'] / gender_sales[year]['count']

        gender_sales[year] = gender_sales[year][["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "gender", "avg_sales_per_store","count"]] \
            .sort_values(by=['region_name', 'year', 'quarter','gender']).reset_index(drop=True)
        # 정렬 기준: region_name > year > quarter
        
        #--age
        age_sales[year] = gender_unknown[["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "age_group", "sales_amount"]] \
            .sort_values(by=["service_name", "age_group", "year", "quarter"]).reset_index(drop=True)
        
        age_sales[year] = age_sales[year].merge(st_ct_df[['zone_id', 'service_code', 'year', 'quarter','count']],on=['zone_id', 'service_code', 'year', 'quarter'],how='inner')
        age_sales[year].loc[:, 'avg_sales_per_store'] = age_sales[year]['sales_amount'] / age_sales[year]['count']

        age_sales[year] = age_sales[year][["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "age_group", "avg_sales_per_store","count"]] \
            .sort_values(by=['region_name', 'year', 'quarter','age_group']).reset_index(drop=True)
        
        #--summary
        sales_df = query_sales(f"sales_summary_{year}")
        summary_sales[year] = sales_df[["region_name", "service_name", "zone_id", "service_code", "year", "quarter", "monthly_sales"]]
        summary_sales[year].loc[:, 'zone_id'] = summary_sales[year]['zone_id'].astype(str)

        summary_sales[year] = summary_sales[year].merge(st_ct_df[['zone_id', 'service_code', 'year', 'quarter','count']],on=['zone_id', 'service_code', 'year', 'quarter'],how='inner')
        summary_sales[year].loc[:, 'avg_sales_per_store'] = summary_sales[year]['monthly_sales'] / summary_sales[year]['count']

        summary_sales[year] = summary_sales[year][["region_name", "zone_id", "service_name", "service_code", "year", "quarter", "avg_sales_per_store","count"]] \
            .sort_values(by=['region_name', 'year', 'quarter']).reset_index(drop=True)
        
    for year in years:
        print(f"{year}",gender_sales[year])
        print(f"{year}",age_sales[year])
        print(f"{year}",summary_sales[year])

    # 평균값 계산 함수
    def get_avg(df, group_col='region_code', val_col=None, rename_col=None):
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
    pop_avg = get_avg(pop_filtered, val_col='floating_population', rename_col='유동인구')
    rent_avg = get_avg(rent_filtered, val_col='rent_total', rename_col='임대시세')
    age_avg = get_avg(age_filtered, val_col='value', rename_col='평균영업기간(년)')
    store_avg = get_avg(store_filtered, val_col='value', rename_col='점포수')

    survive_avg = survive_filtered.groupby('region_code').agg({
        'survival_1yr': 'mean',
        'survival_3yr': 'mean',
        'survival_5yr': 'mean',
        'region_name': 'first'
    }).round(2).reset_index().rename(columns={
        'survival_1yr': '1년 생존율(%)',
        'survival_3yr': '3년 생존율(%)',
        'survival_5yr': '5년 생존율(%)'
    })

    openclose_avg = openclose_filtered.groupby('region_code').agg({
        'num_open': 'mean',
        'num_close': 'mean',
        'region_name': 'first'
    }).round(2).reset_index().rename(columns={
        'num_open': '평균 개업수',
        'num_close': '평균 폐업수'
    })

    # 병합
    dfs = [pop_avg, rent_avg, age_avg, store_avg, survive_avg, openclose_avg]
    from functools import reduce
    merged_df = reduce(lambda left, right: pd.merge(left, right, on=['region_code', 'region_name']), dfs)

    # 컬럼 정리
    merged_df = merged_df.rename(columns={
        'region_code': '행정동코드',
        'region_name': '행정동명'
    }).sort_values(by='유동인구', ascending=False).reset_index(drop=True)

    # 출력
    pd.set_option('display.float_format', '{:,.2f}'.format)
    print("📊 종합 지역 상권 요약 리포트")
    print(merged_df)


    def get_avg_sales(sales_df, group_col):
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])
        
        avg_df = sales_df.groupby(['region_name', group_col]).agg({
            'avg_sales_per_store': 'mean',
            #'region_name': 'first',
            'service_name': 'first'
        }).round(2).reset_index()

        avg_df['avg_sales_per_store'] = (avg_df['avg_sales_per_store'] / 3).round(2)

        return avg_df

    def get_avg_sales_sum(sales_df, group_col=None):
        # 매출 데이터를 숫자로 변환, 결측치 제거
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])

        # 기본 그룹핑 컬럼: 업종 코드
        group_cols = ['region_name']
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

    gender_df.to_json('gender_avg_sales_dong.json', orient='records', force_ascii=False, indent=4)
    age_df.to_json('age_avg_sales_dong.json', orient='records', force_ascii=False, indent=4)
    summary_df.to_json('summary_avg_sales_dong.json', orient='records', force_ascii=False, indent=4)

    # JSON 문자열 변수에 저장
    gender_dong_json = gender_df.to_json(orient='records', force_ascii=False, indent=4)
    age_dong_json = age_df.to_json(orient='records', force_ascii=False, indent=4)
    summary_dong_json = summary_df.to_json(orient='records', force_ascii=False, indent=4)


    # ------------------------
    # 정규화 대상 컬럼 정의
    # ------------------------
    score_columns = [
        '유동인구', '임대시세', '평균영업기간(년)', '점포수',
        '1년 생존율(%)', '3년 생존율(%)', '5년 생존율(%)',
        '평균 개업수', '평균 폐업수'
    ]
    score_columns_2 = ['2022_평균매출', '2023_평균매출', '2024_평균매출']

    # ------------------------
    # 가중치 정의 (수정 가능)
    # ------------------------
    weights = {
        '유동인구': 0.1483,
        '임대시세': -0.0909,
        '평균영업기간(년)': 0.0574,
        '점포수': 0.2871,
        '1년 생존율(%)': 0.0574,
        '3년 생존율(%)': 0.0574,
        '5년 생존율(%)': 0.0574,
        '평균 개업수': 0.0287,
        '평균 폐업수': -0.0287,
        '2022_평균매출': 0.0718,
        '2023_평균매출': 0.1053,
        '2024_평균매출': 0.1053
    }

    ## ------------------------
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
    # 병합 전에 컬럼명 맞추기 (해당 없으면 생략 가능)
    merged_df = merged_df.merge(pivot_summary, on=['행정동명'], how='left')
    merged_df.to_json('merged_dong.json', orient='records', force_ascii=False, indent=4)

    # JSON 문자열 변수에 저장
    merged_dong_json = merged_df.to_json(orient='records', force_ascii=False, indent=4)

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
    merged_with_norm['행정동_추천점수'] = sum(
        merged_with_norm[f'norm_{col}'] * weight
        for col, weight in weights.items()
    )

    # ------------------------
    # 최종 결과 정렬 및 출력
    # ------------------------

    # 정규화된 컬럼 이름 정의
    norm_cols = [f'norm_{col}' for col in all_score_columns]

    # 지역 점수와 정규화 컬럼들을 함께 결합
    final_result = merged_with_norm.drop(columns=norm_cols).sort_values(by='행정동_추천점수', ascending=False).reset_index(drop=True)
    final_result = final_result[final_result['행정동코드'].astype(str).str.len() != 5]
    final_result = final_result.drop(columns='업종명')
    # 결측 또는 무한대 포함된 행정동 제외
    final_result = final_result.replace([np.inf, -np.inf], np.nan)
    final_result = final_result.dropna(subset=['2022_평균매출', '2023_평균매출', '2024_평균매출'])

    # 저장
    final_result.to_csv('filtered_result_dong.csv', index=False, encoding='utf-8-sig')
    final_result.to_json('filtered_result_dong.json', orient='records', force_ascii=False, indent=4)
    filtered_result_dong_json = final_result.to_json(orient='records', force_ascii=False, indent=4)


    # 결과 확인
    print("🏆 최종 추천 행정동 (원본 지표 + 지역 점수 포함)")
    print("추천 행정동\n",final_result)
    print("행정동명 및 점수\n",final_result[['행정동명','행정동_추천점수']].head(10))

    #----LLM----
    # API 키 설정
    genai.configure(api_key="AIzaSyCiEbjep2f6PRLqTr1JKYE2vMlbrAHvr-E")

    # 모델 선택
    model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")
    def generate_region_summary(row, gu_name, category_small):
        few_shot_examples = """
    [예시 1]
    - 행정동명: 서교동
    - 유동인구: 25,000명
    - 임대시세: 3,200,000원/평
    - 평균영업기간: 4.2년
    - 점포수: 180개
    - 3년 생존율: 72%
    - 5년 생존율: 55%
    - 평균 개업수: 14개
    - 평균 폐업수: 8개
    - 2022 평균 월매출: 8,400,000원
    - 2023 평균 월매출: 8,800,000원
    - 2024 평균 월매출: 9,200,000원

    서교동은 높은 유동인구와 지속적으로 상승하는 평균 매출 흐름이 특징입니다. 또한 점포 수가 많고 생존율도 우수해 커피 전문점 창업에 안정적인 조건을 갖춘 상권입니다.

    [예시 2]
    - 행정동명: 행당동
    - 유동인구: 15,000명
    - 임대시세: 2,100,000원/평
    - 평균영업기간: 3.6년
    - 점포수: 110개
    - 3년 생존율: 69%
    - 5년 생존율: 50%
    - 평균 개업수: 10개
    - 평균 폐업수: 6개
    - 2022 평균 월매출: 6,400,000원
    - 2023 평균 월매출: 2,800,000원
    - 2024 평균 월매출: 7,100,000원

    행당동은 임대시세가 낮은 편이면서도 매출 흐름이 안정적이고, 생존율도 평균 이상입니다. 예산이 제한적인 초기 창업자에게 특히 유리한 입지입니다.
    """

        # 프롬프트 완성
        prompt = f"""
    당신은 상권 분석 전문가입니다.
    아래는 '{gu_name}' 지역 '{category_small}' 업종의 특정 행정동 핵심 상권 지표입니다:

    먼저 참고용 예시를 확인하세요:
    {few_shot_examples}

    ---

    이제 아래 지표를 바탕으로 지역의 추천 사유를 긍정적으로 **3줄 이내로 작성**해 주세요:

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


    """
        response = model.generate_content(prompt)
        return response.text.strip()

    recommendation_list = []

    # 상위 5개 행정동
    top_n = 5

    for idx, row in final_result.head(top_n).iterrows():
        full_district_name = f"{gu_name} {row['행정동명']}"
        reason = generate_region_summary(row, gu_name, category_small)

        recommendation_list.append({
            'district': full_district_name,
            'reason': reason
        })

    recommendation_dict = {
        category_small: recommendation_list
    }

    # JSON 파일로 저장
    with open('recommendation_dong.json', 'w', encoding='utf-8') as f:
        json.dump(recommendation_dict, f, ensure_ascii=False, indent=4)

    # JSON 문자열로 변수에 저장
    recommendation_dong_json = json.dumps(recommendation_dict, ensure_ascii=False, indent=4)

    # 출력
    print(recommendation_dong_json)

