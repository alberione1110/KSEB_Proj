# ai/recommend_industry.py
import os
import time
import json
import difflib
import numpy as np
import pandas as pd
from sqlalchemy import text
from sklearn.preprocessing import MinMaxScaler

# DB/엔진은 환경변수에서 안전하게 로드
from config.settings import get_engine

# 선택: LLM
try:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted, GoogleAPIError
except Exception:
    genai = None
    ResourceExhausted = GoogleAPIError = Exception

# ====== 환경설정 ======
USE_LLM = os.getenv("USE_LLM", "1") == "1"
TOPK_FOR_REASON = int(os.getenv("TOPK_FOR_REASON", "5"))
REASON_CACHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "reason_cache.json"))

# ====== LLM (Gemini) 로딩 (있으면 사용, 없으면 폴백) ======
_genai_available = False
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if USE_LLM and genai and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _genai_available = True
    except Exception:
        _genai_available = False

def _genai_model(model_name: str):
    if not _genai_available:
        return None
    try:
        # google-generativeai는 model_name 키워드 사용
        return genai.GenerativeModel(model_name=model_name)
    except Exception:
        return None

# ====== 간단 파일 캐시 ======
def _load_reason_cache():
    if os.path.exists(REASON_CACHE_PATH):
        try:
            with open(REASON_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_reason_cache(cache):
    os.makedirs(os.path.dirname(REASON_CACHE_PATH), exist_ok=True)
    with open(REASON_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

_REASON_CACHE = _load_reason_cache()

def _cache_key(gu_name, region, cat_small, date_key):
    return f"{gu_name}::{region}::{cat_small}::{date_key}"

# ====== 규칙 기반 이유 (LLM 폴백용) ======
def rule_based_reason(row):
    def _num(x, d=0):
        try:
            return round(float(x), d)
        except Exception:
            return 0
    def _int(x):
        try:
            return int(float(x))
        except Exception:
            return 0

    parts = []
    parts.append(f"{row.get('업종명','해당 업종')} 업종은 점포수 {_int(row.get('점포수',0))}개 수준입니다.")
    gy = _num(row.get('평균영업기간(년)', 0), 2)
    if gy > 0:
        parts.append(f"평균 영업기간이 약 {gy}년으로 안정성이 있습니다.")
    for y in (2024, 2023, 2022):
        col = f"{y}_평균매출"
        val = _num(row.get(col, 0), 0)
        if val > 0:
            parts.append(f"{y}년 평균 매출이 양호합니다.")
            break
    s3 = _num(row.get('3년 생존율(%)', 0), 1)
    if s3 > 0:
        parts.append(f"3년 생존율 {s3}% 수준입니다.")
    if not parts:
        return "지역 수요와 경쟁 상황을 고려할 때 잠재력이 있는 업종으로 판단됩니다."
    return " ".join(parts)

# ====== LLM 이유 생성 (429/오류 → 폴백/캐시) ======
def generate_reason_with_llm(gu_name, region, row, prefer_model="models/gemini-1.5-flash"):
    date_key = time.strftime("%Y-%m-%d")
    key = _cache_key(gu_name, region, row.get('업종명', ''), date_key)
    if key in _REASON_CACHE:
        return _REASON_CACHE[key], "cache"

    if not _genai_available:
        r = rule_based_reason(row)
        _REASON_CACHE[key] = r; _save_reason_cache(_REASON_CACHE)
        return r, "fallback-disabled"

    prompt = f"""
당신은 상권 분석 컨설턴트입니다. 아래 지표를 바탕으로 업종 추천 사유를 2~3문장으로 간결하게 써주세요.
- 행정동: {region} ({gu_name})
- 업종명: {row.get('업종명')}
- 점포수: {row.get('점포수')}
- 평균영업기간(년): {row.get('평균영업기간(년)')}
- 3년 생존율(%): {row.get('3년 생존율(%)')}
- 5년 생존율(%): {row.get('5년 생존율(%)')}
- 2022~2024 평균매출(가능한 연도만): {row.get('2022_평균매출','')}, {row.get('2023_평균매출','')}, {row.get('2024_평균매출','')}
가이드: 수치가 클수록 긍정적, 0 또는 결측은 언급하지 않아도 됨. 과장 표현 금지, 간단명료, 한국어.
"""

    models_try = [prefer_model, "models/gemini-1.5-flash-8b"]
    for m in models_try:
        try:
            model = _genai_model(m)
            if not model:
                raise RuntimeError("LLM not configured")
            resp = model.generate_content(prompt)
            text = (resp.text or "").strip()
            if not text:
                raise RuntimeError("Empty LLM response")
            _REASON_CACHE[key] = text; _save_reason_cache(_REASON_CACHE)
            return text, m
        except (ResourceExhausted, GoogleAPIError, Exception) as e:
            msg = str(e)
            if "429" in msg or isinstance(e, ResourceExhausted):
                time.sleep(1.5)
                try:
                    model = _genai_model(m)
                    if model:
                        resp = model.generate_content(prompt)
                        text = (resp.text or "").strip()
                        if text:
                            _REASON_CACHE[key] = text; _save_reason_cache(_REASON_CACHE)
                            return text, f"{m}-retry"
                except Exception:
                    pass
            continue

    r = rule_based_reason(row)
    _REASON_CACHE[key] = r; _save_reason_cache(_REASON_CACHE)
    return r, "fallback-429"

# ====== 핵심 추천 파이프라인 ======
def run_industry_recommendation(region, gu_name):
    """
    입력: region(행정동명), gu_name(구명)
    출력: back/cache/runtime/recommendation_industry.json 에 {region: [{category_large, category_small, reason}, ...]} 저장
    """
    engine = get_engine()

    # (선택) 연결 확인
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ DB 연결 확인")
    except Exception as e:
        print("❌ DB 연결 실패:", e)

    def load_table(table_name: str) -> pd.DataFrame:
        return pd.read_sql(f"SELECT * FROM {table_name}", engine)

    def load_or_cache(name, table):
        os.makedirs("cache", exist_ok=True)
        path = f"cache/{name}.feather"
        if os.path.exists(path):
            print(f"📂 캐시 불러옴: {name}")
            return pd.read_feather(path)
        df = load_table(table)
        df.to_feather(path)
        print(f"💾 캐시 저장: {name}")
        return df

    def get_recent_quarters_by_category(df, group_cols=['category_small'], num_quarters=4):
        if df.empty:
            return df
        df_sorted = df.sort_values(by=group_cols + ['year', 'quarter'])
        return df_sorted.groupby(group_cols, group_keys=False).tail(num_quarters)

    # region_code 조회 (파라미터 바인딩)
    dong_code_df = pd.read_sql(
        "SELECT DISTINCT region_code FROM subcategory_avg_operating_period_stats WHERE region_name = %s LIMIT 1",
        engine, params=(region,),
    )
    if dong_code_df.empty:
        raise ValueError(f"region_code을 찾을 수 없습니다: {region}")
    dong_code = dong_code_df.iloc[0]['region_code']
    print(f"선택한 동 '{region}'의 지역 코드: {dong_code}")

    # 지표 로드
    indicators = {
        'age': ('subcategory_avg_operating_period_stats', 'avg_operating_years_30'),
        'store': ('subcategory_store_count_stats', 'store_total'),
        'survive': ('subcategory_startup_survival', None),
        'openclose': ('subcategory_openclose_stats', None)
    }
    raw_data = {k: load_or_cache(f"{k}_all_df", t) for k, (t, _) in indicators.items()}

    def filter_by_region(df, region_name):
        return df[df['region_name'] == region_name].reset_index(drop=True)

    filtered_data = {}
    for key, (_, indicator) in indicators.items():
        df_region = filter_by_region(raw_data[key], region)
        if indicator and 'indicator' in df_region.columns:
            df_region = df_region[df_region['indicator'] == indicator]
        if key in ['age', 'store']:
            cols = ["category_small", "region_name", "region_code", "year", "quarter", "indicator", "value"]
            filtered_data[key] = get_recent_quarters_by_category(df_region)[cols] if not df_region.empty else df_region
        elif key == 'survive':
            cols = ["category_small", "region_name", "region_code", "year", "quarter",
                    "survival_1yr", "survival_3yr", "survival_5yr"]
            filtered_data[key] = get_recent_quarters_by_category(df_region)[cols] if not df_region.empty else df_region
        else:  # openclose
            cols = ["category_small", "region_name", "region_code", "year", "quarter", "num_open", "num_close"]
            filtered_data[key] = df_region[cols] if not df_region.empty else df_region

    # 평균 계산 유틸
    def get_avg(df, group_col='category_small', val_col=None, rename_col=None):
        if df.empty or (val_col not in df.columns):
            return pd.DataFrame(columns=[group_col, 'region_name', rename_col or val_col])
        df[val_col] = pd.to_numeric(df[val_col], errors='coerce')
        df = df.dropna(subset=[val_col])
        avg = df.groupby(group_col).agg({val_col: 'mean', 'region_name': 'first'}).round(2).reset_index()
        if rename_col:
            avg = avg.rename(columns={val_col: rename_col})
        return avg

    age_avg   = get_avg(filtered_data['age'],   val_col='value', rename_col='평균영업기간(년)')
    store_avg = get_avg(filtered_data['store'], val_col='value', rename_col='점포수')

    if not filtered_data['survive'].empty:
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
    else:
        survive_avg = pd.DataFrame(columns=['category_small','region_name','1년 생존율(%)','3년 생존율(%)','5년 생존율(%)'])

    if not filtered_data['openclose'].empty:
        openclose_avg = filtered_data['openclose'].groupby('category_small').agg({
            'num_open': 'mean',
            'num_close': 'mean',
            'region_name': 'first'
        }).round(2).reset_index().rename(columns={
            'num_open': '평균 개업수',
            'num_close': '평균 폐업수'
        })
    else:
        openclose_avg = pd.DataFrame(columns=['category_small','region_name','평균 개업수','평균 폐업수'])

    dfs = [age_avg, store_avg, survive_avg, openclose_avg]
    merged_df = dfs[0]
    for d in dfs[1:]:
        merged_df = pd.merge(merged_df, d, on=['category_small','region_name'], how='outer')

    merged_df = merged_df.rename(columns={'category_small':'업종명','region_name':'행정동명'})
    merged_df[['평균영업기간(년)','점포수','1년 생존율(%)','3년 생존율(%)','5년 생존율(%)','평균 개업수','평균 폐업수']] = \
        merged_df[['평균영업기간(년)','점포수','1년 생존율(%)','3년 생존율(%)','5년 생존율(%)','평균 개업수','평균 폐업수']].fillna(0)

    # === 매출 처리 ===
    def add_region_service_names(df, zone_df, service_df, region=None):
        if df.empty:
            return df
        df['zone_id'] = df['zone_id'].astype(str)
        zone_df['zone_id'] = zone_df['zone_id'].astype(str)
        df = df.merge(zone_df, on='zone_id', how='left', suffixes=('', '_zone'))
        df = df.merge(service_df, on='service_code', how='left', suffixes=('', '_service'))
        if 'region_name_zone' in df.columns:
            df['region_name'] = df['region_name_zone']; df.drop(columns=['region_name_zone'], inplace=True)
        elif 'region_name_service' in df.columns:
            df['region_name'] = df['region_name_service']; df.drop(columns=['region_name_service'], inplace=True)
        if region:
            df = df[df['region_name'] == region]
        # service_name 개행 정리
        if 'service_name' in df.columns:
            df['service_name'] = df['service_name'].astype(str).str.replace(r'[\r\n]+', '', regex=True)
        return df

    zone_df = load_table('zone_table')
    service_df = load_table('service_type')

    def load_year(table_prefix, year):
        return pd.read_sql(f"SELECT * FROM {table_prefix}_{year}", engine)

    def preprocess_sales(year, region, table_name, filter_cols, group_cols=None):
        df = load_year(table_name, year)
        st_ct_df = load_year("zone_store_count", year)
        df = add_region_service_names(df, zone_df, service_df, region)
        if df.empty:
            return df
        df = df[filter_cols]
        if group_cols is None:
            group_cols = []
        df = df.sort_values(by=group_cols + ['year','quarter']).reset_index(drop=True)
        df = df.merge(st_ct_df[['zone_id','service_code','year','quarter','count']],
                      on=['zone_id','service_code','year','quarter'], how='inner')
        # 컬럼 자동 탐색
        sales_col = [c for c in filter_cols if 'sales' in c or 'amount' in c][-1]
        df['avg_sales_per_store'] = df[sales_col] / df['count']
        return df[['region_name','zone_id','service_name','service_code','year','quarter','avg_sales_per_store','count']]

    years = [2022, 2023, 2024]
    summary_sales = {y: preprocess_sales(
        y, region,
        table_name='sales_summary',
        filter_cols=["region_name","zone_id","service_name","service_code","year","quarter","monthly_sales"],
        group_cols=["service_name"]
    ) for y in years}

    def get_avg_sales_sum(sales_df):
        if sales_df.empty:
            return pd.DataFrame(columns=['service_code','avg_sales_per_store','region_name','service_name'])
        sales_df['avg_sales_per_store'] = pd.to_numeric(sales_df['avg_sales_per_store'], errors='coerce')
        sales_df = sales_df.dropna(subset=['avg_sales_per_store'])
        avg_df = sales_df.groupby(['service_code']).agg({
            'avg_sales_per_store': 'mean',
            'region_name': 'first',
            'service_name': 'first'
        }).reset_index()
        avg_df['avg_sales_per_store'] = (avg_df['avg_sales_per_store'] / 3).round(2)
        return avg_df

    summary_list = []
    for y in years:
        df = get_avg_sales_sum(summary_sales[y])
        df['year'] = y
        summary_list.append(df)
    summary_df = pd.concat(summary_list, ignore_index=True) if summary_list else pd.DataFrame()

    if not summary_df.empty:
        summary_df.rename(columns={
            'region_name':'행정동명','service_name':'업종명','service_code':'업종코드',
            'avg_sales_per_store':'평균 월 매출'
        }, inplace=True)
        pivot_summary = summary_df.pivot_table(
            index=['행정동명','업종명'], columns='year', values='평균 월 매출', aggfunc='mean'
        ).reset_index()
        pivot_summary.columns.name = None
        pivot_summary.rename(columns={2022:'2022_평균매출', 2023:'2023_평균매출', 2024:'2024_평균매출'}, inplace=True)
        merged_df = merged_df.merge(pivot_summary, on=['업종명','행정동명'], how='left')
    else:
        for c in ['2022_평균매출','2023_평균매출','2024_평균매출']:
            merged_df[c] = 0.0

    for c in ['2022_평균매출','2023_평균매출','2024_평균매출']:
        if c not in merged_df.columns:
            merged_df[c] = 0.0
        merged_df[c] = pd.to_numeric(merged_df[c], errors='coerce').fillna(0.0)

    # ===== 스코어링 =====
    score_columns = [
        '평균영업기간(년)','점포수','1년 생존율(%)','3년 생존율(%)','5년 생존율(%)','평균 개업수','평균 폐업수',
        '2022_평균매출','2023_평균매출','2024_평균매출'
    ]
    weights = {
        '평균영업기간(년)': 0.05, '점포수': 0.15, '1년 생존율(%)': 0.05, '3년 생존율(%)': 0.07,
        '5년 생존율(%)': 0.10, '평균 개업수': 0.04, '평균 폐업수': -0.04,
        '2022_평균매출': 0.15, '2023_평균매출': 0.17, '2024_평균매출': 0.22
    }

    clean_df = merged_df[score_columns].replace([np.inf,-np.inf], np.nan).fillna(0)
    scaler = MinMaxScaler()
    normalized = scaler.fit_transform(clean_df)
    normalized_df = pd.DataFrame(normalized, columns=[f"norm_{c}" for c in score_columns])
    merged_with_norm = pd.concat([merged_df, normalized_df], axis=1)

    merged_with_norm['업종_추천점수'] = 0.0
    for col, w in weights.items():
        merged_with_norm['업종_추천점수'] += merged_with_norm[f"norm_{col}"] * w

    final_result = merged_with_norm.drop(columns=[f"norm_{c}" for c in score_columns]).sort_values(
        by='업종_추천점수', ascending=False
    ).reset_index(drop=True)

    print("📊 종합 지역 상권 요약 리포트")
    print(merged_df)
    print("🏆 최종 업종 추천 결과 (지역+업종 기준)")
    print(final_result[['행정동명','업종명','업종_추천점수']].head(10))

    # ===== 상위 TOPK에 대해 이유 생성 =====
    subcategory_df = pd.read_sql(
        "SELECT DISTINCT category_large, category_small FROM subcategory_store_count_stats", engine
    )

    recommendations = []
    for _, row in final_result.head(TOPK_FOR_REASON).iterrows():
        label = (row.get('업종명') or '').strip().replace('\r','')
        large_label = '기타'
        mr = subcategory_df[subcategory_df['category_small'] == label]
        if not mr.empty:
            large_label = mr.iloc[0]['category_large']

        reason, src = generate_reason_with_llm(gu_name, region, row)
        recommendations.append({
            'category_large': large_label,
            'category_small': label,
            'reason': reason
        })

    # ===== JSON 저장 (reloader 감시 밖 경로) =====
    runtime_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache', 'runtime'))
    os.makedirs(runtime_dir, exist_ok=True)
    out_path = os.path.join(runtime_dir, 'recommendation_industry.json')

    payload = { region: recommendations }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)

    print(json.dumps(payload, ensure_ascii=False, indent=4))
    return payload
