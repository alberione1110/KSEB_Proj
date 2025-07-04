import speech_recognition as sr
import csv
from datetime import datetime

def record_and_transcribe():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        print("음성 입력 대기 중...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        print("녹음 완료. 텍스트로 변환 중...")

    try:
        text = recognizer.recognize_google(audio, language='ko-KR')
        print("인식된 텍스트:", text)
        return text
    except sr.UnknownValueError:
        print("음성을 이해하지 못했습니다.")
        return ""
    except sr.RequestError as e:
        print(f"Google API 요청 실패: {e}")
        return ""

def save_text_response(text, filepath="responses.csv"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([now, text])

if __name__ == "__main__":
    text = record_and_transcribe()
    if text:
        save_text_response(text)