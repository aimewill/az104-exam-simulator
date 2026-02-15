import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import ImportWizard from './pages/ImportWizard'
import ExamSession from './pages/ExamSession'
import Results from './pages/Results'
import StudySession from './pages/StudySession'
import Login from './pages/Login'
import Register from './pages/Register'
import { importApi } from './api/client'
import { AuthProvider, useAuth } from './context/AuthContext'

function AppContent() {
  const [needsImport, setNeedsImport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme')
    return saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)
  })
  const navigate = useNavigate()
  const { user, isAuthenticated, logout, loading: authLoading } = useAuth()

  useEffect(() => {
    checkImportStatus()
  }, [])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
    localStorage.setItem('theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  const toggleTheme = () => setDarkMode(!darkMode)

  const checkImportStatus = async () => {
    try {
      const status = await importApi.getStatus()
      setNeedsImport(status.needs_import)
      if (status.needs_import) {
        navigate('/import')
      }
    } catch (err) {
      console.error('Failed to check import status:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading || authLoading) {
    return (
      <div className="loading">
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>AZ-104 Exam Simulator</h1>
          <nav className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/import">Import</Link>
            {isAuthenticated ? (
              <>
                <span className="user-info" title={user.email}>
                  👤 {user.display_name}
                </span>
                <button className="nav-button" onClick={logout}>
                  Sign Out
                </button>
              </>
            ) : (
              <Link to="/login" className="nav-button">
                Sign In
              </Link>
            )}
            <button className="theme-toggle" onClick={toggleTheme} title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
              {darkMode ? '☀️' : '🌙'}
            </button>
          </nav>
        </div>
      </header>

      <main className="container">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/import" element={<ImportWizard onComplete={() => setNeedsImport(false)} />} />
          <Route path="/exam/:sessionId" element={<ExamSession />} />
          <Route path="/results/:sessionId" element={<Results />} />
          <Route path="/study" element={<StudySession />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Routes>
      </main>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
