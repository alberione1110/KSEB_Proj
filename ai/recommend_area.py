def get_recommendation(industry):
    # 예시 더미 데이터
    dummy = {
        '한식음식점': [
            {'district': '홍대동', 'reason': '유동인구가 많고 젊은 층이 많이 거주함'},
            {'district': '신촌동', 'reason': '대학생 밀집 지역으로 카페 수요가 높음'},
            {'district': '망원동', 'reason': '감성 카페 거리로 주목받는 지역'}
        ],
        '편의점': [
            {'district': '을지로동', 'reason': '사무실 밀집 지역으로 24시간 수요 존재'},
            {'district': '강남동', 'reason': '야간 소비 및 유흥 업소 수요가 높음'},
            {'district': '구로동', 'reason': '공단 지역으로 근로자 중심 수요가 많음'}
        ]
    }
    return dummy.get(industry, [])
