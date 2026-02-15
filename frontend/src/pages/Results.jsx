import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { sessionApi } from '../api/client'

function Results() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showMissedOnly, setShowMissedOnly] = useState(false)

  useEffect(() => { loadResults() }, [sessionId])

  const loadResults = async () => {
    try {
      const data = await sessionApi.getResults(sessionId)
      setResults(data)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  if (loading) return <div className="loading">Loading results...</div>
  if (error) return <div className="error">{error}</div>
  if (!results) return null

  const { session, questions, domain_breakdown } = results
  const filteredQuestions = showMissedOnly ? questions.filter(q => !q.is_correct) : questions

  return (
    <div className="results">
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ marginBottom: '8px' }}>Exam Results</h2>
            <p style={{ color: 'var(--gray-600)' }}>
              {new Date(session.completed_at).toLocaleString()} • {session.mode.replace('_', ' ')} mode
            </p>
          </div>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>Back to Dashboard</button>
        </div>
      </div>

      <div className="grid grid-3">
        <div className={`card score-display ${session.passed ? 'passed' : 'failed'}`}>
          <div className="score">{session.scaled_score}</div>
          <div className="label">Scaled Score (0-1000)</div>
          <div style={{ marginTop: '12px' }}>
            <span className={`badge ${session.passed ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '16px', padding: '8px 16px' }}>
              {session.passed ? '✓ PASSED' : '✗ FAILED'}
            </span>
          </div>
        </div>
        <div className="card stat-card">
          <div className="value">{session.correct_count}/{session.total_questions}</div>
          <div className="label">Correct Answers</div>
          <div style={{ marginTop: '8px', color: 'var(--gray-600)' }}>{session.percent_score?.toFixed(1)}%</div>
        </div>
        <div className="card stat-card">
          <div className="value">700</div>
          <div className="label">Passing Score</div>
          <div style={{ marginTop: '8px', color: 'var(--gray-600)' }}>
            {session.passed ? `+${session.scaled_score - 700} above` : `${700 - session.scaled_score} points needed`}
          </div>
        </div>
      </div>

      {Object.keys(domain_breakdown).length > 0 && (
        <div className="card">
          <h3>Domain Breakdown</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
            {Object.entries(domain_breakdown).map(([domain, stats]) => (
              <div key={domain} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ flex: 1, textTransform: 'capitalize' }}>{domain.replace(/-/g, ' ')}</span>
                <div style={{ width: '200px' }}>
                  <div className="progress-bar">
                    <div className="fill" style={{ 
                      width: `${stats.accuracy}%`, 
                      background: stats.accuracy >= 70 ? 'var(--success)' : 'var(--danger)' 
                    }} />
                  </div>
                </div>
                <span style={{ width: '80px', textAlign: 'right' }}>
                  {stats.correct}/{stats.total} ({stats.accuracy}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>Question Review</h3>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input type="checkbox" checked={showMissedOnly} onChange={(e) => setShowMissedOnly(e.target.checked)} />
            Show missed only ({questions.filter(q => !q.is_correct).length})
          </label>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredQuestions.map((item, index) => (
            <div key={item.question.id} style={{
              padding: '16px', borderRadius: '8px',
              background: item.is_correct ? 'rgba(16, 124, 16, 0.05)' : 'rgba(209, 52, 56, 0.05)',
              border: `1px solid ${item.is_correct ? 'var(--success)' : 'var(--danger)'}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontWeight: '600' }}>
                  Q{questions.indexOf(item) + 1}
                  <span className={`badge ${item.is_correct ? 'badge-success' : 'badge-danger'}`} style={{ marginLeft: '8px' }}>
                    {item.is_correct ? 'Correct' : 'Incorrect'}
                  </span>
                </span>
                <span style={{ color: 'var(--gray-600)', fontSize: '14px' }}>
                  {item.question.domain_id?.replace(/-/g, ' ')}
                  {item.question.source_page > 0 && ` • Q${item.question.source_page}`}
                </span>
              </div>

              {item.question.exhibit_image && (
                <div style={{ marginBottom: '16px', border: '1px solid var(--gray-200)', borderRadius: '6px', overflow: 'hidden' }}>
                  <img 
                    src={item.question.exhibit_image}
                    alt="Exhibit"
                    style={{ width: '100%', height: 'auto', display: 'block' }}
                  />
                </div>
              )}
              <div style={{ marginBottom: '12px', whiteSpace: 'pre-line' }}>{item.question.text}</div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {item.question.choices.map(choice => {
                  const isSelected = item.selected?.includes(choice.label)
                  const isCorrect = item.question.correct_answers?.includes(choice.label)
                  let bg = 'white', border = 'var(--gray-200)'
                  if (isCorrect) { bg = 'rgba(16, 124, 16, 0.1)'; border = 'var(--success)' }
                  if (isSelected && !isCorrect) { bg = 'rgba(209, 52, 56, 0.1)'; border = 'var(--danger)' }

                  return (
                    <div key={choice.label} style={{
                      display: 'flex', alignItems: 'flex-start', gap: '8px', padding: '10px',
                      background: bg, border: `1px solid ${border}`, borderRadius: '6px',
                    }}>
                      <span style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        width: '24px', height: '24px', borderRadius: '4px', fontSize: '14px',
                        background: isCorrect ? 'var(--success)' : isSelected ? 'var(--danger)' : 'var(--gray-200)',
                        color: (isCorrect || isSelected) ? 'white' : 'var(--gray-800)', fontWeight: '600', flexShrink: 0,
                      }}>{choice.label}</span>
                      <span style={{ flex: 1 }}>{choice.text}</span>
                      {isSelected && <span style={{ fontSize: '12px', color: 'var(--gray-600)' }}>Your answer</span>}
                      {isCorrect && <span style={{ fontSize: '12px', color: 'var(--success)' }}>✓ Correct</span>}
                    </div>
                  )
                })}
              </div>

              {item.question.explanation && (
                <div style={{ marginTop: '12px', padding: '12px', background: 'var(--gray-100)', borderRadius: '6px', fontSize: '14px' }}>
                  <strong>Explanation:</strong> {item.question.explanation}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Results
