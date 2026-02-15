import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { sessionApi } from '../api/client'

function StudySession() {
  const navigate = useNavigate()
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [seenIds, setSeenIds] = useState(new Set()) // Track locally seen in this session
  const [stats, setStats] = useState({ total: 0, seen: 0, unseen: 0 })

  useEffect(() => { loadStudyQuestions() }, [])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      const key = e.key.toLowerCase()
      if (key === ' ' || key === 'enter') { setShowAnswer(!showAnswer); e.preventDefault() }
      else if (key === 'n' || key === 'arrowright') { goNext() }
      else if (key === 'p' || key === 'arrowleft') { goPrev() }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentIndex, questions, showAnswer])

  const loadStudyQuestions = async () => {
    try {
      const data = await sessionApi.getStudyQuestions()
      setQuestions(data.questions)
      setStats({ total: data.total, seen: data.seen, unseen: data.unseen })
      // Pre-populate seenIds with already-seen questions
      const alreadySeen = new Set(data.questions.filter(q => q.times_shown > 0).map(q => q.id))
      setSeenIds(alreadySeen)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  const markCurrentAsSeen = async () => {
    const question = questions[currentIndex]
    if (question && !seenIds.has(question.id)) {
      try {
        await sessionApi.markStudySeen(question.id)
        setSeenIds(prev => new Set([...prev, question.id]))
        setStats(prev => ({ ...prev, seen: prev.seen + 1, unseen: prev.unseen - 1 }))
      } catch (err) {
        console.error('Failed to mark as seen:', err)
      }
    }
  }

  const goNext = () => {
    if (currentIndex < questions.length - 1) {
      markCurrentAsSeen() // Mark current as seen when moving to next
      setCurrentIndex(currentIndex + 1)
      setShowAnswer(false)
    }
  }
  
  const goPrev = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
      setShowAnswer(false)
    }
  }

  if (loading) return <div className="loading">Loading study cards...</div>
  if (error) return <div className="error">{error}</div>
  if (!questions.length) return (
    <div className="card" style={{ textAlign: 'center' }}>
      <h2>No Study Questions Available</h2>
      <p>All questions have been imported as interactive exams.</p>
      <button className="btn btn-primary" onClick={() => navigate('/')}>Back to Dashboard</button>
    </div>
  )

  const question = questions[currentIndex]

  return (
    <div className="study-session">
      <div style={{ display: 'flex', gap: '20px' }}>
        <div style={{ flex: 1 }}>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <span style={{ color: 'var(--gray-600)' }}>
                Study Card {currentIndex + 1} of {questions.length}
              </span>
              <span className="badge badge-info">
                {question.question_type === 'study' ? '📚 Study' : question.question_type}
              </span>
            </div>
            
            <div style={{ fontSize: '18px', marginBottom: '24px', lineHeight: 1.6 }}>
              {question.text}
            </div>

            {!showAnswer ? (
              <button 
                className="btn btn-primary" 
                onClick={() => setShowAnswer(true)}
                style={{ width: '100%', padding: '16px', fontSize: '16px' }}
              >
                Show Answer & Explanation
              </button>
            ) : (
              <div style={{ 
                background: 'var(--success-light, #e8f5e9)', 
                padding: '20px', 
                borderRadius: '8px',
                border: '2px solid var(--success)'
              }}>
                <h4 style={{ marginBottom: '12px', color: 'var(--success)' }}>📖 Explanation</h4>
                <div style={{ lineHeight: 1.6 }}>
                  {question.explanation || 'No explanation available for this question.'}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
              <button className="btn btn-secondary" onClick={goPrev} disabled={currentIndex === 0}>
                ← Previous
              </button>
              <button className="btn btn-secondary" onClick={goNext} disabled={currentIndex === questions.length - 1}>
                Next →
              </button>
            </div>
            
            <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: 'var(--gray-600)' }}>
              Shortcuts: <span className="kbd">Space</span> show/hide • <span className="kbd">N</span> next • <span className="kbd">P</span> prev
            </div>
          </div>
        </div>

        <div style={{ width: '280px' }}>
          <div className="card">
            <h3 style={{ marginBottom: '12px' }}>📊 Coverage</h3>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginBottom: '4px' }}>
                <span>Seen</span>
                <span style={{ fontWeight: '600' }}>{seenIds.size} / {stats.total}</span>
              </div>
              <div className="progress-bar">
                <div className="fill" style={{ 
                  width: `${(seenIds.size / stats.total) * 100}%`,
                  background: 'linear-gradient(90deg, var(--primary), var(--primary-hover))'
                }} />
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                {stats.total - seenIds.size} unseen
              </div>
            </div>
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginBottom: '4px' }}>
                <span>Session Progress</span>
                <span>{currentIndex + 1} / {questions.length}</span>
              </div>
              <div className="progress-bar">
                <div className="fill" style={{ width: `${((currentIndex + 1) / questions.length) * 100}%` }} />
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: '12px' }}>Navigator</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '6px', maxHeight: '300px', overflowY: 'auto' }}>
              {questions.map((q, i) => (
                <button
                  key={q.id}
                  onClick={() => { setCurrentIndex(i); setShowAnswer(false) }}
                  style={{
                    width: '36px', height: '36px', border: 'none', borderRadius: '4px',
                    background: i === currentIndex ? 'var(--primary)' : i < currentIndex ? 'var(--success)' : 'var(--gray-200)',
                    color: i <= currentIndex ? 'white' : 'var(--gray-800)',
                    cursor: 'pointer', fontWeight: i === currentIndex ? '600' : '400',
                  }}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          </div>

          <button 
            className="btn btn-secondary" 
            style={{ width: '100%', marginTop: '16px' }} 
            onClick={() => navigate('/')}
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    </div>
  )
}

export default StudySession
