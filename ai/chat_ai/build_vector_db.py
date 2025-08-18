import os
from .pdf_loader import extract_text_from_pdf
from .text_splitter import split_text
from .rag_embedder import save_to_vectorstore
from .config import PROJECT_ROOT

# PDF와 벡터 저장 경로 지정
PDF_DIR_DEFAULT = os.path.join(PROJECT_ROOT, "data")
VECTOR_DB_DIR_DEFAULT = os.path.join(PROJECT_ROOT, "data", "vector_db")

def process_all_pdfs(pdf_dir=PDF_DIR_DEFAULT,
                     vector_dir=VECTOR_DB_DIR_DEFAULT):
    print(f"📁 PDF 디렉토리 경로: {pdf_dir}")
    print(f"💾 벡터 저장 경로: {vector_dir}")

    os.makedirs(vector_dir, exist_ok=True)

    texts = []
    found_pdf = False
    for filename in sorted(os.listdir(pdf_dir)):
        print(f"🔍 발견한 파일: {filename}")
        if filename.lower().endswith(".pdf"):
            found_pdf = True
            path = os.path.join(pdf_dir, filename)
            print(f"📄 처리 중: {filename}")
            text = extract_text_from_pdf(path)
            if text:
                texts.append(text)
            else:
                print(f"⚠️ 텍스트 추출 실패: {filename}")

    if not found_pdf:
        print("❌ PDF 파일이 없습니다. 디렉토리를 확인하세요.")
        return vector_dir

    if not texts:
        print("⚠️ PDF에서 텍스트를 추출하지 못했습니다.")
        return vector_dir

    full_text = "\n\n".join(texts)
    chunks = split_text(full_text)

    print(f"🧩 청크 수: {len(chunks)}")

    save_to_vectorstore(chunks, save_path=vector_dir)
    print(f"\n✅ 총 {len(chunks)}개 chunk로 저장 완료.")
    return vector_dir

if __name__ == "__main__":
    process_all_pdfs()