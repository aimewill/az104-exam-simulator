import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { dashboardApi, sessionApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

function Dashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [startingSession, setStartingSession] = useState(false)
  const [timedMode, setTimedMode] = useState(false)
  const [timeLimit, setTimeLimit] = useState(100) // Default 100 minutes like real exam
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      const dashboard = await dashboardApi.get()
      setData(dashboard)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const startExam = async (mode) => {
    setStartingSession(true)
    try {
      const timeLimitMinutes = timedMode ? timeLimit : null
      const session = await sessionApi.start(mode, timeLimitMinutes)
      navigate(`/exam/${session.id}`)
    } catch (err) {
      setError(err.message)
      setStartingSession(false)
    }
  }

  const exportMissed = async () => {
    try {
      const blob = await dashboardApi.exportMissed()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'missed_questions.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <div className="loading">Loading dashboard...</div>
  if (error) return <div className="error">{error}</div>
  if (!data) return null

  const { overview, recent_sessions, weak_domains, trend_data } = data

  return (
    <div className="dashboard">
      <div className="card">
        <h2>Start New Exam</h2>
        <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>
          Choose an exam mode to begin a 60-question session
        </p>
        
        {/* Timer Mode Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '20px', padding: '14px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)' }}>
          <div style={{ display: 'flex', gap: '6px', padding: '4px', background: 'var(--gray-200)', borderRadius: '8px' }}>
            <button
              onClick={() => setTimedMode(false)}
              style={{
                padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                background: !timedMode ? 'var(--primary)' : 'transparent',
                color: !timedMode ? 'white' : 'var(--text-secondary)',
                fontWeight: '500', fontSize: '13px', transition: 'all 0.15s ease',
              }}
            >Practice Mode</button>
            <button
              onClick={() => setTimedMode(true)}
              style={{
                padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer',
                background: timedMode ? 'var(--primary)' : 'transparent',
                color: timedMode ? 'white' : 'var(--text-secondary)',
                fontWeight: '500', fontSize: '13px', transition: 'all 0.15s ease',
              }}
            >⏱️ Timed</button>
          </div>
          {timedMode ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="number"
                min="10"
                max="180"
                value={timeLimit}
                onChange={(e) => setTimeLimit(Math.max(10, Math.min(180, parseInt(e.target.value) || 100)))}
                style={{ width: '56px', padding: '6px 8px', borderRadius: '6px', border: '1px solid var(--border-color)', textAlign: 'center', background: 'var(--bg-card)', color: 'var(--text-primary)', fontSize: '13px', fontWeight: '500' }}
              />
              <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>min</span>
            </div>
          ) : (
            <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No time limit</span>
          )}
        </div>
        
        {!isAuthenticated ? (
          <div style={{ padding: '20px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-color)', textAlign: 'center' }}>
            <p style={{ marginBottom: '12px', color: 'var(--text-secondary)' }}>
              🔐 Please sign in to start an exam and track your progress
            </p>
            <Link to="/login" className="btn btn-primary">Sign In to Start</Link>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={() => startExam('random')}
                disabled={startingSession || overview.total_questions === 0}>Random</button>
              <button className="btn btn-secondary" onClick={() => startExam('unseen')}
                disabled={startingSession || overview.total_questions === 0}>Unseen First</button>
              <button className="btn btn-secondary" onClick={() => startExam('weak')}
                disabled={startingSession || overview.total_questions === 0}>Weak Areas</button>
              <button className="btn btn-secondary" onClick={() => startExam('review_wrong')}
                disabled={startingSession || overview.total_questions === 0}>Review Wrong</button>
              <button className="btn btn-secondary" onClick={() => navigate('/study')}
                style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)', color: 'white', border: 'none' }}>📚 Study Mode</button>
            </div>
            {overview.total_questions === 0 && (
              <p style={{ marginTop: '12px', color: 'var(--danger)' }}>
                No questions available. Please import questions first.
              </p>
            )}
          </>
        )}
      </div>

      <div className="grid grid-4">
        <div className="card stat-card">
          <div className="value">{overview.exam_questions || overview.total_questions}</div>
          <div className="label">Exam Questions</div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            +{overview.total_questions - (overview.exam_questions || overview.total_questions)} study
          </div>
        </div>
        <div className="card stat-card">
          <div className="value" style={{ color: overview.unseen_questions > 0 ? 'var(--primary)' : 'var(--success)' }}>
            {overview.unseen_questions || 0}
          </div>
          <div className="label">Unseen</div>
          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            {overview.seen_questions || 0} seen
          </div>
        </div>
        <div className="card stat-card">
          <div className="value">{overview.average_score}</div>
          <div className="label">Average Score</div>
        </div>
        <div className="card stat-card">
          <div className="value">{overview.passing_rate}%</div>
          <div className="label">Passing Rate</div>
        </div>
      </div>

      {/* Progress through exam questions */}
      {(overview.exam_questions || overview.total_questions) > 0 && (
        <div className="card">
          <h3>📊 Exam Question Coverage</h3>
          <div style={{ marginTop: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '13px' }}>
              <span>{overview.seen_questions || 0} of {overview.exam_questions || overview.total_questions} exam questions seen</span>
              <span style={{ fontWeight: '600' }}>
                {Math.round(((overview.seen_questions || 0) / (overview.exam_questions || overview.total_questions)) * 100)}%
              </span>
            </div>
            <div className="progress-bar" style={{ height: '10px' }}>
              <div 
                className="fill" 
                style={{ 
                  width: `${((overview.seen_questions || 0) / (overview.exam_questions || overview.total_questions)) * 100}%`,
                  background: 'linear-gradient(90deg, var(--primary), var(--primary-hover))'
                }} 
              />
            </div>
            <p style={{ marginTop: '10px', fontSize: '12px', color: 'var(--text-secondary)' }}>
              {overview.unseen_questions > 0 
                ? `${Math.ceil(overview.unseen_questions / 60)} more sessions to see all exam questions`
                : '✅ You have seen all exam questions! Use "Review Wrong" to focus on missed ones.'
              }
            </p>
          </div>
        </div>
      )}

      {weak_domains.length > 0 && (
        <div className="card">
          <h3>Weak Areas</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {weak_domains.map(domain => (
              <div key={domain.domain_id} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ flex: 1 }}>{domain.domain_name}</span>
                <div style={{ width: '200px' }}>
                  <div className="progress-bar">
                    <div className="fill" style={{ width: `${domain.accuracy * 100}%`, background: 'var(--danger)' }} />
                  </div>
                </div>
                <span style={{ width: '50px', textAlign: 'right' }}>{Math.round(domain.accuracy * 100)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {trend_data.length > 0 && (
        <div className="card">
          <h3>Score Trend</h3>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px', height: '150px', marginTop: '16px' }}>
            {trend_data.map((point, i) => (
              <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <div style={{
                  width: '100%', maxWidth: '40px', height: `${(point.scaled_score / 1000) * 100}%`,
                  background: point.passed ? 'var(--success)' : 'var(--danger)',
                  borderRadius: '4px 4px 0 0', minHeight: '4px',
                }} title={`Score: ${point.scaled_score}`} />
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)', marginTop: '4px' }}>{point.scaled_score}</span>
              </div>
            ))}
          </div>
          <div style={{ textAlign: 'center', marginTop: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            Passing score: 700
          </div>
        </div>
      )}

      {recent_sessions.length > 0 && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ margin: 0 }}>Recent Sessions</h3>
            <button className="btn btn-secondary" onClick={exportMissed}>Export Missed Questions</button>
          </div>
          <table className="table">
            <thead>
              <tr><th>Date</th><th>Mode</th><th>Score</th><th>Scaled</th><th>Result</th><th></th></tr>
            </thead>
            <tbody>
              {recent_sessions.map(session => (
                <tr key={session.id}>
                  <td>{new Date(session.date).toLocaleDateString()}</td>
                  <td style={{ textTransform: 'capitalize' }}>{session.mode.replace('_', ' ')}</td>
                  <td>{session.correct}/{session.total} ({session.percent_score}%)</td>
                  <td>{session.scaled_score}/1000</td>
                  <td><span className={`badge ${session.passed ? 'badge-success' : 'badge-danger'}`}>
                    {session.passed ? 'PASS' : 'FAIL'}</span></td>
                  <td><button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '12px' }}
                    onClick={() => navigate(`/results/${session.id}`)}>Review</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Dashboard
