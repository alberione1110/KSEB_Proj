# import pandas as pd
# import numpy as np
# import json
# from sqlalchemy import create_engine
# from functools import reduce
# from sklearn.preprocessing import MinMaxScaler
# import google.generativeai as genai

# def get_recommendation(gu_name, region):
#     target_gu = gu_name
#     target_dong = region

#     # MySQL 접속 정보 (수정 필요)
#     user = 'root'
#     password = '1234'
#     host = 'localhost'
#     port = 3306
#     database = 'self_employed_data'

#     engine = create_engine(
#         f'mysql+pymysql://{user}:{password}@{host}:{port}/{database}',
#         connect_args={'charset':'utf8mb4'}
#     )

#     def get_recent_quarters_by_category(df, group_cols=['category_small'], num_quarters=4):
#         df_sorted = df.sort_values(by=group_cols + ['year', 'quarter'])
#         return df_sorted.groupby(group_cols, group_keys=False).tail(num_quarters)

#     def load_table(table_name):
#         return pd.read_sql(f"SELECT * FROM {table_name}", engine)

#     def query_table(table_name, extra_condition="", category_col=None, indicator_col='indicator', indicator_val=None):
#         use_region_code = 'region_code' in pd.read_sql(f"SHOW COLUMNS FROM {table_name}", engine)['Field'].values
#         conditions = []

#         if use_region_code:
#             conditions.append(f"region_code LIKE '{dong_code}%%'")
#         elif target_dong and category_col:
#             conditions.append(f"{category_col} = '{target_dong}'")
#         if indicator_val and indicator_col:
#             conditions.append(f"{indicator_col} = '{indicator_val}'")
#         if extra_condition:
#             conditions.append(extra_condition)

#         where_clause = " AND ".join(conditions) if conditions else "1=1"
#         sql = f"SELECT * FROM {table_name} WHERE {where_clause} ORDER BY year, quarter"
#         return pd.read_sql(sql, engine)

#     def query_sales(table, service_code=None):
#         cond = f"region_name = '{target_dong}'"
#         if service_code:
#             cond += f" AND service_code = '{service_code}'"
#         sql = f"SELECT * FROM {table} WHERE {cond} ORDER BY service_code, zone_id, year, quarter"
#         df = pd.read_sql(sql, engine)
#         return df.drop_duplicates(subset=["region_name", "year", "quarter", "service_code", "monthly_sales"])

#     def add_region_service_names(df, zone_df, service_df, target_dong=None):
#         df = df.merge(zone_df, on='zone_id', how='left')
#         df = df.merge(service_df, on='service_code', how='left')
#         if target_dong:
#             df = df[df['region_name'] == target_dong]
#         return df

#     dong_query = f"SELECT DISTINCT region_code FROM subcategory_avg_operating_period_stats WHERE region_name = '{target_dong}' LIMIT 1"
#     dong_code = pd.read_sql(dong_query, engine).iloc[0]['region_code']

#     zone_df = load_table('zone_table')
#     service_df = load_table('service_type')

#     indicators = {
#         'age': ('subcategory_avg_operating_period_stats', 'avg_operating_years_30'),
#         'store': ('subcategory_store_count_stats', 'store_total'),
#         'survive': ('subcategory_startup_survival', None),
#         'openclose': ('subcategory_openclose_stats', None)
#     }
#     filtered_data = {}
#     for key, (table, indicator) in indicators.items():
#         df = query_table(table, indicator_val=indicator)
#         if key in ['age', 'store']:
#             filtered_data[key] = get_recent_quarters_by_category(df)[["category_small", "region_name", "region_code", "year", "quarter", "indicator", "value"]]
#         elif key == 'survive':
#             filtered_data[key] = get_recent_quarters_by_category(df)[["category_small", "region_name", "region_code", "year", "quarter",
#                                                                       "survival_1yr", "survival_3yr", "survival_5yr"]]
#         else:
#             filtered_data[key] = df[["category_small", "region_name", "region_code", "year", "quarter",
#                                      "num_open", "num_close"]]

#     years = [2022, 2023, 2024]
#     gender_sales = {}
#     age_sales = {}
#     summary_sales = {}

#     for year in years:
#         st_ct_df = load_table(f"zone_store_count_{year}")
#         gender_df = load_table(f"sales_by_gender_age_{year}")
#         gender_known = gender_df[gender_df['gender'].isin(['여성', '남성'])]
#         gender_unknown = gender_df[~gender_df['gender'].isin(['여성', '남성'])]

#         gender_known = add_region_service_names(gender_known, zone_df, service_df, target_dong)
#         gender_unknown = add_region_service_names(gender_unknown, zone_df, service_df, target_dong)

#         gender_sales[year] = gender_known.merge(st_ct_df, on=['zone_id', 'service_code', 'year', 'quarter'])
#         gender_sales[year]['avg_sales_per_store'] = gender_sales[year]['sales_amount'] / gender_sales[year]['count']

#         age_sales[year] = gender_unknown.merge(st_ct_df, on=['zone_id', 'service_code', 'year', 'quarter'])
#         age_sales[year]['avg_sales_per_store'] = age_sales[year]['sales_amount'] / age_sales[year]['count']

#         sales_df = query_sales(f"sales_summary_{year}")
#         summary_sales[year] = sales_df.merge(st_ct_df, on=['zone_id', 'service_code', 'year', 'quarter'])
#         summary_sales[year]['avg_sales_per_store'] = summary_sales[year]['monthly_sales'] / summary_sales[year]['count']

#     def get_avg(df, group_col='category_small', val_col=None, rename_col=None):
#         df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
#         df = df.dropna(subset=[val_col])
#         avg = df.groupby(group_col).agg({val_col: 'mean', 'region_name': 'first'}).round(2).reset_index()
#         if rename_col:
#             avg = avg.rename(columns={val_col: rename_col})
#         return avg

#     age_avg = get_avg(filtered_data['age'], val_col='value', rename_col='평균영업기간(년)')
#     store_avg = get_avg(filtered_data['store'], val_col='value', rename_col='점포수')

#     survive_avg = filtered_data['survive'].groupby('category_small').agg({
#         'survival_1yr': 'mean', 'survival_3yr': 'mean', 'survival_5yr': 'mean', 'region_name': 'first'
#     }).round(2).reset_index().rename(columns={
#         'survival_1yr': '1년 생존율(%)', 'survival_3yr': '3년 생존율(%)', 'survival_5yr': '5년 생존율(%)'
#     })

#     openclose_avg = filtered_data['openclose'].groupby('category_small').agg({
#         'num_open': 'mean', 'num_close': 'mean', 'region_name': 'first'
#     }).round(2).reset_index().rename(columns={
#         'num_open': '평균 개업수', 'num_close': '평균 폐업수'
#     })

#     dfs = [age_avg, store_avg, survive_avg, openclose_avg]
#     merged_df = reduce(lambda left, right: pd.merge(left, right, on=['category_small', 'region_name']), dfs)
#     merged_df = merged_df.rename(columns={'category_small': '업종명', 'region_name': '행정동명'})

#     def get_avg_sales_sum(sales_df):
#         sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
#         sales_df = sales_df.dropna(subset=['avg_sales_per_store'])
#         avg_df = sales_df.groupby('service_code').agg({
#             'avg_sales_per_store': 'mean', 'region_name': 'first', 'service_name': 'first'
#         })
#         avg_df['avg_sales_per_store'] = (avg_df['avg_sales_per_store'] / 3).round(2)
#         return avg_df.reset_index()

#     summary_list = []
#     for year in years:
#         summary_avg_df = get_avg_sales_sum(summary_sales[year])
#         summary_avg_df['year'] = year
#         summary_list.append(summary_avg_df)
#     summary_df = pd.concat(summary_list).reset_index(drop=True)

#     pivot_summary = summary_df.pivot_table(
#         index=['region_name', 'service_name'],
#         columns='year', values='avg_sales_per_store', aggfunc='mean'
#     ).reset_index()
#     pivot_summary.columns.name = None
#     pivot_summary.rename(columns={2022: '2022_평균매출', 2023: '2023_평균매출', 2024: '2024_평균매출'}, inplace=True)
#     merged_df = merged_df.merge(pivot_summary, left_on=['행정동명', '업종명'], right_on=['region_name', 'service_name'], how='left')

#     score_columns = ['평균영업기간(년)', '점포수', '1년 생존율(%)', '3년 생존율(%)', '5년 생존율(%)', '평균 개업수', '평균 폐업수']
#     score_columns_2 = ['2022_평균매출', '2023_평균매출', '2024_평균매출']
#     weights = {'평균영업기간(년)': 0.05, '점포수': 0.15, '1년 생존율(%)': 0.05, '3년 생존율(%)': 0.07, '5년 생존율(%)': 0.10,
#                '평균 개업수': 0.04, '평균 폐업수': -0.04, '2022_평균매출': 0.15, '2023_평균매출': 0.17, '2024_평균매출': 0.22}

#     all_score_columns = score_columns + score_columns_2
#     clean_df = merged_df[all_score_columns].replace([np.inf, -np.inf], np.nan).fillna(0)
#     scaler = MinMaxScaler()
#     normalized = scaler.fit_transform(clean_df)
#     normalized_df = pd.DataFrame(normalized, columns=[f'norm_{col}' for col in all_score_columns])
#     merged_with_norm = pd.concat([merged_df, normalized_df], axis=1)
#     merged_with_norm['업종_추천점수'] = sum(
#         merged_with_norm[f'norm_{col}'] * weight for col, weight in weights.items())

#     final_result = merged_with_norm.sort_values(by='업종_추천점수', ascending=False).reset_index(drop=True)

#     genai.configure(api_key="YOUR_GOOGLE_GENAI_API_KEY")  # Replace with your actual key
#     model = genai.GenerativeModel(model_name="models/gemini-2.5-flash")

#     def generate_business_summary(row, idx):
#         업종명 = row['업종명']
#         행정동명 = row['행정동명']
#         template = f"'{업종명}' 업종은 추천 순위 {idx+1}위입니다. 주요 지표: 점포수={row['점포수']}, 3년 생존율={row['3년 생존율(%)']}%, 2024년 평균 매출={row['2024_평균매출']}. 이유를 2문장으로 요약해 주세요."
#         prompt = f"{template}"
#         response = model.generate_content(prompt)
#         return response.text.strip()

#     recommendation_list = []
#     subcategory_df = pd.read_sql("SELECT DISTINCT category_large, category_small FROM subcategory_store_count_stats", engine)
#     for idx, row in final_result.iterrows():
#         if idx > 5:
#             break
#         label = row['업종명']
#         match_row = subcategory_df[subcategory_df['category_small'] == label]
#         large_label = match_row.iloc[0]['category_large'] if not match_row.empty else '기타'
#         reason = generate_business_summary(row, idx)
#         recommendation_list.append({
#             'category_large': large_label,
#             'category_small': label,
#             'reason': reason
#         })

#     return recommendation_list


# ai/recommend_industry.py

def get_recommendation(gu_name, region):
    """
    더미 데이터를 반환하는 테스트용 업종 추천 함수
    """
    return [
        {
            'category_large': '외식업',
            'category_small': '분식',
            'reason': f'{region}은 유동 인구가 많고, 간편식 수요가 높아 분식 업종이 유리합니다.'
        },
        {
            'category_large': '서비스업',
            'category_small': '미용실',
            'reason': f'{region}은 20~40대 여성이 밀집한 지역으로 미용 서비스 수요가 풍부합니다.'
        },
        {
            'category_large': '교육업',
            'category_small': '어학원',
            'reason': f'{region}에는 학생과 직장인이 많아 어학 수요가 존재합니다.'
        }
    ]
