# ai/recommend_industry.py

def get_recommendation(district):
    return [
        {
            'industry': '카페',
            'reason': f'{district}는 유동인구가 많아 카페 수요가 높습니다.',
        },
        {
            'industry': '헬스장',
            'reason': f'{district}는 20~30대 인구 비중이 높아 헬스장 수요가 증가 중입니다.',
        },
        {
            'industry': '코인노래방',
            'reason': f'{district}는 대학가 근처로 코인노래방 수요가 많습니다.',
        },
    ]
