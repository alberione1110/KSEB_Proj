import { useRef, useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import ksebLogo from '../img/kseb_logo.png'
import seoulBg from '../img/seoul.avif'
import ownerImg from '../img/owner.jpg'
import preownerImg from '../img/preowner.jpg'
import section2bg from '../img/section2.jpg'
import section3bg from '../img/section3.jpg'
import '../App.css'
import Select from 'react-select'
import districtOptions from '../data/districtOptions'
import industryCategories from '../data/industryOptions'
import axios from 'axios'

function HomePage() {
  const ownerRef = useRef(null)
  const preOwnerRef = useRef(null)
  const [rawMonthlySales, setRawMonthlySales] = useState('')
  const [formattedMonthlySales, setFormattedMonthlySales] = useState('')
  const [selectedRole, setSelectedRole] = useState(null)
  const navigate = useNavigate()
  const [selectedDistrict, setSelectedDistrict] = useState(null)
  const [mainIndustry, setMainIndustry] = useState(null) // 대분류
  const [subIndustry, setSubIndustry] = useState(null) // 소분류
  const industryMainOptions = Object.keys(industryCategories).map(
    (category) => ({
      label: category,
      value: category,
    })
  )
  const subIndustryOptions = mainIndustry
    ? industryCategories[mainIndustry.value].map((sub) => ({
        label: sub,
        value: sub,
      }))
    : []
  const handleMonthlySalesChange = (e) => {
    const input = e.target.value.replace(/[^0-9]/g, '') // 숫자만
    const formatted = input.replace(/\B(?=(\d{3})+(?!\d))/g, ',') // 3자리 콤마
    setRawMonthlySales(input)
    setFormattedMonthlySales(formatted)
  }

  const [purpose, setPurpose] = useState(null)

  useEffect(() => {
    const setVh = () => {
      const vh = window.innerHeight * 0.01
      document.documentElement.style.setProperty('--vh', `${vh}px`)
    }

    setVh() // 초기 실행
    window.addEventListener('resize', setVh) // 창 크기 변경 시 업데이트

    return () => window.removeEventListener('resize', setVh)
  }, [])
  // 선택된 역할에 따라 자동 스크롤
  useEffect(() => {
    if (selectedRole === 'owner' && ownerRef.current) {
      ownerRef.current.scrollIntoView({ behavior: 'smooth' })
    }
    if (selectedRole === 'preOwner' && preOwnerRef.current) {
      preOwnerRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [selectedRole])

  return (
    <div
      className="App"
      style={{ fontFamily: 'sans-serif', scrollBehavior: 'smooth' }}
    >
      {/* Section 1: 메인 영역 */}
      <section style={{ color: 'white' }}>
        {/* 상단: 배경 이미지 적용 영역 */}
        <div
          style={{
            backgroundImage: `url(${seoulBg})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            paddingBottom: '6rem',
            position: 'relative',
            height: 'calc(var(--vh, 1vh) * 50)',
          }}
        >
          {/* 어두운 Overlay */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0,0,0,0.5)',
              zIndex: 1,
            }}
          />

          {/* Header */}
          <header
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '1rem 2rem',
              position: 'relative',
              zIndex: 2,
            }}
          >
            <img src={ksebLogo} alt="KSEB Logo" style={{ width: '100px' }} />
            <div>
              <button
                style={{
                  backgroundColor: '#726EFF',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '0.5rem 1rem',
                  fontWeight: 'bold',
                  marginRight: '1rem',
                }}
                onClick={() => navigate('/chatbot')}
              >
                챗봇 상담
              </button>
              <button
                style={{
                  backgroundColor: 'transparent',
                  border: '1px solid white',
                  borderRadius: '8px',
                  padding: '0.5rem 1rem',
                  color: 'white',
                }}
              >
                로그인
              </button>
            </div>
          </header>

          {/* 검색 영역 */}
          <div
            style={{
              paddingTop: '6rem',
              textAlign: 'center',
              position: 'relative',
              zIndex: 2,
            }}
          >
            <h1
              style={{
                fontSize: '2.5rem',
                fontWeight: '800',
                lineHeight: '1.4',
              }}
            >
              서울에서 <br /> 창업하고 싶으신가요?
            </h1>
            <p
              style={{
                color: '#f0f0f0',
                marginTop: '1rem',
                fontSize: '1.1rem',
              }}
            >
              당신에게 딱! 맞는 터, “딱!터”가 찾아드립니다.
            </p>

            <div
              style={{
                marginTop: '3rem',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <Select
                options={districtOptions}
                placeholder="지역명을 입력하세요 (예: 강남구)"
                value={selectedDistrict}
                onChange={(selected) => setSelectedDistrict(selected)}
                isClearable={true}
                styles={{
                  container: (base) => ({
                    ...base,
                    width: '60%',
                    maxWidth: '500px',
                  }),
                  control: (base) => ({
                    ...base,
                    borderRadius: '9999px',
                    padding: '4px 8px',
                    fontSize: '1rem',
                    backgroundColor: 'rgba(255,255,255,0.7)',
                    border: 'none',
                    backdropFilter: 'blur(4px)',
                    boxShadow: 'none',
                    textAlign: 'left',
                  }),
                  singleValue: (styles) => ({
                    ...styles,
                    color: '#555',
                    textAlign: 'left',
                  }),
                  placeholder: (styles) => ({
                    ...styles,
                    color: 'black',
                    textAlign: 'left',
                  }),
                  menu: (base) => ({
                    ...base,
                    textAlign: 'left',
                  }),
                  option: (base, state) => ({
                    ...base,
                    color: 'black',
                    backgroundColor: state.isFocused ? '#f0f0f0' : 'white',
                  }),
                }}
              />
            </div>
          </div>
        </div>

        {/* 하단: 카드 선택 영역 (배경 이미지 X) */}
        <div
          style={{
            backgroundColor: '#ffffffff',
            padding: '1rem 2rem',
            color: 'black',
          }}
        >
          <h2
            style={{
              textAlign: 'center',
              marginBottom: '2rem',
              fontWeight: 'bold',
              fontSize: '1.5rem',
            }}
          >
            어떤 분이신가요?
          </h2>

          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '2rem',
              flexWrap: 'wrap',
            }}
          >
            {/* 사장님 카드 */}
            <div
              id="role-owner-card"
              onClick={() => {
                if (
                  !selectedDistrict ||
                  !selectedDistrict.label ||
                  !selectedDistrict.value
                ) {
                  alert('먼저 지역을 선택해주세요!')
                  return
                }
                setSelectedRole('owner')
              }}
              style={{
                backgroundImage: `url(${ownerImg})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                color: 'white',
                borderRadius: '20px',
                padding: '2rem',
                width: '250px',
                height: '200px',
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
              }}
            >
              {/* 반투명 블러 오버레이 */}
              <div
                style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  right: 0,
                  padding: '0.3rem',
                  backgroundColor: 'rgba(0, 0, 0, 0.5)', // 아래쪽 어둡게
                  backdropFilter: 'blur(4px)',
                }}
              >
                <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                  사장님
                </h3>
                <p
                  style={{
                    marginTop: '0.5rem',
                    fontSize: '0.95rem',
                    color: '#CCCCCC',
                  }}
                >
                  2호점을 내고 싶어요
                  <br />
                  시장 조사를 하고 싶어요
                </p>
              </div>
            </div>

            {/* 예비 사장님 카드 */}
            <div
              id="role-preowner-card"
              onClick={() => {
                if (
                  !selectedDistrict ||
                  !selectedDistrict.label ||
                  !selectedDistrict.value
                ) {
                  alert('먼저 지역을 선택해주세요!')
                  return
                }
                setSelectedRole('preOwner')
              }}
              style={{
                backgroundImage: `url(${preownerImg})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                color: 'white',
                borderRadius: '20px',
                padding: '2rem',
                width: '250px',
                height: '200px',
                cursor: 'pointer',
                position: 'relative',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'flex-end',
                marginLeft: '3rem',
              }}
            >
              {/* 반투명 블러 오버레이 */}
              <div
                style={{
                  position: 'absolute',
                  bottom: 0,
                  left: 0,
                  right: 0,
                  padding: '0.3rem',
                  backgroundColor: 'rgba(0, 0, 0, 0.5)', // 아래쪽 어둡게
                  backdropFilter: 'blur(4px)',
                }}
              >
                <h3 style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                  예비 사장님
                </h3>
                <p
                  style={{
                    marginTop: '0.5rem',
                    fontSize: '0.95rem',
                    color: '#CCCCCC',
                  }}
                >
                  창업 예정인데 지역/업종
                  <br />
                  추천 받고 싶어요
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: 설문 폼 */}
      {selectedRole === 'owner' && (
        <section
          ref={ownerRef}
          style={{
            position: 'relative',
            height: 'calc(var(--vh, 1vh) * 100)',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            padding: '12rem 2rem',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-start',
            overflow: 'hidden',
          }}
        >
          {/* 배경 이미지 위에 반투명 오버레이 */}
          <div
            style={{
              backgroundImage: `url(${section2bg})`,
              backgroundSize: 'cover',
              backgroundPosition: 'top',
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              opacity: 0.3, // 이미지 투명도
              zIndex: 0,
            }}
          />

          {/* 질문 내용 박스 */}
          <div
            style={{
              position: 'relative',
              zIndex: 1,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              borderRadius: '20px',
              padding: '5rem',
              maxWidth: '700px',
              width: '100%',
              color: '#fff',
            }}
          >
            <h3
              style={{
                textAlign: 'center',
                fontSize: '1.5rem',
                marginBottom: '2rem',
              }}
            >
              현재 사업 중인 업종이 무엇인가요?
            </h3>

            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '1rem',
                marginBottom: '2rem',
              }}
            >
              {/* 대분류 선택 */}
              <Select
                options={industryMainOptions}
                placeholder="대분류 업종 선택"
                value={mainIndustry}
                onChange={(selected) => {
                  setMainIndustry(selected)
                  setSubIndustry(null) // 소분류 초기화
                }}
                styles={{
                  container: (base) => ({ ...base, width: '200px' }),
                  control: (base) => ({
                    ...base,
                    borderRadius: '5px',
                    textAlign: 'left',
                  }),
                  menu: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                  option: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                }}
              />

              {/* 소분류 선택 */}
              <Select
                options={subIndustryOptions}
                placeholder="소분류 업종 선택"
                value={subIndustry}
                onChange={(selected) => setSubIndustry(selected)}
                isDisabled={!mainIndustry}
                styles={{
                  container: (base) => ({ ...base, width: '200px' }),
                  control: (base) => ({
                    ...base,
                    borderRadius: '5px',
                    textAlign: 'left',
                  }),
                  menu: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                  option: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                }}
              />
            </div>
            <h3
              style={{
                textAlign: 'center',
                fontSize: '1.5rem',
                marginBottom: '2rem',
                marginTop: '3rem',
              }}
            >
              현재 월 평균 매출이 얼마인가요?
            </h3>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
              }}
            >
              <input
                type="text"
                placeholder="예: 200,000 (단위 : 만원)"
                value={formattedMonthlySales}
                onChange={handleMonthlySalesChange}
                style={{
                  borderRadius: '5px',
                  padding: '0.6rem 1rem',
                  fontSize: '1rem',
                  border: '1px solid #ccc',
                  width: '250px',
                }}
              />
              <span
                style={{ fontSize: '1rem', fontWeight: 'bold', color: 'white' }}
              >
                만원
              </span>
            </div>

            <h3
              style={{
                textAlign: 'center',
                fontSize: '1.5rem',
                marginBottom: '1rem',
                marginTop: '3rem',
              }}
            >
              이용 목적은 무엇인가요?
            </h3>

            <div
              style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}
            >
              <button
                onClick={() => setPurpose('market')}
                style={{
                  backgroundColor:
                    purpose === 'market' ? '#262f95ff' : '#726EFF',
                  color: 'white',
                  padding: '0.8rem 1.5rem',
                  borderRadius: '12px',
                  border: 'none',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                단순 시장 조사
              </button>
              <button
                onClick={() => setPurpose('expand')}
                style={{
                  backgroundColor:
                    purpose === 'expand' ? '#262f95ff' : '#726EFF',
                  color: 'white',
                  padding: '0.8rem 1.5rem',
                  borderRadius: '12px',
                  border: 'none',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                }}
              >
                동일 업종 확장
              </button>
            </div>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                style={{
                  backgroundColor: '#726EFF',
                  color: 'white',
                  padding: '1rem 2rem',
                  borderRadius: '12px',
                  fontWeight: 'bold',
                  border: 'none',
                  cursor: 'pointer',
                  marginTop: '3rem',
                }}
                onClick={() => {
                  if (!mainIndustry) {
                    alert('대분류 업종을 선택해주세요!')
                    return
                  }
                  if (!subIndustry) {
                    alert('소분류 업종을 선택해주세요!')
                    return
                  }
                  if (!rawMonthlySales || Number(rawMonthlySales) <= 0) {
                    alert('월 평균 매출을 입력해주세요!')
                    return
                  }
                  if (!purpose) {
                    alert('이용 목적을 선택해주세요!')
                    return
                  }
                  if (
                    !selectedDistrict ||
                    !selectedDistrict.label ||
                    !selectedDistrict.value
                  ) {
                    alert('지역을 선택해주세요!')
                    return
                  }

                  const dongRegex = /.+구\s.+동$/
                  const isDongUnit = dongRegex.test(
                    selectedDistrict.label || ''
                  )

                  if (!isDongUnit) {
                    alert(
                      '선택한 지역이 너무 넓어 지역 추천 페이지로 이동합니다.'
                    )
                    navigate('/recommend/area', {
                      state: {
                        role: 'owner',
                        selectedDistrict,
                        mainIndustry: mainIndustry.label,
                        subIndustry: subIndustry.label,
                        rawMonthlySales,
                        purpose,
                      },
                    })
                    return
                  }

                  navigate('/report', {
                    state: {
                      role: 'owner',
                      selectedDistrict,
                      mainIndustry: mainIndustry.label,
                      subIndustry: subIndustry.label,
                      rawMonthlySales,
                      purpose,
                    },
                  })
                }}
              >
                리포트 받으러 가기
              </button>
            </div>
          </div>
        </section>
      )}

      {/* Section 3: 예비 사장님 설문 폼 */}
      {selectedRole === 'preOwner' && (
        <section
          ref={preOwnerRef}
          style={{
            position: 'relative',
            height: 'calc(var(--vh, 1vh) * 100)',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            padding: '12rem 2rem',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-start',
            overflow: 'hidden',
          }}
        >
          {/* 반투명한 배경 이미지 레이어 */}
          <div
            style={{
              backgroundImage: `url(${section3bg})`,
              backgroundSize: 'cover',
              backgroundPosition: 'top',
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              opacity: 0.3,
              zIndex: 0,
            }}
          />

          {/* 질문 박스 */}
          <div
            style={{
              position: 'relative',
              zIndex: 1,
              backgroundColor: 'rgba(0, 0, 0, 0.7)', // 더 어두운 배경
              borderRadius: '20px',
              padding: '5rem',
              maxWidth: '700px',
              width: '100%',
              color: '#fff',
            }}
          >
            <h3
              style={{
                textAlign: 'center',
                fontSize: '1.5rem',
                marginBottom: '1rem',
                color: '#fff',
              }}
            >
              생각하신 업종이 있으신가요?
            </h3>
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '1rem',
                marginBottom: '1rem',
              }}
            >
              {/* 대분류 선택 */}
              <Select
                options={industryMainOptions}
                placeholder="대분류 업종 선택"
                value={mainIndustry}
                onChange={(selected) => {
                  setMainIndustry(selected)
                  setSubIndustry(null) // 소분류 초기화
                }}
                styles={{
                  container: (base) => ({ ...base, width: '200px' }),
                  control: (base) => ({
                    ...base,
                    borderRadius: '5px',
                    textAlign: 'left',
                  }),
                  menu: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                  option: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                }}
              />

              {/* 소분류 선택 */}
              <Select
                options={subIndustryOptions}
                placeholder="소분류 업종 선택"
                value={subIndustry}
                onChange={(selected) => setSubIndustry(selected)}
                isDisabled={!mainIndustry}
                styles={{
                  container: (base) => ({ ...base, width: '200px' }),
                  control: (base) => ({
                    ...base,
                    borderRadius: '5px',
                    textAlign: 'left',
                  }),
                  menu: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                  option: (base) => ({
                    ...base,
                    color: 'black',
                    textAlign: 'left',
                  }),
                }}
              />
            </div>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                style={{
                  backgroundColor: '#726EFF',
                  color: 'white',
                  padding: '1rem 2rem',
                  borderRadius: '12px',
                  fontWeight: 'bold',
                  border: 'none',
                  cursor: 'pointer',
                  marginTop: '0.5rem',
                }}
                onClick={async () => {
                  if (!mainIndustry) {
                    alert('대분류 업종을 선택해주세요!')
                    return
                  }
                  if (!subIndustry) {
                    alert('소분류 업종을 선택해주세요!')
                    return
                  }

                  const districtLabel = selectedDistrict?.label || ''
                  const dongRegex = /.+구\s.+동$/
                  const isDongUnit = dongRegex.test(districtLabel)

                  if (!isDongUnit) {
                    alert(
                      '선택한 지역이 너무 넓어 지역 추천 페이지로 이동합니다.'
                    )
                    // ✅ 구 or 시 단위일 때 → 지역 추천 백엔드 요청
                    try {
                      const response = await fetch(
                        'http://localhost:5001/api/recommend/area',
                        {
                          method: 'POST',
                          headers: {
                            'Content-Type': 'application/json',
                          },
                          body: JSON.stringify({
                            industry: subIndustry.label, // 또는 mainIndustry.label (원하는 기준에 따라)
                          }),
                        }
                      )

                      if (!response.ok) {
                        throw new Error('추천 요청 실패')
                      }

                      const data = await response.json()

                      navigate('/recommend/area', {
                        state: {
                          role: 'preOwner',
                          selectedDistrict,
                          industry: subIndustry.label,
                          recommendations: data.recommendations,
                        },
                      })
                    } catch (err) {
                      console.error(err)
                      alert('추천 요청 중 오류가 발생했습니다.')
                    }
                    return
                  }

                  // ✅ 동 단위라면 report 페이지로 이동
                  navigate('/report')
                }}
              >
                리포트 받으러 가기
              </button>
            </div>
            <h3
              style={{
                textAlign: 'center',
                fontSize: '1.5rem',
                marginBottom: '1rem',
                marginTop: '4rem',
                color: '#fff',
              }}
            >
              생각하신 업종이 없으시다면?
            </h3>
            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <button
                style={{
                  backgroundColor: '#726EFF',
                  color: 'white',
                  padding: '1rem 2rem',
                  borderRadius: '12px',
                  fontWeight: 'bold',
                  border: 'none',
                  cursor: 'pointer',
                }}
                onClick={async () => {
                  if (
                    !selectedDistrict ||
                    !selectedDistrict.label ||
                    !selectedDistrict.value
                  ) {
                    alert('지역을 먼저 선택해주세요!')
                    return
                  }

                  const isDongLevel = selectedDistrict.label?.endsWith('동')
                  if (!isDongLevel) {
                    alert(
                      'AI 업종 추천은 세부 동 단위 지역을 선택한 경우에만 이용할 수 있어요.'
                    )
                    return
                  }

                  try {
                    const response = await axios.post(
                      'http://localhost:5001/api/recommend/industry',
                      {
                        district: selectedDistrict.label,
                      }
                    )

                    const recommendations = response.data.recommendations

                    navigate('/recommend/industry', {
                      state: {
                        role: '예비사장', // ✅ 역할 추가
                        district: selectedDistrict,
                        recommendations: recommendations,
                      },
                    })
                  } catch (error) {
                    console.error('추천 요청 실패:', error)
                    alert('AI 추천을 받아오는 데 실패했습니다.')
                  }
                }}
              >
                AI 업종 추천 받으러 가기
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

export default HomePage
