import { useEffect, useRef, useState } from 'react'
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
    region,             // 입력받았을 수도 있으나, 여기서는 추천된 district를 최종 선택
    category_large,
    category_small,
    rawMonthlySales,
    purpose,
  } = location.state || {}

  const [recommendations, setRecommendations] = useState([])
  const [expandedIndex, setExpandedIndex] = useState(null)
  const [selectedIndex, setSelectedIndex] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [debugPayload, setDebugPayload] = useState(null)

  // 최신 요청만 반영 (업종 페이지와 동일 패턴)
  const reqIdRef = useRef(0)

  async function fetchWithRetry(url, opts, tries = 2) {
    try {
      const res = await fetch(url, opts)
      const txt = await res.text()
      let data = {}
      try {
        data = JSON.parse(txt)
      } catch {}
      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText} ${txt}`)
      return data
    } catch (e) {
      const s = String(e)
      if (
        tries > 1 &&
        (s.includes('ERR_EMPTY_RESPONSE') ||
          s.includes('Failed to fetch') ||
          s.includes('NetworkError'))
      ) {
        return fetchWithRetry(url, opts, tries - 1)
      }
      throw e
    }
  }

  useEffect(() => {
    window.scrollTo(0, 0)
    if (!gu_name || !category_small) {
      setError('선택된 구/업종(소분류) 정보가 없습니다. 메인에서 다시 선택해 주세요.')
      setRecommendations([])
      return
    }

    const myReqId = ++reqIdRef.current
    const controller = new AbortController()
    const signal = controller.signal

    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        setExpandedIndex(null)
        setSelectedIndex(null)

        const idemKey =
          (typeof crypto !== 'undefined' && crypto.randomUUID)
            ? crypto.randomUUID()
            : `${Date.now()}-${Math.random().toString(16).slice(2)}`

        const data = await fetchWithRetry('http://localhost:5001/api/recommend/area', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Idempotency-Key': idemKey,
          },
          body: JSON.stringify({ gu_name, category_small }),
          signal,
        })

        if (myReqId !== reqIdRef.current) return
        setDebugPayload(data)

        // 다양한 스키마 대응
        let arr = []
        if (Array.isArray(data?.recommendations)) {
          arr = data.recommendations
        } else if (data && typeof data === 'object') {
          const key = category_small || Object.keys(data)[0]
          if (Array.isArray(data[key])) arr = data[key]
        }

        arr = arr.map((x) => ({
          district: (x?.district ?? x?.행정동명 ?? '').toString().trim(),
          reason: (x?.reason ?? x?.사유 ?? '').toString().trim(),
          score:
            typeof x?.score === 'number'
              ? x.score
              : typeof x?.['지역_추천점수'] === 'number'
              ? x['지역_추천점수']
              : null,
        }))

        setRecommendations(arr)
        if (arr.length === 0) setError('추천 결과가 비어 있습니다.')
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('[recommend/area] fetch error:', err)
          setError('지역 추천 요청 실패')
          setRecommendations([])
        }
      } finally {
        if (myReqId === reqIdRef.current) setLoading(false)
      }
    })()

    return () => controller.abort()
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
        paddingBottom: '5rem',
        // ✅ 오버레이가 콘텐츠 전체 높이를 기준으로 깔리도록 기준 컨테이너 지정
        position: 'relative',
      }}
    >
      {/* ✅ 콘텐츠 전체 높이에 따라 함께 늘어나는 오버레이 */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          zIndex: 0,
          pointerEvents: 'none', // 이벤트 가로채지 않도록
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
            marginBottom: '1rem',
            color: 'white',
            fontSize: '2rem',
            fontWeight: 'bold',
          }}
        >
          {`${gu_name || ''}`}에서 <span style={{ color: '#a6b0ff' }}>{category_small || '업종 없음'}</span>에 적합한 지역은?
        </h1>

        <div style={{ textAlign: 'center', marginBottom: '1rem', opacity: 0.9 }}>
          {loading ? '로딩 중...' : recommendations.length ? `총 ${recommendations.length}건` : ''}
        </div>

        {error && (
          <div style={{ textAlign: 'center', marginBottom: '1rem', color: '#ffb3b3', whiteSpace: 'pre-wrap' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {recommendations.map((rec, index) => (
            <div
              key={`${rec.district}-${index}`}
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
                {rec.district || '행정동 미상'}
              </h2>

              {expandedIndex === index ? (
                <p style={{ color: '#444' }}>{rec.reason || '사유 없음'}</p>
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
              const chosen = recommendations[selectedIndex]
              navigate('/report', {
                state: {
                  role,
                  gu_name,
                  region: chosen.district,          // ✅ 추천된 행정동을 region으로 전달
                  category_large,
                  category_small,
                  rawMonthlySales,
                  purpose,
                },
              })
            }}
            disabled={loading || recommendations.length === 0}
            style={{
              backgroundColor: '#262f95ff',
              color: 'white',
              padding: '1rem 2rem',
              borderRadius: '12px',
              fontWeight: 'bold',
              border: 'none',
              cursor: loading || recommendations.length === 0 ? 'not-allowed' : 'pointer',
              opacity: loading || recommendations.length === 0 ? 0.6 : 1,
            }}
          >
            리포트 받으러 가기
          </button>
        </div>

        {!loading && recommendations.length === 0 && debugPayload && (
          <details style={{ marginTop: '1rem', fontSize: '.85rem', color: '#ddd' }}>
            <summary>디버그: 서버 응답 보기</summary>
            <pre style={{ whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(debugPayload, null, 2)}
            </pre>
          </details>
        )}
      </div>
    </div>
  )
}

export default RecommendAreaPage
