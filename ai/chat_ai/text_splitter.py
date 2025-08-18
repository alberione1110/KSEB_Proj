# ai/chat_ai/text_splitter.py
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Optional

def split_text(
    text: Optional[str],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: Optional[list] = None
) -> List[str]:
    """
    긴 텍스트를 RecursiveCharacterTextSplitter로 나누어 반환.
    - PDF/문서 전처리 결과를 청크 단위로 쪼갬
    - chunk_size: 청크 최대 길이
    - chunk_overlap: 청크 간 중복 문자 수
    - separators: 분리 기준 우선순위 (없으면 기본값)
    """
    if not text:
        return []

    # 불필요한 공백/줄바꿈 정리
    clean_text = str(text).replace("\r", "").strip()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators or ["\n\n", "\n", ".", " ", ""]
    )
    return splitter.split_text(clean_text)
