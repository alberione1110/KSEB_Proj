# back/routes/chat.py
from flask import Blueprint, request, jsonify
from flask_cors import CORS
import sys, os

# ai/chat_ai.py 사용
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ai')))
from chat_ai import generate_chat_response

bp = Blueprint('chat', __name__)
CORS(bp)

@bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        messages = data.get('messages', [])

        print("[Chat] 받은 메시지 목록:", messages)

        response = generate_chat_response(messages)
        return jsonify({"response": response})

    except Exception as e:
        print("[Error] 챗봇 응답 실패:", str(e))
        return jsonify({"error": "챗봇 응답 실패"}), 500
