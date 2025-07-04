import speech_recognition as sr
import csv
from datetime import datetime
import os

def transcribe_audio_file(file_path):
    recognizer = sr.Recognizer()

    if not os.path.exists(file_path):
        print("오디오 파일 없음:", file_path)
        return ""

    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language='ko-KR')
        print(f"[{os.path.basename(file_path)}] 인식된 텍스트: {text}")
        return text
    except sr.UnknownValueError:
        print(f"[{os.path.basename(file_path)}] 음성을 이해하지 못함.")
        return ""
    except sr.RequestError as e:
        print(f"[{os.path.basename(file_path)}] Google API 오류: {e}")
        return ""

def save_response(filename, text, filepath="responses.csv"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([now, filename, text])

if __name__ == "__main__":
    folder_path = "dementia_audio/audio_samples"
    audio_files = sorted([f for f in os.listdir(folder_path) if f.endswith(".wav")])

    for file_name in audio_files:
        full_path = os.path.join(folder_path, file_name)
        text = transcribe_audio_file(full_path)
        if text:
            save_response(file_name, text)