import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import '../App.css'
import ksebLogo from '../img/kseb_logo.png'
import bgimg from '../img/bgimg.jpg'

function RecommendAreaPage() {
  const navigate = useNavigate()
  const location = useLocation()

  // ✅ location.state에서 모든 값 추출
  const {
    role,
    industry,
    mainIndustry,
    subIndustry,
    rawMonthlySales,
    purpose,
    selectedDistrict: prevSelectedDistrict,
  } = location.state || {}

  const [recommendations, setRecommendations] = useState([])
  const [expandedIndex, setExpandedIndex] = useState(null)
  const [selectedIndex, setSelectedIndex] = useState(null)

  useEffect(() => {
    window.scrollTo(0, 0)
    if (industry) {
      fetch('http://localhost:5001/api/recommend/area', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ industry }),
      })
        .then((res) => res.json())
        .then((data) => {
          setRecommendations(data.recommendations || [])
        })
        .catch((err) => {
          console.error('추천 요청 실패:', err)
        })
    }
  }, [industry])

  return (
    <div
      className="App"
      style={{
        fontFamily: 'sans-serif',
        minHeight: '100vh',
        backgroundImage: `url(${bgimg})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        color: 'white',
      }}
    >
      {/* 어두운 배경 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          zIndex: 0,
        }}
      />

      {/* 네비게이션 */}
      <nav
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1rem 2rem',
          position: 'relative',
          zIndex: 1,
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
              cursor: 'pointer',
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
              cursor: 'pointer',
            }}
            onClick={() => navigate('/')}
          >
            메인으로
          </button>
        </div>
      </nav>

      {/* 콘텐츠 */}
      <div
        style={{
          padding: '4rem 2rem 2rem',
          position: 'relative',
          zIndex: 1,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          borderRadius: '20px',
          maxWidth: '900px',
          margin: '3rem auto',
        }}
      >
        <h1
          style={{
            textAlign: 'center',
            marginBottom: '2rem',
            color: 'white',
            fontSize: '2rem',
            fontWeight: 'bold',
          }}
        >
          {industry || '업종 없음'}에 적합한 지역은?
        </h1>

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1.5rem',
          }}
        >
          {recommendations.map((rec, index) => (
            <div
              key={index}
              onClick={() => setSelectedIndex(index)}
              style={{
                backgroundColor: selectedIndex === index ? '#e0e7ff' : 'white',
                color: selectedIndex === index ? '#000' : '#000',
                padding: '1.5rem',
                borderRadius: '16px',
                boxShadow:
                  selectedIndex === index
                    ? '0 4px 12px rgba(38, 47, 149, 0.3)'
                    : '0 2px 8px rgba(0, 0, 0, 0.1)',
                cursor: 'pointer',
                transform: selectedIndex === index ? 'scale(1.03)' : 'scale(1)',
                transition: 'transform 0.2s, box-shadow 0.2s',
              }}
              onMouseEnter={(e) => {
                if (selectedIndex !== index) {
                  e.currentTarget.style.transform = 'scale(1.03)'
                }
              }}
              onMouseLeave={(e) => {
                if (selectedIndex !== index) {
                  e.currentTarget.style.transform = 'scale(1)'
                }
              }}
            >
              <h2
                style={{
                  fontSize: '1.4rem',
                  fontWeight: 'bold',
                  color: '#262f95ff',
                  marginBottom: '0.5rem',
                }}
              >
                {rec.district}
              </h2>

              {expandedIndex === index ? (
                <p style={{ color: '#444' }}>{rec.reason}</p>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpandedIndex(index)
                  }}
                  style={{
                    backgroundColor: '#726EFF',
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '0.4rem 1rem',
                    cursor: 'pointer',
                  }}
                >
                  추천 이유 보기
                </button>
              )}

              {expandedIndex === index && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    setExpandedIndex(null)
                  }}
                  style={{
                    backgroundColor: 'transparent',
                    color: '#999',
                    border: 'none',
                    marginTop: '0.5rem',
                    cursor: 'pointer',
                    fontSize: '0.9rem',
                  }}
                >
                  닫기
                </button>
              )}
            </div>
          ))}
        </div>

        {/* 리포트 이동 버튼 */}
        <div style={{ textAlign: 'center', marginTop: '3rem' }}>
          <button
            onClick={() => {
              if (selectedIndex === null) {
                alert('지역을 하나 선택해주세요!')
                return
              }
              navigate('/report', {
                state: {
                  role,
                  selectedDistrict: recommendations[selectedIndex].district,
                  industry,
                  mainIndustry,
                  subIndustry,
                  rawMonthlySales,
                  purpose,
                },
              })
            }}
            style={{
              backgroundColor: '#262f95ff',
              color: 'white',
              padding: '1rem 2rem',
              borderRadius: '12px',
              fontWeight: 'bold',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            리포트 받으러 가기
          </button>
        </div>
      </div>
    </div>
  )
}

export default RecommendAreaPage
