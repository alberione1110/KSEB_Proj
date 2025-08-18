import os
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine
from dotenv import load_dotenv

# .env 자동 로드 (back/.env 또는 프로젝트 루트 .env)
# 존재하지 않아도 에러내지 않음.
load_dotenv()

def _required(name: str) -> str:
    val = os.getenv(name)
    if not val or not val.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return val.strip()

@lru_cache(maxsize=1)
def get_db_url() -> str:
    host = _required("DB_HOST")
    port = _required("DB_PORT")
    user = _required("DB_USER")
    password = _required("DB_PASSWORD")
    name = _required("DB_NAME")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

@lru_cache(maxsize=1)
def get_engine():
    url = get_db_url()
    # utf8mb4 + pre_ping 권장
    return create_engine(
        url,
        connect_args={"charset": "utf8mb4"},
        pool_pre_ping=True,
    )
