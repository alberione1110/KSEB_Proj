# ai/chat_ai/pdf_loader.py
import os
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        print(f"[pdf_loader] 파일을 찾을 수 없습니다: {pdf_path}")
        return ""
    try:
        reader = PdfReader(pdf_path)
        texts = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ""
                if t:
                    texts.append(t.strip())
            except Exception as e:
                print(f"[pdf_loader] 페이지 {i} 추출 실패: {e}")
        return "\n\n".join(texts).strip()
    except Exception as e:
        print(f"[pdf_loader] PDF 열기 실패: {pdf_path} ({e})")
        return ""
