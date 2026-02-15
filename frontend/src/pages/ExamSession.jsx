import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sessionApi } from '../api/client'

// Timer component
function Timer({ sessionId, onTimeExpired }) {
  const [timeRemaining, setTimeRemaining] = useState(null)
  const [isPaused, setIsPaused] = useState(false)
  const [hasTimeLimit, setHasTimeLimit] = useState(false)
  const intervalRef = useRef(null)

  // Fetch initial time from backend
  useEffect(() => {
    const fetchTime = async () => {
      try {
        const data = await sessionApi.getTime(sessionId)
        if (data.time_limit_minutes) {
          setHasTimeLimit(true)
          setTimeRemaining(data.time_remaining_seconds)
          setIsPaused(data.is_paused)
        }
      } catch (err) {
        console.error('Failed to fetch time:', err)
      }
    }
    fetchTime()
  }, [sessionId])

  // Countdown effect
  useEffect(() => {
    if (!hasTimeLimit || isPaused || timeRemaining === null) return

    intervalRef.current = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          clearInterval(intervalRef.current)
          onTimeExpired()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(intervalRef.current)
  }, [hasTimeLimit, isPaused, timeRemaining !== null, onTimeExpired])

  const handlePause = async () => {
    try {
      if (isPaused) {
        await sessionApi.resume(sessionId)
        setIsPaused(false)
      } else {
        await sessionApi.pause(sessionId)
        setIsPaused(true)
      }
    } catch (err) {
      console.error('Failed to toggle pause:', err)
    }
  }

  if (!hasTimeLimit) return null

  const minutes = Math.floor(timeRemaining / 60)
  const seconds = timeRemaining % 60
  const isWarning = timeRemaining <= 600 && timeRemaining > 120 // 10 min warning
  const isCritical = timeRemaining <= 120 // 2 min critical

  let bgColor = 'var(--gray-100)'
  let textColor = 'var(--gray-700)'
  if (isCritical) {
    bgColor = 'var(--danger)'
    textColor = 'white'
  } else if (isWarning) {
    bgColor = 'var(--warning)'
    textColor = 'var(--gray-900)'
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 16px',
      background: bgColor, borderRadius: '8px', marginBottom: '16px',
      animation: isCritical ? 'pulse 1s infinite' : 'none',
    }}>
      <span style={{ fontSize: '20px' }}>⏱️</span>
      <span style={{ 
        fontSize: '24px', fontWeight: '700', fontFamily: 'monospace',
        color: textColor,
      }}>
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
      <span style={{ color: textColor, fontSize: '14px' }}>remaining</span>
      <button
        onClick={handlePause}
        style={{
          marginLeft: 'auto', padding: '6px 12px', borderRadius: '4px',
          border: 'none', cursor: 'pointer',
          background: isPaused ? 'var(--success)' : 'rgba(0,0,0,0.1)',
          color: isPaused ? 'white' : textColor,
        }}
      >
        {isPaused ? '▶️ Resume' : '⏸️ Pause'}
      </button>
      {isWarning && !isCritical && <span style={{ fontSize: '12px', color: textColor }}>Less than 10 minutes!</span>}
      {isCritical && <span style={{ fontSize: '12px', fontWeight: '600', color: textColor }}>Time almost up!</span>}
    </div>
  )
}

function ExamSession() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [flags, setFlags] = useState({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleTimeExpired = useCallback(async () => {
    if (submitting) return
    alert('Time expired! Your exam will be submitted automatically.')
    try {
      await sessionApi.submit(sessionId)
      navigate(`/results/${sessionId}`)
    } catch (err) {
      setError(err.message)
    }
  }, [sessionId, navigate, submitting])

  useEffect(() => { loadQuestions() }, [sessionId])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
      const key = e.key.toLowerCase()
      if (key >= '1' && key <= '9') {
        const choiceIndex = parseInt(key) - 1
        if (questions[currentIndex]?.choices[choiceIndex]) {
          toggleChoice(questions[currentIndex].choices[choiceIndex].label)
        }
      } else if (key === 'f') { toggleFlag() }
      else if (key === 'n' || key === 'arrowright') { goNext() }
      else if (key === 'p' || key === 'arrowleft') { goPrev() }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [currentIndex, questions, answers])

  const loadQuestions = async () => {
    try {
      const data = await sessionApi.getQuestions(sessionId)
      // If completed, redirect to results immediately
      if (data.is_completed) { 
        navigate(`/results/${sessionId}`)
        return 
      }
      setQuestions(data.questions)
      const existingAnswers = {}, existingFlags = {}
      data.questions.forEach(q => {
        if (q.user_selected?.length) existingAnswers[q.id] = q.user_selected
        if (q.user_flagged) existingFlags[q.id] = true
      })
      setAnswers(existingAnswers)
      setFlags(existingFlags)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  const toggleChoice = (label) => {
    const q = questions[currentIndex]
    if (!q) return
    const current = answers[q.id] || []
    let updated
    if (q.question_type === 'single' || q.question_type === 'truefalse') {
      updated = current.includes(label) ? [] : [label]
    } else {
      updated = current.includes(label) ? current.filter(l => l !== label) : [...current, label]
    }
    setAnswers(prev => ({ ...prev, [q.id]: updated }))
    saveAnswer(q.id, updated, flags[q.id] || false)
  }

  const toggleFlag = () => {
    const q = questions[currentIndex]
    if (!q) return
    const newFlag = !flags[q.id]
    setFlags(prev => ({ ...prev, [q.id]: newFlag }))
    saveAnswer(q.id, answers[q.id] || [], newFlag)
  }

  const saveAnswer = async (questionId, selected, flagged) => {
    try { await sessionApi.answer(sessionId, questionId, selected, flagged) }
    catch (err) { console.error('Failed to save answer:', err) }
  }

  const goNext = () => { if (currentIndex < questions.length - 1) setCurrentIndex(currentIndex + 1) }
  const goPrev = () => { if (currentIndex > 0) setCurrentIndex(currentIndex - 1) }

  const submitExam = async () => {
    if (!confirm('Submit exam? You cannot change answers after submission.')) return
    setSubmitting(true)
    try { await sessionApi.submit(sessionId); navigate(`/results/${sessionId}`) }
    catch (err) { setError(err.message); setSubmitting(false) }
  }

  if (loading) return <div className="loading">Loading exam...</div>
  if (error) return <div className="error">{error}</div>
  if (!questions.length) return <div className="error">No questions loaded</div>

  const question = questions[currentIndex]
  const selectedAnswers = answers[question.id] || []
  const isFlagged = flags[question.id] || false
  const answeredCount = Object.keys(answers).filter(k => answers[k]?.length > 0).length
  const flaggedCount = Object.keys(flags).filter(k => flags[k]).length

  return (
    <div className="exam-session">
      <Timer sessionId={sessionId} onTimeExpired={handleTimeExpired} />
      <div style={{ display: 'flex', gap: '20px' }}>
        <div style={{ flex: 1 }}>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ color: 'var(--gray-600)' }}>Question {currentIndex + 1} of {questions.length}</span>
                {question.source_page > 0 && (
                  <span style={{ fontSize: '12px', color: 'var(--gray-500)', background: 'var(--gray-100)', padding: '4px 8px', borderRadius: '4px' }}>
                    📄 Q{question.source_page}
                  </span>
                )}
                {question.domain_id && (
                  <span style={{ fontSize: '12px', color: 'var(--gray-500)' }} title={`Domain: ${question.domain_id}`}>
                    {question.domain_id}
                  </span>
                )}
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                {question.question_type === 'multi' && <span className="badge badge-info">Select multiple</span>}
                <button className={`btn ${isFlagged ? 'btn-danger' : 'btn-secondary'}`} onClick={toggleFlag} style={{ padding: '6px 12px' }}>
                  {isFlagged ? '🚩 Flagged' : '🏳️ Flag'}
                </button>
              </div>
            </div>
            {question.exhibit_image && (
              <div style={{ marginBottom: '20px', border: '1px solid var(--gray-200)', borderRadius: '8px', overflow: 'hidden' }}>
                <img 
                  src={question.exhibit_image}
                  alt="Exhibit"
                  style={{ width: '100%', height: 'auto', display: 'block' }}
                />
              </div>
            )}
            <div style={{ fontSize: '18px', marginBottom: '24px', lineHeight: 1.6, whiteSpace: 'pre-line' }}>{question.text}</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {question.choices.map((choice, i) => {
                const isSelected = selectedAnswers.includes(choice.label)
                const borderColor = isSelected ? 'var(--primary)' : 'var(--gray-200)'
                const bgColor = isSelected ? 'rgba(0, 120, 212, 0.05)' : 'white'
                
                return (
                  <button key={choice.label} onClick={() => toggleChoice(choice.label)} style={{
                    display: 'flex', alignItems: 'flex-start', gap: '12px', padding: '16px',
                    border: `2px solid ${borderColor}`,
                    borderRadius: '8px', background: bgColor,
                    cursor: 'pointer', textAlign: 'left', fontSize: '16px',
                  }}>
                    <span style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px',
                      borderRadius: '4px', 
                      background: isSelected ? 'var(--primary)' : 'var(--gray-200)',
                      color: isSelected ? 'white' : 'var(--gray-800)', fontWeight: '600', flexShrink: 0,
                    }}>{choice.label}</span>
                    <span style={{ flex: 1 }}>{choice.text}</span>
                  </button>
                )
              })}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '24px' }}>
              <button className="btn btn-secondary" onClick={goPrev} disabled={currentIndex === 0}>← Previous</button>
              <button className="btn btn-secondary" onClick={goNext} disabled={currentIndex === questions.length - 1}>Next →</button>
            </div>
            <div style={{ marginTop: '16px', textAlign: 'center', fontSize: '12px', color: 'var(--gray-600)' }}>
              Shortcuts: <span className="kbd">1-9</span> select • <span className="kbd">F</span> flag • <span className="kbd">N</span> next • <span className="kbd">P</span> prev
            </div>
          </div>
        </div>
        <div style={{ width: '280px' }}>
          <div className="card">
            <h3 style={{ marginBottom: '12px' }}>Progress</h3>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', marginBottom: '4px' }}>
                <span>Answered</span><span>{answeredCount} / {questions.length}</span>
              </div>
              <div className="progress-bar"><div className="fill" style={{ width: `${(answeredCount / questions.length) * 100}%` }} /></div>
            </div>
            {flaggedCount > 0 && <div style={{ fontSize: '14px', color: 'var(--warning)' }}>🚩 {flaggedCount} flagged for review</div>}
          </div>
          <div className="card">
            <h3 style={{ marginBottom: '12px' }}>Navigator</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '6px' }}>
              {questions.map((q, i) => {
                const isAnswered = answers[q.id]?.length > 0
                const isFlag = flags[q.id]
                let bg = 'var(--gray-200)'
                if (isAnswered) bg = 'var(--success)'
                if (isFlag) bg = 'var(--warning)'
                if (i === currentIndex) bg = 'var(--primary)'
                return (
                  <button key={q.id} onClick={() => setCurrentIndex(i)} style={{
                    width: '36px', height: '36px', border: 'none', borderRadius: '4px', background: bg,
                    color: (i === currentIndex || isAnswered) ? 'white' : 'var(--gray-800)',
                    cursor: 'pointer', fontWeight: i === currentIndex ? '600' : '400',
                  }}>{i + 1}</button>
                )
              })}
            </div>
          </div>
          <button className="btn btn-primary" style={{ width: '100%', marginTop: '16px' }} onClick={submitExam} disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit Exam'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ExamSession
