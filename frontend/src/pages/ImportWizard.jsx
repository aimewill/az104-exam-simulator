import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { importApi } from '../api/client'

function ImportWizard({ onComplete }) {
  const [step, setStep] = useState('check') // check, scan, review, importing, done
  const [status, setStatus] = useState(null)
  const [scanResult, setScanResult] = useState(null)
  const [error, setError] = useState(null)
  const [importing, setImporting] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    checkStatus()
  }, [])

  const checkStatus = async () => {
    try {
      const result = await importApi.getStatus()
      setStatus(result)
      if (!result.needs_import) {
        setStep('done')
      } else {
        setStep('scan')
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const runScan = async () => {
    setStep('scanning')
    setError(null)
    try {
      const result = await importApi.scan()
      setScanResult(result)
      setStep('review')
    } catch (err) {
      setError(err.message)
      setStep('scan')
    }
  }

  const runImport = async () => {
    setImporting(true)
    setError(null)
    try {
      const result = await importApi.run([])
      setStep('done')
      onComplete?.()
    } catch (err) {
      setError(err.message)
      setImporting(false)
    }
  }

  if (step === 'check') {
    return <div className="loading">Checking import status...</div>
  }

  return (
    <div className="import-wizard">
      <div className="card">
        <h2>Import Questions</h2>
        
        {error && <div className="error">{error}</div>}

        {step === 'scan' && (
          <>
            <p style={{ marginBottom: '16px' }}>
              {status?.new_files?.length > 0 
                ? `Found ${status.new_files.length} new PDF file(s) to import.`
                : 'Scan your PDF files to extract exam questions.'}
            </p>
            {status?.new_files?.length > 0 && (
              <ul style={{ marginBottom: '16px', paddingLeft: '20px' }}>
                {status.new_files.map(f => <li key={f}>{f}</li>)}
              </ul>
            )}
            <button className="btn btn-primary" onClick={runScan}>
              Scan PDFs
            </button>
          </>
        )}

        {step === 'scanning' && (
          <div className="loading">Scanning PDF files... This may take a moment.</div>
        )}

        {step === 'review' && scanResult && (
          <>
            <h3>Scan Results</h3>
            <div className="grid grid-3" style={{ marginBottom: '20px' }}>
              <div className="card stat-card">
                <div className="value">{scanResult.total_questions}</div>
                <div className="label">Total Found</div>
              </div>
              <div className="card stat-card">
                <div className="value">{scanResult.valid_questions}</div>
                <div className="label">Valid Questions</div>
              </div>
              <div className="card stat-card">
                <div className="value">{scanResult.files_found}</div>
                <div className="label">PDF Files</div>
              </div>
            </div>

            {scanResult.issues_summary && Object.keys(scanResult.issues_summary).length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h4>Issues Found</h4>
                <ul style={{ paddingLeft: '20px' }}>
                  {scanResult.issues_summary.missing_answers > 0 && (
                    <li>{scanResult.issues_summary.missing_answers} questions missing answers</li>
                  )}
                  {scanResult.issues_summary.broken_choices > 0 && (
                    <li>{scanResult.issues_summary.broken_choices} questions with broken choices</li>
                  )}
                  {scanResult.issues_summary.duplicates > 0 && (
                    <li>{scanResult.issues_summary.duplicates} duplicate questions</li>
                  )}
                  {scanResult.issues_summary.info && (
                    <li style={{ color: 'var(--primary)' }}>{scanResult.issues_summary.info}</li>
                  )}
                </ul>
              </div>
            )}

            {scanResult.reports?.map((report, i) => (
              <div key={i} style={{ marginBottom: '16px', padding: '12px', background: 'var(--gray-100)', borderRadius: '8px' }}>
                <strong>{report.filename}</strong>
                <span style={{ marginLeft: '12px', color: 'var(--gray-600)' }}>
                  {report.valid_questions} valid / {report.total_questions} total
                </span>
              </div>
            ))}

            <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
              <button className="btn btn-primary" onClick={runImport} disabled={importing}>
                {importing ? 'Importing...' : `Import ${scanResult.valid_questions} Questions`}
              </button>
              <button className="btn btn-secondary" onClick={runScan} disabled={importing}>
                Re-scan
              </button>
            </div>
          </>
        )}

        {step === 'done' && (
          <>
            <p style={{ color: 'var(--success)', marginBottom: '16px' }}>
              ✓ Questions imported successfully!
            </p>
            <p style={{ marginBottom: '16px' }}>
              You have {status?.questions_in_db || 'some'} questions in the database.
            </p>
            <button className="btn btn-primary" onClick={() => navigate('/')}>
              Go to Dashboard
            </button>
          </>
        )}
      </div>
    </div>
  )
}

export default ImportWizard
