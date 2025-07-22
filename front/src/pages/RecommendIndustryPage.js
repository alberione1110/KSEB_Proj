import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import '../App.css'
import ksebLogo from '../img/kseb_logo.png'
import bgimg2 from '../img/bgimg2.jpg'

function RecommendIndustryPage() {
  const navigate = useNavigate()
  const location = useLocation()

  const {
    role = '예비사장',
    gu_name,
    region,
  } = location.state || {}

  const [recommendations, setRecommendations] = useState([])
  const [expandedIndex, setExpandedIndex] = useState(null)
  const [selectedIndex, setSelectedIndex] = useState(null)

  useEffect(() => {
    window.scrollTo(0, 0)
    if (gu_name && region) {
      fetch('http://localhost:5001/api/recommend/industry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gu_name, region }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.recommendations) {
            setRecommendations(data.recommendations)
          } else {
            alert('추천 결과를 받아오지 못했습니다.')
          }
        })
        .catch((err) => {
          console.error(err)
          alert('추천 요청 실패')
        })
    }
  }, [gu_name, region])

  return (
    <div
      className="App"
      style={{
        fontFamily: 'sans-serif',
        minHeight: '100vh',
        backgroundImage: `url(${bgimg2})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        paddingBottom: '5rem',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
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
            onClick={() => navigate('/')}
          >
            메인으로
          </button>
        </div>
      </nav>

      <div
        style={{
          maxWidth: '800px',
          margin: '3rem auto',
          backgroundColor: 'rgba(0,0,0,0.6)',
          padding: '2rem',
          borderRadius: '20px',
          color: 'white',
          position: 'relative',
          zIndex: 1,
        }}
      >
        <h1
          style={{
            textAlign: 'center',
            marginBottom: '2rem',
            fontSize: '2rem',
            fontWeight: 'bold',
          }}
        >
          {`${gu_name || ''} ${region || ''}`}에서 추천되는 유망 업종은?
        </h1>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {recommendations.map((rec, index) => (
            <div
              key={index}
              onClick={() => setSelectedIndex(index)}
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
              style={{
                backgroundColor: selectedIndex === index ? '#a0a8ff' : 'white',
                color: 'black',
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
            >
              <h2
                style={{
                  fontSize: '1.4rem',
                  fontWeight: 'bold',
                  color: '#262f95ff',
                  marginBottom: '0.5rem',
                }}
              >
                {rec.category_small}
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
                alert('업종을 하나 선택해주세요!')
                return
              }

              navigate('/report', {
                state: {
                  role,
                  gu_name,
                  region,
                  category_large: recommendations[selectedIndex].category_large,
                  category_small: recommendations[selectedIndex].category_small,
                  rawMonthlySales: null,
                  purpose: null,
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

export default RecommendIndustryPage
