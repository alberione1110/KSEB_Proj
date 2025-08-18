# ai/chat_ai/data_loader.py
import os, json
import pandas as pd
from pathlib import Path

# 프로젝트 루트 기준으로 back/data 탐색 (기본은 /back)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("BACK_DIR", PROJECT_ROOT / "back")).resolve()

DONG_CSV = "filtered_result_dong.csv"
IND_CSV  = "filtered_result_industry.csv"
DONG_JSON = "recommendation_dong.json"
IND_JSON  = "recommendation_industry.json"

def _must(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"[data_loader] 파일을 찾을 수 없습니다: {path}")
    return path

def load_csv_data():
    dong_df = pd.read_csv(_must(DATA_DIR / DONG_CSV))
    industry_df = pd.read_csv(_must(DATA_DIR / IND_CSV))
    return dong_df, industry_df

def load_json_reasons():
    with open(_must(DATA_DIR / DONG_JSON), "r", encoding="utf-8") as f:
        dong_reasons = json.load(f)
    with open(_must(DATA_DIR / IND_JSON), "r", encoding="utf-8") as f:
        industry_reasons = json.load(f)
    return dong_reasons, industry_reasons
