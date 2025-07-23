import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import RecommendIndustryPage from './pages/RecommendIndustryPage'
import RecommendAreaPage from './pages/RecommendAreaPage'
import ReportPage from './pages/ReportPage'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/recommend/industry" element={<RecommendIndustryPage />} />
        <Route path="/recommend/area" element={<RecommendAreaPage />} />
        <Route path="/report" element={<ReportPage />} />
      </Routes>
    </Router>
  )
}

export default App
