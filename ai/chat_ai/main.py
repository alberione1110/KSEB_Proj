# ai/chat_ai/main.py
from typing import List, Dict, Optional
import threading

from .report_loader import load_report_text_and_metadata
from .build_vector_db import process_all_pdfs
from .gpt_consultant import get_response_with_rag
from .csv_consultant import (
    answer_from_csv,
    answer_simple_recommendation,
    answer_top_recommendation,
)
from .utils import classify_question_and_subject
from .config import VECTOR_DB_DIR

_init_lock = threading.Lock()
_initialized = False

def _ensure_initialized() -> None:
    """PDF → 벡터스토어가 없으면 1회 구축."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        try:
            process_all_pdfs()  # /data 의 PDF → /data/vector_db 인덱스
        except Exception as e:
            print(f"[chat_ai] 벡터스토어 구축 경고: {e}")
        _initialized = True

def _normalize_history(messages: List[Dict]) -> List[Dict]:
    """front: 'user'|'bot' → llm: 'user'|'assistant'"""
    norm = []
    for m in messages[-12:]:
        role = (m.get("role") or "user").strip()
        content = (m.get("content") or "").strip()
        if not content:
            continue
        if role == "bot":
            role = "assistant"
        norm.append({"role": role, "content": content})
    return norm

def _load_context(context: Dict) -> Dict:
    """프론트/백 컨텍스트를 로더로 정리."""
    rpt_text, location, category, report_type = load_report_text_and_metadata(
        text=context.get("report_text"),
        location=context.get("region"),
        category=context.get("category_small"),
        report_type=context.get("purpose"),
    )
    return {
        "report_text": rpt_text,
        "location": location,
        "category": category,
        "report_type": report_type or "창업 준비",
    }

def generate_chat_response(messages: List[Dict], context: Optional[Dict] = None) -> str:
    """
    messages: [{role:'user'|'bot', content:str}, ...]
    context : {role, gu_name, region, category_large, category_small, purpose, report_text}
    """
    _ensure_initialized()

    ctx_in = context or {}
    history = _normalize_history(messages)
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "").strip()
    ctx = _load_context(ctx_in)

    # 질문 분류 → 처리 라우팅
    q_type, subject_type = classify_question_and_subject(last_user)

    if q_type == "순위추천":
        return answer_top_recommendation(last_user)

    if q_type in ("수치", "비교", "수치전략"):
        mode = "dong" if (subject_type == "지역") else "industry"
        target_name = ctx["location"] if mode == "dong" else ctx["category"]
        return answer_from_csv(last_user, target_name, mode)

    if q_type == "간단추천":
        return answer_simple_recommendation(last_user, ctx["location"])

    # 전략/정보 탐색(RAG) + 기타 fallback
    return get_response_with_rag(
        query=last_user,
        vectorstore_path=VECTOR_DB_DIR,
        context=ctx["report_text"],
        location=ctx["location"],
        category=ctx["category"],
        report_type=ctx["report_type"],
        history=history,
    )
