# ai/recommend_area.py

def get_recommendation(category_small, gu_name):
    dummy = {
        '한식음식점': [
            {'district': f'{gu_name} 홍대동', 'reason': '유동인구가 많고 젊은 층이 많이 거주함'},
            {'district': f'{gu_name} 신촌동', 'reason': '대학생 밀집 지역으로 한식 수요가 높음'},
            {'district': f'{gu_name} 망원동', 'reason': '감성 맛집 거리로 주목받는 지역'}
        ],
        '편의점': [
            {'district': f'{gu_name} 을지로동', 'reason': '사무실 밀집 지역으로 24시간 수요 존재'},
            {'district': f'{gu_name} 강남동', 'reason': '야간 소비 및 유흥 업소 수요가 높음'},
            {'district': f'{gu_name} 구로동', 'reason': '공단 지역으로 근로자 중심 수요가 많음'}
        ],
        '카페': [
            {'district': f'{gu_name} 합정동', 'reason': '카페 골목으로 유명한 지역'},
            {'district': f'{gu_name} 연남동', 'reason': '트렌디한 감성 카페 밀집'},
            {'district': f'{gu_name} 서교동', 'reason': 'MZ세대 유동인구 많음'}
        ]
    }

    return dummy.get(category_small, [])
