# back/routes/chat.py
from flask import Blueprint, request, jsonify
from flask_cors import CORS

# ai 패키지에서 엔트리 임포트
from ai.chat_ai.main import generate_chat_response

bp = Blueprint('chat', __name__)
CORS(bp)

@bp.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json(force=True) or {}
        messages = data.get('messages', [])

        # 프론트에서 전달하는 리포트/맥락 정보를 그대로 넘겨줌
        context = {
            "role": data.get("role"),
            "gu_name": data.get("gu_name"),
            "region": data.get("region"),
            "category_large": data.get("category_large"),
            "category_small": data.get("category_small"),
            "purpose": data.get("purpose"),
            "report_text": data.get("report_text"),
        }

        reply = generate_chat_response(messages, context=context)
        return jsonify({"response": reply})

    except Exception as e:
        print("[Error] /api/chat 실패:", e)
        return jsonify({"error": "챗봇 응답 실패"}), 500
