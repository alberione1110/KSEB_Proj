import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import '../App.css'
import ksebLogo from '../img/kseb_logo.png'
import bgimg from '../img/bgimg.jpg'

function ReportPage() {
  const navigate = useNavigate()
  const location = useLocation()

  const {
    role,
    gu_name,
    region,
    category_large,
    category_small,
    purpose,
  } = location.state || {}

  const [report, setReport] = useState(null)

  useEffect(() => {
    window.scrollTo(0, 0)
    fetch('http://localhost:5001/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role,
        gu_name,
        region,
        category_large,
        category_small,
        purpose,
      }),
    })
      .then((res) => res.json())
      .then((data) => {
        setReport(data)
      })
      .catch((err) => {
        console.error('리포트 요청 실패:', err)
        alert('리포트를 받아오는 데 실패했습니다.')
      })
  }, [role, gu_name, region, category_large, category_small, purpose])

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
          padding: '4rem 2rem',
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
          상권 분석 결과 리포트
        </h1>
        {report ? (
          <>
            <p style={{ marginTop: '0.5rem' }}>{report.summary}</p>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>기본 지역 정보</h2>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>상권 변화</h2>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>생존율 및 영업 기간</h2>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>개폐업 추이 및 진입 위험도</h2>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>인구 및 유동 인구 특성</h2>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>임대료 수준</h2>
            <h2 style={{ color: '#A5B4FC', fontWeight: 'bold', marginTop: '2rem' }}>매출 특성 요약</h2>
          </>
        ) : (
          <p>리포트를 불러오는 중입니다...</p>
        )}

        <div style={{ textAlign: 'center', marginTop: '3rem' }}>
          <button
            onClick={() => navigate('/chatbot')}
            style={{
              backgroundColor: '#4F46E5',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              padding: '0.75rem 1.5rem',
              fontSize: '1rem',
              fontWeight: 'bold',
              cursor: 'pointer',
            }}
          >
            챗봇으로 자세한 컨설팅 받아보기
          </button>
        </div>
      </div>
    </div>
  )
}

export default ReportPage
