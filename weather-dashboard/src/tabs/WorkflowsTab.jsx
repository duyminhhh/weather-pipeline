import { useState, useEffect } from 'react'
import { getJobId, listRuns, getRun } from '../api'
import { Card, SectionHead, Btn, Badge, Spinner, Alert } from '../components/UI'

const DATABRICKS_HOST = import.meta.env.VITE_DATABRICKS_HOST || ''

const STATE_COLOR = {
  RUNNING:         'blue',
  PENDING:         'amber',
  TERMINATED:      'gray',
  INTERNAL_ERROR:  'red',
}
const RESULT_COLOR = {
  SUCCESS:  'green',
  FAILED:   'red',
  CANCELED: 'gray',
  TIMEDOUT: 'amber',
}

function duration(r) {
  if (!r.start_time || !r.end_time) return '—'
  const ms = r.end_time - r.start_time
  const s = Math.floor(ms / 1000)
  if (s < 60) return `${s}s`
  return `${Math.floor(s / 60)}m ${s % 60}s`
}

function ts(epoch) {
  if (!epoch) return '—'
  return new Date(epoch).toISOString().slice(0, 16).replace('T', ' ') + ' UTC'
}

export default function WorkflowsTab() {
  const [jobId, setJobId] = useState(null)
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [runIdInput, setRunIdInput] = useState('')
  const [runInfo, setRunInfo] = useState(null)
  const [runInfoLoading, setRunInfoLoading] = useState(false)
  const [error, setError] = useState(null)

  async function load() {
    setLoading(true); setError(null)
    try {
      const jid = await getJobId()
      setJobId(jid)
      if (jid) {
        const data = await listRuns(jid)
        setRuns(data.runs ?? [])
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function checkRun() {
    if (!runIdInput) return
    setRunInfoLoading(true); setRunInfo(null)
    try {
      const info = await getRun(parseInt(runIdInput))
      setRunInfo(info)
    } catch (e) {
      setRunInfo({ _error: e.message })
    } finally {
      setRunInfoLoading(false)
    }
  }

  return (
    <div>
      {/* Run ID checker */}
      <Card style={{ marginBottom: 20 }}>
        <SectionHead action={<Btn small onClick={load}>↻ Refresh</Btn>}>
          Check Run by ID
        </SectionHead>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            placeholder="run_id e.g. 123456"
            value={runIdInput}
            onChange={e => setRunIdInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && checkRun()}
            style={{ flex: 1, maxWidth: 300 }}
          />
          <Btn primary onClick={checkRun} disabled={runInfoLoading || !runIdInput}>
            {runInfoLoading ? '…' : '→ Check'}
          </Btn>
        </div>

        {runInfo && !runInfo._error && (
          <div style={{ marginTop: 14, padding: '12px 16px', background: 'var(--bg2)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              <div>
                <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>State</div>
                <Badge color={STATE_COLOR[runInfo.state?.life_cycle_state] || 'gray'}>
                  {runInfo.state?.life_cycle_state ?? '—'}
                </Badge>
              </div>
              <div>
                <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Result</div>
                <Badge color={RESULT_COLOR[runInfo.state?.result_state] || 'gray'}>
                  {runInfo.state?.result_state ?? '—'}
                </Badge>
              </div>
              <div>
                <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Duration</div>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 12 }}>{duration(runInfo)}</span>
              </div>
              <div>
                <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Link</div>
                {runInfo.run_page_url ? (
                  <a href={runInfo.run_page_url} target="_blank" rel="noreferrer"
                     style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--accent2)' }}>↗ Databricks</a>
                ) : '—'}
              </div>
            </div>
            {runInfo.state?.state_message && (
              <div style={{ marginTop: 10, fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)', borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                {runInfo.state.state_message}
              </div>
            )}
          </div>
        )}
        {runInfo?._error && <Alert type="error" style={{ marginTop: 10 }}>{runInfo._error}</Alert>}
      </Card>

      {/* Run history */}
      <SectionHead>Run History — last 15 runs</SectionHead>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: 12, padding: '16px 0' }}>
          <Spinner /> Loading runs…
        </div>
      )}
      {error && <Alert type="error">{error}</Alert>}
      {!loading && !jobId && !error && <Alert type="warn">Workflow "weather-pipeline" not found.</Alert>}
      {!loading && jobId && runs.length === 0 && <Alert type="info">No runs found yet.</Alert>}

      {runs.length > 0 && (
        <Card>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'var(--mono)' }}>
            <thead>
              <tr>
                {['Run ID', 'State', 'Result', 'Started', 'Duration', 'Link'].map(h => (
                  <th key={h} style={{
                    padding: '7px 12px', textAlign: 'left', fontSize: 10,
                    color: 'var(--text3)', letterSpacing: 1, textTransform: 'uppercase',
                    borderBottom: '1px solid var(--border)',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.map((r, i) => {
                const life = r.state?.life_cycle_state ?? ''
                const result = r.state?.result_state ?? ''
                return (
                  <tr key={r.run_id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '8px 12px', color: 'var(--accent2)' }}>{r.run_id}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <Badge color={STATE_COLOR[life] || 'gray'}>{life || '—'}</Badge>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <Badge color={RESULT_COLOR[result] || 'gray'}>{result || '—'}</Badge>
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--text2)' }}>{ts(r.start_time)}</td>
                    <td style={{ padding: '8px 12px', color: 'var(--text2)' }}>{duration(r)}</td>
                    <td style={{ padding: '8px 12px' }}>
                      {r.run_page_url ? (
                        <a href={r.run_page_url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent2)' }}>↗ View</a>
                      ) : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  )
}
