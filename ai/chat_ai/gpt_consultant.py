# ai/chat_ai/gpt_consultant.py
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# ✅ 상대 임포트
from .config import OPENAI_API_KEY, MODEL, VECTOR_DB_DIR

# ---- OpenAI 초기화 ----
# 임베딩/LLM은 모듈 로드 시 1회 초기화
embedding = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)  # 기본: text-embedding-3-small
llm = ChatOpenAI(model_name=MODEL, openai_api_key=OPENAI_API_KEY, temperature=0.3)

# ---- 시스템 프롬프트 ----
system_context = """
너는 서울 지역 창업을 전문으로 컨설팅하는 GPT 컨설턴트야.
레포트(report.text)를 기반으로 질문을 해석하고, 사용자에게 전략적 조언을 줘야 해. 

[컨설팅 시스템의 작동 방식]
- 모든 답변은 사용자 질문을 바탕으로, 미리 분석한 상권 보고서(report.txt)와 수치 기반 데이터(filtered_result.csv, filtered_result_industry)를 근거로 제공해야 함
- 마케팅 관련 전략과 추천에 대한 근거는 recommandation_dong, recommandation_industry를 기반으로 답변해야함.
- 상권 분석 보고서에는 해당 지역의 특성, 유동 인구, 생존율, 개·폐업 추이, 임대료 등이 포함됨
- 수치 기반 CSV 자료에는 서울시 각 동별 평균 임대시세, 생존율, 점포 수, 개업/폐업 수 등의 지표가 포함됨

[답변 작성 시 유의사항]
- 반드시 서울 지역 상권 내 창업에 초점을 맞춘 실질적이고 구체적인 조언을 할 것
- 단순 요약이 아니라, 사용자의 업종과 지역을 고려해 성공 가능성을 높일 수 있는 전략적 조언을 제공할 것
- 특히 경쟁이 치열한 업종의 경우, 주변 상권과의 차별화 전략(메뉴, 인테리어, 타깃층 등)을 창의적이고 지역 특성에 맞게 제안할 것
- 필요 시 수치 기반 비교, 예시 제시, 전략 대안 제안 등도 포함해줘

📌 답변 형식 지침:
- 일반적인 분석/해석은 3~4줄 이내로 간결하게 요약
- 전략 제안, 차별화 아이디어, 메뉴 추천 등은 리스트 형식으로 깔끔하게 나열
- 숫자나 지표는 정확히 포함 (예: "5년 생존율 50.7%")
"""

def get_specific_instructions(report_type: str) -> str:
    if report_type == "창업 준비":
        return """
        [사용자 프로필]
        - 창업 경험이 없는 예비 사장님
        - 업종·상권 분석에 대한 지식이 거의 없고, 전문 용어 이해도가 낮음
        - 사업 계획 수립이 처음이며, 자본과 리스크에 민감함

        [답변 톤 & 스타일]
        - 쉽고 친근한 어투, 전문 용어는 풀어서 설명
        - 단계별 접근(1단계, 2단계...) 구조로 안내
        - 비유, 사례를 활용해 직관적 이해를 돕기
        - 불필요한 데이터 과잉 제공 대신 핵심 지표만 명확히 제시

        [내용 우선순위]
        1) 상권·임대료·유동인구 등 기초 지표의 의미와 해석
        2) 창업 준비 절차와 체크리스트
        3) 비용 절감 및 리스크 최소화 팁
        4) 업종·입지별 성공 사례 소개
        """
    elif report_type == "시장조사":
        return """
        [사용자 프로필]
        - 현재 매장을 운영 중인 현직 사장님
        - 업종 운영 경험이 있으며, 현 매출·고객 데이터 보유
        - 신제품 출시, 마케팅 전략 변경, 확장 가능성 평가를 위해 시장 동향이 필요함

        [답변 톤 & 스타일]
        - 전문적이고 분석적인 어투
        - 데이터와 수치를 근거로 결론 제시
        - 통계, 비교 분석, 업계 트렌드를 적극 활용
        - 실행 전략은 구체적이고 ROI 중심으로 제안

        [내용 우선순위]
        1) 현재 시장 점유율·성장률·소비 트렌드
        2) 경쟁사 분석(가격·상품·마케팅 전략)
        3) 매출 확대 가능성이 높은 품목과 채널
        4) 단기·중장기 시장 리스크 요인
        """
    elif report_type == "확장":
        return """
        [사용자 프로필]
        - 기존 매장을 안정적으로 운영 중인 사장님
        - 신규 지점 출점 또는 브랜드 확장을 고려 중
        - 운영 효율, 인력 관리, 자본 배분에 관심이 높음

        [답변 톤 & 스타일]
        - 투자자 보고서처럼 논리적·계산적인 설명
        - 비용 구조와 수익성 분석 강조
        - 지역·상권 포화도와 경쟁 분석 포함
        - 확장 시 예상되는 리스크와 대안 제시

        [내용 우선순위]
        1) 신규 입지의 상권 분석(유동인구·임대료·경쟁 강도)
        2) 기존 매장과의 시너지 효과 가능성
        3) 확장에 따른 비용 구조 변화와 수익성 예측
        4) 장기 성장 전략과 확장 속도 조절 방안
        """
    return ""

def format_history(history: List[Dict]) -> str:
    if not history:
        return ""
    lines = []
    for h in history:
        role = h.get("role", "user")
        content = h.get("content", "")
        if not content:
            continue
        who = "사용자" if role == "user" else "컨설턴트"
        lines.append(f"{who}: {content}")
    return "\n".join(lines)

prompt_template = PromptTemplate(
    template=(
        system_context + "\n\n"
        "{specific}\n\n"
        "[이전 대화 기록]\n{history}\n\n"
        "[레포트 종류: {report_type}]\n"
        "[분석 지역: {location}]\n[분석 업종: {category}]\n"
        "[문서 요약 정보]\n{context}\n\n[사용자 질문]\n{question}"
    ),
    input_variables=["context", "question", "location", "category", "report_type", "specific", "history"]
)

def get_response_with_rag(
    query: str,
    vectorstore_path: Optional[str] = None,
    context: str = "",
    location: str = "",
    category: str = "",
    report_type: str = "",
    history: Optional[List[Dict]] = None,
) -> str:
    """
    RAG 기반 답변 생성.
    - vectorstore_path 미지정 시 config.VECTOR_DB_DIR 사용
    - history: [{role:'user'|'assistant'|'bot', content:str}, ...]
    """
    # 1) 벡터스토어 로드
    path = vectorstore_path or VECTOR_DB_DIR
    try:
        db = FAISS.load_local(
            folder_path=path,
            embeddings=embedding,
            allow_dangerous_deserialization=True
        )
    except Exception as e:
        return f"지식베이스를 아직 준비하지 못했어요. (벡터스토어 경로: {path})\n관리자: 인덱스를 먼저 생성해 주세요. 상세: {e}"

    retriever = db.as_retriever()

    # 2) 관련 문서 검색 → 컨텍스트 갱신
    try:
        docs = retriever.invoke(query)
        if docs:
            context = "\n\n".join([getattr(d, "page_content", "") for d in docs if getattr(d, "page_content", "")])
    except Exception as e:
        # 검색 실패 시에도 최소 동작
        context = context or ""
    
    # 3) report_type별 세부 지시문
    specific_instructions = get_specific_instructions(report_type)

    # 4) 프롬프트 + LLM 실행
    chain = LLMChain(llm=llm, prompt=prompt_template)
    out = chain.invoke({
        "context": context,
        "question": query,
        "location": location,
        "category": category,
        "report_type": report_type,
        "specific": specific_instructions,
        "history": format_history(history or []),
    })
    return out["text"] if isinstance(out, dict) else str(out)
