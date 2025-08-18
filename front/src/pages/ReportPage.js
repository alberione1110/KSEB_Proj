// ReportPage.jsx
import React, { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import * as echarts from 'echarts';
import '../App.css';
import ksebLogo from '../img/kseb_logo.png';
import bgimg3 from '../img/bgimg3.jpeg'; // 프로젝트에 실제 존재하는 확장자로 맞춰주세요 (.jpeg이면 경로 수정)

function ChatbotPanel() {
  const [messages, setMessages] = useState([{ role: 'bot', content: '안녕하세요! 무엇을 도와드릴까요?' }]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);
  const [isComposing, setIsComposing] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMessage = { role: 'user', content: input.trim() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    try {
      const res = await fetch('http://localhost:5001/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [...messages, userMessage] }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'bot', content: data.response }]);
    } catch (err) {
      console.error('챗봇 응답 실패:', err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '1rem', color: 'black' }}>챗봇 상담</h2>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: msg.role === 'user' ? '#6366F1' : 'rgba(240,240,240,0.7)',
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
      <div style={{ display: 'flex', padding: '1rem', gap: '0.5rem', borderTop: '1px solid rgba(0, 0, 0, 0.1)' }}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="메시지를 입력하세요"
          onCompositionStart={() => setIsComposing(true)}
          onCompositionEnd={() => setIsComposing(false)}
          onKeyDown={e => {
            if (e.key === 'Enter' && !isComposing) {
              e.preventDefault();
              sendMessage();
            }
          }}
          style={{ flex: 1, padding: '0.75rem', borderRadius: '10px', border: 'none', fontSize: '1rem' }}
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
  );
}

function ReportPage() {
  const navigate = useNavigate();
  const location = useLocation();

  // state 우선, 없으면 쿼리스트링 사용
  const qs = new URLSearchParams(location.search);
  const state = location.state || {};
  const role = state.role ?? qs.get('role') ?? '';
  const gu_name = state.gu_name ?? qs.get('gu_name') ?? '';
  const region = state.region ?? qs.get('region') ?? '';
  const category_large = state.category_large ?? qs.get('category_large') ?? '';
  const category_small = state.category_small ?? qs.get('category_small') ?? '';
  let purposeRaw = state.purpose ?? qs.get('purpose') ?? '';

  // purpose 정규화 + 기본값
  const normalizePurpose = (p) => {
    if (!p) return '창업 준비';
    const t = String(p).trim().replace(/\s+/g, '');
    if (['창업', '창업준비', '창업진입'].includes(t)) return '창업 준비';
    if (['확장', '브랜드확장', '가맹확장'].includes(t)) return '확장';
    if (['시장조사', '리서치', '시장분석'].includes(t)) return '시장조사';
    return String(p).trim();
  };
  const purpose = normalizePurpose(purposeRaw);

  const [report, setReport] = useState(null);
  const [showChatbot, setShowChatbot] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);

    const missing = [];
    if (!region) missing.push('region');
    if (!gu_name) missing.push('gu_name');
    if (!category_small) missing.push('category_small');
    if (!purpose) missing.push('purpose');

    if (missing.length) {
      console.warn('필수 파라미터 누락:', missing);
      alert(`필수 항목 누락: ${missing.join(', ')}\nURL 쿼리 또는 이전 화면에서 값을 전달해 주세요.`);
      return;
    }

    fetch('http://localhost:5001/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, gu_name, region, category_large, category_small, purpose }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.ok === false) {
          const msg = data?.detail || data?.error || `HTTP ${res.status}`;
          throw new Error(msg);
        }
        return data;
      })
      .then((data) => {
        setReport(data); // { sections, chart_data, zone_ids, zone_texts, ... }
      })
      .catch((err) => {
        console.error('리포트 요청 실패:', err);
        alert(`리포트를 받아오는 데 실패했습니다.\n원인: ${err.message}`);
      });
  }, [role, gu_name, region, category_large, category_small, purpose]);

  useEffect(() => {
    if (report) drawCharts(report);
    return () => {
      // 차트 메모리 해제
      const nodes = document.querySelectorAll('[id$="_chart"], [id^="sales_"]');
      nodes.forEach(n => {
        const inst = echarts.getInstanceByDom(n);
        if (inst) inst.dispose();
      });
    };
  }, [report]);

  const drawCharts = (data) => {
    const chartData = data.chart_data || {};
    const zoneIds = (data.zone_ids || []).map(String);

    const renderBar = (id, labels, values, title, unit = '') => {
      const el = document.getElementById(id);
      if (!el || !labels || !values) return;
      const chart = echarts.init(el);
      chart.setOption({
        title: { text: title, left: 'center' },
        tooltip: {
          trigger: 'axis',
          valueFormatter: v => (unit === '%' ? `${v}${unit}` : `${Number(v).toLocaleString()}${unit}`),
        },
        xAxis: { type: 'category', data: labels, axisLabel: { interval: 0 } },
        yAxis: {
          type: 'value',
          axisLabel: {
            formatter: v => (unit === '%' ? `${v}${unit}` : `${Number(v).toLocaleString()}${unit}`),
          },
        },
        series: [{ type: 'bar', data: values }],
      });
    };

    const renderLine = (id, labels, values, title, unit = '') => {
      const el = document.getElementById(id);
      if (!el || !labels || !values) return;
      const chart = echarts.init(el);
      chart.setOption({
        title: { text: title, left: 'center' },
        tooltip: {
          trigger: 'axis',
          valueFormatter: v => (unit ? `${Number(v).toLocaleString()}${unit}` : Number(v).toLocaleString()),
        },
        xAxis: { type: 'category', data: labels },
        yAxis: { type: 'value' },
        series: [{ type: 'line', data: values }],
      });
    };

    const renderPie = (id, labels, values, title) => {
      const el = document.getElementById(id);
      if (!el || !labels || !values) return;
      const chart = echarts.init(el);
      chart.setOption({
        title: { text: title, left: 'center' },
        tooltip: { trigger: 'item' },
        legend: { bottom: 0 },
        series: [
          {
            type: 'pie',
            radius: '50%',
            data: labels.map((l, i) => ({ name: l, value: values[i] })),
          },
        ],
      });
    };

    // 공통 차트
    if (chartData.store_yearly)
      renderLine('store_yearly_chart', chartData.store_yearly.labels, chartData.store_yearly.values, '연도별 점포 수 변화');

    if (chartData.survival)
      renderBar('survival_chart', chartData.survival.labels, chartData.survival.values, '신생기업 생존율', '%');

    if (chartData.operating_period)
      renderBar('operating_period_chart', chartData.operating_period.labels, chartData.operating_period.values, '평균 영업 기간', '년');

    if (chartData.floating)
      renderLine('floating_chart', chartData.floating.labels, chartData.floating.values, '유동인구 추이', '명');

    if (chartData.open_close) {
      const el = document.getElementById('open_close_chart');
      if (el) {
        const chart = echarts.init(el);
        chart.setOption({
          title: { text: '연도별 개폐업 수 추이', left: 'center' },
          tooltip: { trigger: 'axis' },
          legend: { data: ['개업', '폐업'], top: 30 },
          xAxis: { type: 'category', data: chartData.open_close.labels },
          yAxis: { type: 'value' },
          series: [
            { name: '개업', type: 'line', data: chartData.open_close.open },
            { name: '폐업', type: 'line', data: chartData.open_close.close },
          ],
        });
      }
    }

    if (chartData.rent)
      renderBar('rent_chart', chartData.rent.labels, chartData.rent.values, '3.3㎡당 임대료 수준', '원');

    // zone 차트
    if (chartData.sales) {
      zoneIds.forEach((zoneId) => {
        const z = chartData.sales[zoneId];
        if (!z) return;
        renderBar(`sales_day_${zoneId}`, z.sales_by_day.labels, z.sales_by_day.values, '요일별 평균 매출', '원');
        renderBar(`sales_hour_${zoneId}`, z.sales_by_hour.labels, z.sales_by_hour.values, '시간대별 평균 매출', '원');
        renderPie(`sales_gender_${zoneId}`, z.sales_by_gender.labels, z.sales_by_gender.values, '성별 매출');
        renderBar(`sales_age_${zoneId}`, z.sales_by_age_group.labels, z.sales_by_age_group.values, '연령대별 매출', '원');
        renderPie(`sales_weekday_vs_weekend_${zoneId}`, z.weekday_vs_weekend.labels, z.weekday_vs_weekend.values, '평일 vs 주말 매출');
        renderBar(`sales_avg_price_${zoneId}`, z.avg_price_per_order.labels, z.avg_price_per_order.values, '객단가', '원');
      });
    }
  };

  // 본문 스타일
  const baseParagraph = {
    margin: '6px 0',
    color: '#444',
    lineHeight: 1.8,
    textAlign: 'justify',
    textJustify: 'inter-word',
    whiteSpace: 'pre-wrap',
  };

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
    textAlign: 'left',
  };

  const getChartIdFromTitle = (title) => {
    if (title.includes('상권 변화')) return 'store_yearly_chart';
    if (title.includes('생존율')) return 'survival_chart';
    if (title.includes('임대료')) return 'rent_chart';
    if (title.includes('개폐업')) return 'open_close_chart';
    if (title.includes('유동 인구') || title.includes('유동인구')) return 'floating_chart';
    return '';
  };

  const summarySection = report?.sections?.find(s => s.title.includes('👉') || s.title.includes('종합 평가'));
  const otherSections = (report?.sections || []).filter(s => !(s.title.includes('👉') || s.title.includes('종합 평가')));

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
      <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem 2rem', position: 'relative', zIndex: 2 }}>
        <img src={ksebLogo} alt="KSEB Logo" style={{ width: '100px' }} />
        <button
          style={{ backgroundColor: 'transparent', border: '1px solid white', borderRadius: '8px', padding: '0.5rem 1rem', color: 'white', cursor: 'pointer' }}
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
          <h1 style={{ textAlign: 'center', fontSize: '2rem', fontWeight: 'bold' }}>상권 분석 결과 리포트</h1>

          {!report ? (
            <p style={baseParagraph}>리포트를 불러오는 중입니다...</p>
          ) : (
            <>
              {summarySection && (
                <div style={{ backgroundColor: '#fff9e6', border: '2px solid #f1c40f', borderRadius: 8, padding: 20, marginTop: 30 }}>
                  <h2 style={{ color: '#d35400', marginTop: 0, textAlign: 'left' }}>{summarySection.title}</h2>
                  <div>
                    {summarySection.content.split('\n').map((line, i) => {
                      const trimmed = line.trim();
                      const isBullet = trimmed.startsWith('•') || trimmed.startsWith('-');
                      return (
                        <p key={i} style={{ ...baseParagraph, textAlign: 'left', color: '#333' }}>
                          {isBullet ? <span style={{ color: '#e67e22', fontWeight: 'bold', marginRight: 6 }}>•</span> : null}
                          {isBullet ? trimmed.replace(/^[-•]\s?/, '') : trimmed}
                        </p>
                      );
                    })}
                  </div>
                </div>
              )}

              {otherSections
                .filter(sec => !sec.title.includes('매출'))
                .map((section, idx) => (
                  <div key={idx} style={{ marginBottom: '2rem' }}>
                    <h2 style={{ fontSize: '1.3rem', marginBottom: '0.5rem', color: '#2c3e50', textAlign: 'left' }}>{section.title}</h2>
                    <p style={baseParagraph}>{section.content}</p>
                    {getChartIdFromTitle(section.title) && (
                      <div id={getChartIdFromTitle(section.title)} style={{ width: '100%', height: '400px', marginTop: 10 }} />
                    )}
                  </div>
                ))}

              {(report.sections || [])
                .filter(sec => sec.title.includes('매출'))
                .map((section, idx) => (
                  <div key={`sales-sec-${idx}`} style={{ margin: '2rem 0' }}>
                    <h2 style={{ fontSize: '1.3rem', marginBottom: '0.5rem', color: '#2c3e50', textAlign: 'left' }}>{section.title}</h2>
                    <p style={baseParagraph}>{section.content}</p>
                  </div>
                ))}

              {(report.zone_ids || []).map((zoneId) => {
                const zid = String(zoneId);
                const zname = report.chart_data?.zone_names?.[zid];
                const ztext = (report.zone_texts?.[zid] || '').split('\n').filter(Boolean);
                return (
                  <div key={zid} style={{ marginBottom: 50, padding: 20, border: '2px solid #e0e0e0', borderRadius: 10, backgroundColor: '#fafafa' }}>
                    <h3 style={{ marginBottom: 20, fontSize: 20, color: '#34495e', textAlign: 'left' }}>{zname || `Zone ${zid}`}</h3>

                    <div>
                      {ztext.map((line, i) => (
                        <p key={i} style={{ ...baseParagraph, color: '#333' }}>{line}</p>
                      ))}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20, marginTop: 10 }}>
                      <div id={`sales_day_${zid}`} style={{ width: '100%', height: 400, background: '#f8f9fa', border: '1px solid #ddd', borderRadius: 10 }} />
                      <div id={`sales_hour_${zid}`} style={{ width: '100%', height: 400, background: '#f8f9fa', border: '1px solid #ddd', borderRadius: 10 }} />
                      <div id={`sales_gender_${zid}`} style={{ width: '100%', height: 400, background: '#f8f9fa', border: '1px solid #ddd', borderRadius: 10 }} />
                      <div id={`sales_age_${zid}`} style={{ width: '100%', height: 400, background: '#f8f9fa', border: '1px solid #ddd', borderRadius: 10 }} />
                      <div id={`sales_weekday_vs_weekend_${zid}`} style={{ width: '100%', height: 400, background: '#f8f9fa', border: '1px solid #ddd', borderRadius: 10 }} />
                      <div id={`sales_avg_price_${zid}`} style={{ width: '100%', height: 400, background: '#f8f9fa', border: '1px solid #ddd', borderRadius: 10 }} />
                    </div>
                  </div>
                );
              })}
            </>
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
  );
}

export default ReportPage;
