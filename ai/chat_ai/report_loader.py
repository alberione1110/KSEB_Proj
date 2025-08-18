# ai/chat_ai/report_loader.py
from typing import Optional, Tuple

def load_report_text_and_metadata(
    text: Optional[str] = None,
    location: Optional[str] = None,
    category: Optional[str] = None,
    report_type: Optional[str] = None,
) -> Tuple[str, str, str, str]:
    """
    파일 의존 없이 프론트/백에서 넘긴 값으로 동작.
    - text        : 리포트 본문(RAG 컨텍스트)
    - location    : 지역명
    - category    : 업종 소분류
    - report_type : '창업 준비' | '시장조사' | '확장'
    """
    report_text = (text or "").strip()
    loc = (location or "").strip() or "지역정보없음"
    cat = (category or "").strip() or "업종정보없음"
    rtp = (report_type or "").strip() or "창업 준비"
    return report_text, loc, cat, rtp
