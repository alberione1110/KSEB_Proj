import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import '../App.css'
import ksebLogo from '../img/kseb_logo.png'
import bgimg from '../img/bgimg.jpg'

function RecommendAreaPage() {
  const navigate = useNavigate()
  const location = useLocation()

  const {
    role,
    gu_name,
    region,
    category_large,
    category_small,
    rawMonthlySales,
    purpose,
  } = location.state || {}

  const [recommendations, setRecommendations] = useState([])
  const [expandedIndex, setExpandedIndex] = useState(null)
  const [selectedIndex, setSelectedIndex] = useState(null)

  useEffect(() => {
    window.scrollTo(0, 0)
    if (gu_name && category_small) {
      fetch('http://localhost:5001/api/recommend/area', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gu_name, category_small }),
      })
        .then((res) => res.json())
        .then((data) => {
          setRecommendations(data.recommendations || [])
        })
        .catch((err) => {
          console.error('추천 요청 실패:', err)
        })
    }
  }, [gu_name, category_small])

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
          {category_small || '업종 없음'}에 적합한 지역은?
        </h1>

        <div
          style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
        >
          {recommendations.map((rec, index) => (
            <div
              key={index}
              onClick={() => setSelectedIndex(index)}
              style={{
                backgroundColor: selectedIndex === index ? '#e0e7ff' : 'white',
                color: '#000',
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

        <div style={{ textAlign: 'center', marginTop: '3rem' }}>
          <button
            onClick={() => {
              if (selectedIndex === null) {
                alert('지역을 하나 선택해주세요!')
                return
              }
              const selectedFull = recommendations[selectedIndex].district
              const parts = selectedFull.split(' ')
              const selectedGu = parts[0] || ''
              const selectedDong = parts[1] || ''

              navigate('/report', {
                state: {
                  role,
                  gu_name: selectedGu,
                  region: selectedDong,
                  category_large,
                  category_small,
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
