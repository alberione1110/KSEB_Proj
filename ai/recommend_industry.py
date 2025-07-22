def get_recommendation(gu_name, region):
    district = f'{gu_name} {region}'
    return [
        {
            'category_small': '카페',
            'category_large': '외식업',
            'reason': f'{district}는 유동인구가 많아 카페 수요가 높습니다.',
        },
        {
            'category_small': '헬스장',
            'category_large': '운동/건강',
            'reason': f'{district}는 20~30대 인구 비중이 높아 헬스장 수요가 증가 중입니다.',
        },
        {
            'category_small': '코인노래방',
            'category_large': '여가/오락',
            'reason': f'{district}는 대학가 근처로 코인노래방 수요가 많습니다.',
        },
    ]
