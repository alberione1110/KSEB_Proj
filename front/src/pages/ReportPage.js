// ReportPage.jsx
import { useEffect, useState, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import '../App.css'
import ksebLogo from '../img/kseb_logo.png'
import bgimg3 from '../img/bgimg3.jpeg'

function ChatbotPanel() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      content: '안녕하세요! 무엇을 도와드릴까요?',
    },
  ])
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)
  const [isComposing, setIsComposing] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = {
      role: 'user',
      content: input.trim(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')

    try {
      const res = await fetch('http://localhost:5001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [...messages, userMessage] }),
      })

      const data = await res.json()
      setMessages((prev) => [...prev, { role: 'bot', content: data.response }])
    } catch (err) {
      console.error('챗봇 응답 실패:', err)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '1rem', color: 'black' }}>
        챗봇 상담
      </h2>
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem',
        }}
      >
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor:
                msg.role === 'user' ? '#6366F1' : 'rgba(240,240,240,0.7)',
              color: msg.role === 'user' ? 'white' : 'black',
              padding: '0.75rem 1rem',
              borderRadius: '1rem',
              maxWidth: '100%',
              wordBreak: 'break-word',
              fontSize: '0.95rem',
              lineHeight: 1.5,
            }}
          >
            {msg.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div
        style={{
          display: 'flex',
          padding: '1rem',
          gap: '0.5rem',
          borderTop: '1px solid rgba(0, 0, 0, 0.1)',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="메시지를 입력하세요"
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !isComposing) {
              e.preventDefault()
              sendMessage()
            }
          }}
          style={{
            flex: 1,
            padding: '0.75rem',
            borderRadius: '10px',
            border: 'none',
            fontSize: '1rem',
          }}
        />
        <button
          onClick={sendMessage}
          style={{
            backgroundColor: '#6366F1',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            padding: '0 1rem',
            fontWeight: 'bold',
            fontSize: '1rem',
            cursor: 'pointer',
          }}
        >
          보내기
        </button>
      </div>
    </div>
  )
}

function ReportPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { role, gu_name, region, category_large, category_small, purpose } =
    location.state || {}
  const [report, setReport] = useState(null)
  const [showChatbot, setShowChatbot] = useState(false)

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
      .then((data) => setReport(data))
      .catch((err) => {
        console.error('리포트 요청 실패:', err)
        alert('리포트를 받아오는 데 실패했습니다.')
      })
  }, [role, gu_name, region, category_large, category_small, purpose])

  const reportCardStyle = {
    width: '100%',
    maxWidth: '900px',
    height: '90vh',
    minHeight: '700px',
    backgroundColor: 'rgba(255, 255, 255, 1)',
    borderRadius: '20px',
    padding: '2.5rem',
    overflowY: 'auto',
    boxShadow: '0 0 20px rgba(0,0,0,0.3)',
    boxSizing: 'border-box',
    display: 'flex',
    flexDirection: 'column',
    color: 'black',
    textAlign:'left'
  }

  const chatbotCardStyle = {
    width: '100%',
    maxWidth: '600px',
    height: '90vh',
    backgroundColor: 'rgba(255,255,255,0.6)',
    borderRadius: '20px',
    padding: '2rem',
    overflow: 'hidden',
    boxShadow: '0 0 20px rgba(0,0,0,0.3)',
    boxSizing: 'border-box',
    display: 'flex',
    flexDirection: 'column',
    color: 'black',
  }

  return (
    <div
      className="App"
      style={{
        fontFamily: 'sans-serif',
        minHeight: '100vh',
        backgroundImage: `url(${bgimg3})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        backgroundAttachment: 'fixed',
        color: 'white',
      }}
    >
      <nav
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
      </nav>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          alignItems: 'flex-start',
          gap: '3rem',
          padding: '2rem 1rem 4rem',
          maxWidth: '1800px',
          margin: '0 auto',
        }}
      >
        <div style={reportCardStyle}>
          <h1
            style={{
              textAlign: 'center',
              marginBottom: '1rem',
              fontSize: '2rem',
              fontWeight: 'bold',
            }}
          >
            상권 분석 결과 리포트
          </h1>
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {report ? (
              <>
                <p>{report.summary}</p>
                <h2 style={{ marginTop: '2rem' }}>기본 지역 정보</h2>
                <h2 style={{ marginTop: '2rem' }}>상권 변화</h2>
                <h2 style={{ marginTop: '2rem' }}>생존율 및 영업 기간</h2>
                <h2 style={{ marginTop: '2rem' }}>
                  개폐업 추이 및 진입 위험도
                </h2>
                <h2 style={{ marginTop: '2rem' }}>
                  인구 및 유동 인구 특성
                </h2>
                <h2 style={{ marginTop: '2rem' }}>임대료 수준</h2>
                <h2 style={{ marginTop: '2rem' }}>매출 특성 요약</h2>
              </>
            ) : (
              <p>리포트를 불러오는 중입니다...</p>
            )}
          </div>
          {!showChatbot && (
            <div style={{ textAlign: 'center', marginTop: '2rem' }}>
              <button
                onClick={() => setShowChatbot(true)}
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
          )}
        </div>

        {showChatbot && <div style={chatbotCardStyle}><ChatbotPanel /></div>}
      </div>
    </div>
  )
}

export default ReportPage
