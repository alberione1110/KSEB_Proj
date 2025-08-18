# ai/chat_ai/rag_embedder.py
import os
from typing import Iterable, List
from tqdm import tqdm

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

from .config import OPENAI_API_KEY, VECTOR_DB_DIR

def _as_str_chunks(chunks: Iterable) -> List[str]:
    out = []
    for c in chunks:
        if c is None:
            continue
        # dict 형태({text: ...})나 Document 형태 대응
        if hasattr(c, "page_content"):
            out.append(str(getattr(c, "page_content")))
        elif isinstance(c, dict) and "text" in c:
            out.append(str(c["text"]))
        else:
            out.append(str(c))
    # 빈 문자열 제거
    return [s for s in (t.strip() for t in out) if s]

def save_to_vectorstore(
    chunks: Iterable,
    save_path: str = None,
    batch_size: int = 100,
    embedding_model: str = "text-embedding-3-small",
) -> str:
    """
    청크 텍스트를 임베딩하여 FAISS 벡터스토어로 저장.
    - chunks: 문자열/Document/딕셔너리 혼합 가능
    - save_path: 지정 없으면 config.VECTOR_DB_DIR/faiss_index 에 저장
    - 반환: 저장된 인덱스의 폴더 경로
    """
    texts = _as_str_chunks(chunks)
    if not texts:
        raise ValueError("[rag_embedder] 저장할 청크가 없습니다.")

    # 저장 경로 결정 및 보장
    base_dir = VECTOR_DB_DIR
    index_dir = save_path or os.path.join(base_dir, "faiss_index")
    os.makedirs(index_dir, exist_ok=True)

    # 임베딩 초기화 (환경변수/설정에 있는 키 사용)
    embedding = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model=embedding_model,
    )

    vectordb = None
    total = len(texts)
    for i in tqdm(range(0, total, batch_size), desc="🔄 벡터스토어 생성 중"):
        batch = texts[i : i + batch_size]
        # 배치 단위로 벡터스토어 생성 후 병합
        batch_db = FAISS.from_texts(batch, embedding)
        if vectordb is None:
            vectordb = batch_db
        else:
            vectordb.merge_from(batch_db)

    if vectordb is None:
        raise RuntimeError("[rag_embedder] 벡터스토어 생성에 실패했습니다.")

    # 로컬 저장
    vectordb.save_local(index_dir)
    return index_dir
