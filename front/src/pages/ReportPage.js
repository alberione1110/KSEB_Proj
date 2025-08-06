// ReportPage.jsx
import React, { useEffect, useState, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import * as echarts from 'echarts'
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
      .then((data) => {
        setReport(data)
      })
      .catch((err) => {
        console.error('리포트 요청 실패:', err)
        alert('리포트를 받아오는 데 실패했습니다.')
      })
  }, [role, gu_name, region, category_large, category_small, purpose])

  useEffect(() => {
    if (report) {
      drawCharts()
    }
  }, [report])

  // ✅ 차트 렌더 함수 (간단화 버전)
  const drawCharts = () => {
    const chartData = report.chart_data
    const zoneIds = report.zone_ids.map(String)

    const renderBar = (id, labels, values, title, unit = '') => {
      const el = document.getElementById(id)
      if (!el) return
      const chart = echarts.init(el)
      chart.setOption({
        title: { text: title, left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: labels },
        yAxis: { type: 'value' },
        series: [{ type: 'bar', data: values }],
      })
    }

    const renderLine = (id, labels, values, title) => {
      const el = document.getElementById(id)
      if (!el) return
      const chart = echarts.init(el)
      chart.setOption({
        title: { text: title, left: 'center' },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: labels },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: values }],
      })
    }

    const renderPie = (id, labels, values, title) => {
      const el = document.getElementById(id)
      if (!el) return
      const chart = echarts.init(el)
      chart.setOption({
        title: { text: title, left: 'center' },
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie',
          radius: '50%',
          data: labels.map((l, i) => ({ name: l, value: values[i] })),
        }],
      })
    }

    // 기본 차트
    if (chartData?.store_yearly)
      renderLine('store_yearly_chart', chartData.store_yearly.labels, chartData.store_yearly.values, '연도별 점포 수 변화')

    if (chartData?.survival)
      renderBar('survival_chart', chartData.survival.labels, chartData.survival.values, '생존율', '%')

    if (chartData?.rent)
      renderBar('rent_chart', chartData.rent.labels, chartData.rent.values, '임대료', '원')

    if (chartData?.open_close)
      renderLine('open_close_chart', chartData.open_close.labels, chartData.open_close.open, '개업 수')

    // zone별 차트
    if (chartData?.sales) {
      zoneIds.forEach(zoneId => {
        const zone = chartData.sales[zoneId]
        if (!zone) return
        renderBar(`sales_day_${zoneId}`, zone.sales_by_day.labels, zone.sales_by_day.values, '요일별 매출')
        renderBar(`sales_hour_${zoneId}`, zone.sales_by_hour.labels, zone.sales_by_hour.values, '시간대별 매출')
        renderPie(`sales_gender_${zoneId}`, zone.sales_by_gender.labels, zone.sales_by_gender.values, '성별 매출')
        renderBar(`sales_age_${zoneId}`, zone.sales_by_age_group.labels, zone.sales_by_age_group.values, '연령별 매출')
      })
    }
  }

  const reportCardStyle = {
    width: '100%',
    maxWidth: '1000px',
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
          <h1 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: 'bold' }}>
            상권 분석 결과 리포트
          </h1>
          {report ? (
            <>
              <p style={{ marginBottom: '2rem', color: '#444' }}>{report.summary}</p>
              {report.sections.map((section, idx) => (
                <div key={idx} style={{ marginBottom: '2rem' }}>
                  <h2 style={{ fontSize: '1.3rem', marginBottom: '0.5rem' }}>{section.title}</h2>
                  <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{section.content}</p>
                  <div id={getChartIdFromTitle(section.title)} style={{ width: '100%', height: '400px' }} />
                </div>
              ))}
              <h2 style={{ marginTop: '3rem' }}>📈 매출 특성 요약</h2>
              {report.zone_ids.map((zoneId) => (
                <div key={zoneId} style={{ marginBottom: '3rem' }}>
                  <h3>📍 Zone ID: {zoneId}</h3>
                  <div id={`sales_day_${zoneId}`} style={{ width: '100%', height: '300px' }} />
                  <div id={`sales_hour_${zoneId}`} style={{ width: '100%', height: '300px' }} />
                  <div id={`sales_gender_${zoneId}`} style={{ width: '100%', height: '300px' }} />
                  <div id={`sales_age_${zoneId}`} style={{ width: '100%', height: '300px' }} />
                </div>
              ))}
            </>
          ) : (
            <p>리포트를 불러오는 중입니다...</p>
          )}
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

        {showChatbot && (
          <div
            style={{
              width: '100%',
              maxWidth: '600px',
              height: '90vh',
              backgroundColor: 'rgba(255,255,255,0.6)',
              borderRadius: '20px',
              padding: '2rem',
              overflow: 'hidden',
              boxShadow: '0 0 20px rgba(0,0,0,0.3)',
              display: 'flex',
              flexDirection: 'column',
              color: 'black',
            }}
          >
            <ChatbotPanel />
          </div>
        )}
      </div>
    </div>
  )
}

// 섹션 제목에 따라 고유 차트 id 반환
function getChartIdFromTitle(title) {
  if (title.includes('상권 변화')) return 'store_yearly_chart'
  if (title.includes('생존율')) return 'survival_chart'
  if (title.includes('임대료')) return 'rent_chart'
  if (title.includes('개폐업')) return 'open_close_chart'
  return ''
}

export default ReportPage
