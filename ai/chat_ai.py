# ai/chat_ai.py

def generate_chat_response(messages):
    """
    전달받은 messages: [{ role: 'user'/'bot', content: '...' }] 리스트를 기반으로
    마지막 사용자 메시지를 분석한 더미 응답 생성
    """
    if not messages:
        return "안녕하세요! 무엇을 도와드릴까요?"

    last_user_msg = next((msg["content"] for msg in reversed(messages) if msg["role"] == "user"), None)

    if last_user_msg:
        return f'당신이 말씀하신 "{last_user_msg}"에 대해 분석 중입니다!'
    else:
        return "죄송합니다. 이해하지 못했습니다."
