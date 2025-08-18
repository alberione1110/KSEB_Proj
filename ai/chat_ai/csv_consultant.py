# ai/chat_ai/csv_consultant.py
from .data_loader import load_csv_data, load_json_reasons
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from .gpt_consultant import llm
from .utils import normalize_location
import pandas as pd

# 데이터 로드 (/back 경로에서 읽도록 data_loader가 처리)
dong_df, industry_df = load_csv_data()
dong_reasons, industry_reasons = load_json_reasons()

KEYWORD_COLUMN_MAP = {
    "유동인구": "유동인구",
    "임대료": "임대시세",
    "임대시세": "임대시세",
    "생존율": ["1년 생존율(%)", "3년 생존율(%)", "5년 생존율(%)"],
    "개업": "평균 개업수",
    "폐업": "평균 폐업수",
    "점포": "점포수",
    "영업기간": "평균영업기간(년)",
    "지역 점수": "지역_점수",
    "좋은 지역": "지역_점수",
}

csv_prompt_template = PromptTemplate(
    template=(
        "다음은 서울 지역 창업 분석 수치야:\n"
        "[대상: {target_name}]\n"
        "질문: {question}\n"
        "수치 요약:\n"
        "{stats}\n\n"
        "(임대시세는 3.3㎡(평)당 월세 기준임)\n\n"
        "위 수치를 바탕으로 자연스럽게 설명해줘.\n"
        "- 먼저 질문과 관련된 수치를 해석해주고,\n"
        "- 그 다음 창업 전략이나 조언을 대화체로 덧붙여줘.\n\n"
        "답변은 간결하고 유창하게 작성하고, 숫자는 구체적으로 써줘."
    ),
    input_variables=["target_name", "question", "stats"]
)
csv_chain = LLMChain(llm=llm, prompt=csv_prompt_template)

def extract_relevant_stats(question: str, row: pd.Series) -> str:
    stats = []
    q = str(question)

    for keyword, columns in KEYWORD_COLUMN_MAP.items():
        if keyword in q:
            if isinstance(columns, str):
                value = row.get(columns)
                if pd.notna(value):
                    if "인구" in keyword:
                        stats.append(f"- {keyword}: {int(value):,}명")
                    elif "임대" in keyword:
                        stats.append(f"- {keyword}: 3.3㎡당 {int(value):,}원")
                    else:
                        stats.append(f"- {keyword}: {value}")
            else:
                survival_stats = "\n".join(
                    [f"- {col}: {row[col]}%" for col in columns if pd.notna(row.get(col))]
                )
                if survival_stats:
                    stats.append(survival_stats)

    if not stats and pd.notna(row.get("유동인구")):
        stats.append(f"- 유동인구: {int(row['유동인구']):,}명")

    return "\n".join(stats)

def get_recommendation_text(target_name: str, reasons: dict, mode: str) -> str:
    if mode == "dong":
        for _, reason_list in reasons.items():
            for r in reason_list:
                if r.get("district") == target_name:
                    return f"\n추천 이유: {r.get('reason','')}"
        return ""
    else:
        if target_name in reasons:
            return "\n".join(
                [f"- {r.get('category_small')}: {r.get('reason','')}" for r in reasons[target_name]]
            )
        return ""

def answer_from_csv(question: str, target_name: str, mode: str = "dong") -> str:
    target_name = normalize_location(target_name)
    question = str(question).lower()

    df = dong_df if mode == "dong" else industry_df
    reasons = dong_reasons if mode == "dong" else industry_reasons
    column_name = "행정동명" if mode == "dong" else "업종명"

    row_sel = df[df[column_name] == target_name]
    if row_sel.empty:
        return f"{target_name}에 대한 데이터가 없어."

    row = row_sel.iloc[0]
    stats = extract_relevant_stats(question, row)
    reason_text = get_recommendation_text(target_name, reasons, mode)

    out = csv_chain.invoke({
        "target_name": target_name,
        "question": question,
        "stats": (stats + ("\n" + reason_text if reason_text else "")),
    })
    return out["text"] if isinstance(out, dict) else str(out)

def answer_top_recommendation(question: str, top_n: int = 5) -> str:
    q_lower = str(question).lower()
    df = dong_df.copy()

    if "유동인구" in q_lower:
        column, ascending = "유동인구", False
    elif ("임대료" in q_lower) or ("임대시세" in q_lower):
        column = "임대시세"
        ascending = True if any(w in q_lower for w in ["낮", "싼"]) else False
    elif "생존율" in q_lower:
        column, ascending = "5년 생존율(%)", False
    elif ("지역 점수" in q_lower) or ("좋은 지역" in q_lower):
        column, ascending = "지역_점수", False
    else:
        return "추천 기준을 알 수 없어. 유동인구, 임대료, 생존율, 지역 점수 중 하나로 물어봐줘."

    result = df.sort_values(column, ascending=ascending).head(top_n)

    unit = "3.3㎡당 원" if column == "임대시세" else ("명" if column == "유동인구" else "%")
    lines = [f"{row['행정동명']} ({column}: {row[column]:,.1f} {unit})" for _, row in result.iterrows()]
    return f"{column} 기준 추천 TOP {top_n} 지역:\n" + "\n".join(lines)

def answer_simple_recommendation(question: str, location: str) -> str:
    prompt = PromptTemplate(
        template=(
            "서울 창업 컨설턴트야.\n"
            "사용자 질문: {question}\n"
            "지역: {location}\n\n"
            "수치 분석 없이 간단한 아이디어나 추천만 필요한 상황이야.\n"
            "메뉴, 브랜딩, 이름 추천 등 짧고 실용적인 조언을 해줘."
        ),
        input_variables=["question", "location"]
    )
    chain = LLMChain(llm=llm, prompt=prompt)
    out = chain.invoke({"question": question, "location": location})
    return out["text"].strip() if isinstance(out, dict) else str(out).strip()
