# ai/chat_ai/utils.py
import re
import json
from typing import Tuple

from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from .gpt_consultant import llm  # ✅ 상대 임포트

# === 질문 유형 / 대상 분류 프롬프트 ===
combined_prompt = PromptTemplate(
    template=(
        "질문: {question}\n\n"
        "아래 두 가지를 JSON 형식으로 정확히 분류해줘.\n"
        "1) question_type: 질문의 성격\n"
        "   - 수치: 특정 수치 값만 궁금한 질문 (예: 임대료가 얼마야?)\n"
        "   - 비교: 다른 지역과 수치를 비교하는 질문 (예: 더 유동인구 많은 데는?)\n"
        "   - 수치전략: 수치를 바탕으로 가능성·위험을 판단해달라는 질문 (예: 생존율이 낮은데 창업해도 될까?)\n"
        "   - 전략아이디어: SNS 활용, 마케팅, 차별화, 브랜딩 등 전략적 아이디어를 원하는 질문\n"
        "   - 간단추천: 메뉴, 이름, 감성 키워드 등 짧은 아이디어만 필요한 질문\n"
        "   - 순위추천: 특정 지표 기준 TOP N 지역을 추천해달라는 질문 (예: 유동인구 많은 지역 TOP 5 알려줘)\n"
        "   - rag: 문서 기반 창업 정보가 궁금한 질문\n\n"
        "2) subject_type: 질문의 대상\n"
        "   - 지역: 특정 동, 상권, 위치 중심 질문\n"
        "   - 업종: 카페, 음식점 등 업종 중심 질문\n\n"
        "출력은 반드시 JSON만 반환:\n"
        "{{\"question_type\": \"수치\", \"subject_type\": \"지역\"}}"
    ),
    input_variables=["question"]
)

# 전역 체인 재사용 (온도/모델은 gpt_consultant에서 이미 설정)
_combined_chain = LLMChain(llm=llm, prompt=combined_prompt)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)

def _extract_json_block(text: str) -> str:
    """응답에서 최초의 JSON 오브젝트 블록만 추출."""
    if not text:
        return ""
    # ```json ... ``` 같은 코드블록 제거
    t = re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()
    m = _JSON_BLOCK_RE.search(t)
    return m.group(0) if m else t  # 그래도 실패하면 원문 시도

def classify_question_and_subject(question: str) -> Tuple[str, str]:
    """
    질문을 (question_type, subject_type)으로 분류.
    실패 시 ('rag','지역') 폴백.
    """
    try:
        out = _combined_chain.invoke({"question": str(question)})
        raw = out["text"] if isinstance(out, dict) else str(out)
        js = _extract_json_block(raw)
        parsed = json.loads(js)
        qtype = parsed.get("question_type", "rag")
        stype = parsed.get("subject_type", "지역")
        return qtype, stype
    except Exception:
        return "rag", "지역"

# === 지역명 정규화 ===
# 예: "서울특별시 종로구 청운효자동" -> "청운효자동"
#     "종로구 종로1·2·3·4가동" -> "종로1·2·3·4가동"
_ADMIN_PREFIX_RE = re.compile(r"^(서울특별시|서울시)\s+")
_GU_SUFFIX_RE = re.compile(r"\s*[가-힣A-Za-z0-9·\.]+구\s*")
_PAREN_RE = re.compile(r"\s*\(.*?\)\s*")

def normalize_location(location: str) -> str:
    """
    행정동명만 뽑아내는 간단 정규화.
    - 시/구 접두 제거
    - 괄호 제거
    - 공백/기호 정리
    - 마지막에 '동'으로 끝나는 토큰 우선 선택
    """
    if not location:
        return ""

    s = str(location).strip()
    s = _PAREN_RE.sub(" ", s)            # 괄호 내용 제거
    s = _ADMIN_PREFIX_RE.sub("", s)      # '서울특별시 ' / '서울시 ' 제거
    s = s.replace(",", " ").replace("  ", " ").strip()

    # '○○구' 제거 (중간에 있을 수도 있어 유연하게)
    s = _GU_SUFFIX_RE.sub(" ", s).strip()
    tokens = [t for t in s.split() if t]

    # '...동'으로 끝나는 마지막 토큰 찾아서 반환
    for t in reversed(tokens):
        if t.endswith("동"):
            return t

    # 못 찾으면 마지막 토큰 반환
    return tokens[-1] if tokens else ""
