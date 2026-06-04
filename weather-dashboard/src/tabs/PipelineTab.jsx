import { useState, useEffect } from 'react'
import { getJobId, triggerJob, listClusters, submitNotebook } from '../api'
import { Card, SectionHead, Btn, Badge, Spinner, Alert, PipeNode } from '../components/UI'

const DATABRICKS_HOST = import.meta.env.VITE_DATABRICKS_HOST || ''

const NOTEBOOKS = [
  { label: '🕷️ Crawler',    path: '/Shared/weather-pipeline/weather_crawler',    desc: 'Fetch raw weather data' },
  { label: '🟤 Bronze',     path: '/Shared/weather-pipeline/01_bronze_ingest',    desc: 'Ingest raw JSON to Delta' },
  { label: '🥈 Silver',     path: '/Shared/weather-pipeline/02_silver_transform', desc: 'Validate & normalize data' },
  { label: '🥇 Gold',       path: '/Shared/weather-pipeline/03_gold_aggregate',   desc: 'Aggregate & build KPIs' },
  { label: '🤖 ML Train',   path: '/Shared/weather-pipeline/04_ml_train',         desc: 'Train forecasting model' },
]

export default function PipelineTab() {
  const [jobId, setJobId] = useState(null)
  const [clusters, setClusters] = useState([])
  const [selCluster, setSelCluster] = useState('')
  const [loading, setLoading] = useState(true)
  const [triggering, setTriggering] = useState(false)
  const [runningNb, setRunningNb] = useState(null)
  const [messages, setMessages] = useState([])
  const [error, setError] = useState(null)

  function addMsg(text, type = 'info') {
    setMessages(prev => [...prev, { text, type, ts: new Date().toISOString().slice(11, 19) }])
  }

  useEffect(() => {
    async function load() {
      setLoading(true)
      try {
        const [jid, cls] = await Promise.allSettled([getJobId(), listClusters()])
        if (jid.status === 'fulfilled') setJobId(jid.value)
        if (cls.status === 'fulfilled') {
          setClusters(cls.value)
          if (cls.value.length > 0) setSelCluster(cls.value[0].cluster_id)
        }
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  async function triggerFull() {
    if (!jobId) return
    setTriggering(true)
    try {
      const resp = await triggerJob(jobId)
      addMsg(`✅ Pipeline triggered — run_id: ${resp.run_id}`, 'success')
    } catch (e) {
      addMsg(`❌ ${e.message}`, 'error')
    } finally {
      setTriggering(false)
    }
  }

  async function runNotebook(nb) {
    if (!selCluster) return
    setRunningNb(nb.path)
    try {
      const resp = await submitNotebook(selCluster, nb.path)
      addMsg(`✅ ${nb.label} submitted — run_id: ${resp.run_id}`, 'success')
    } catch (e) {
      addMsg(`❌ ${nb.label}: ${e.message}`, 'error')
    } finally {
      setRunningNb(null)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>
      {/* Left: Full Pipeline */}
      <div>
        <SectionHead>Full Pipeline</SectionHead>

        {/* Flow diagram */}
        <Card style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, overflowX: 'auto', paddingBottom: 4 }}>
            <PipeNode icon="🕷️" label="Crawler" color="indigo" />
            <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 12 }}>→</span>
            <PipeNode icon="🟤" label="Bronze" color="amber" />
            <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 12 }}>→</span>
            <PipeNode icon="🥈" label="Silver" color="gray" />
            <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 12 }}>→</span>
            <PipeNode icon="🥇" label="Gold" color="gold" />
            <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)', fontSize: 12 }}>→</span>
            <PipeNode icon="🤖" label="ML" color="purple" />
          </div>
        </Card>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: 12 }}>
            <Spinner /> Connecting to Databricks…
          </div>
        ) : error ? (
          <Alert type="error">{error}</Alert>
        ) : jobId ? (
          <Card style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 4 }}>Workflow Found</div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <Badge color="green">weather-pipeline</Badge>
                <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text2)' }}>job_id: {jobId}</span>
              </div>
            </div>
            <Btn primary onClick={triggerFull} disabled={triggering} style={{ width: '100%', justifyContent: 'center' }}>
              {triggering ? '⟳ Triggering…' : '▶ Trigger Full Pipeline'}
            </Btn>
            <div style={{ marginTop: 8 }}>
              <a
                href={`${DATABRICKS_HOST}/jobs/${jobId}`}
                target="_blank"
                rel="noreferrer"
                style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--accent2)' }}
              >
                ↗ View on Databricks
              </a>
            </div>
          </Card>
        ) : (
          <Alert type="warn">Workflow "weather-pipeline" not found. Run 00_setup_workflow first.</Alert>
        )}

        {/* Message log */}
        {messages.length > 0 && (
          <div style={{ marginTop: 12 }}>
            {messages.map((m, i) => (
              <div key={i} style={{
                padding: '6px 10px', borderRadius: 'var(--radius)',
                marginBottom: 4, fontSize: 11, fontFamily: 'var(--mono)',
                background: m.type === 'success' ? 'rgba(61,214,140,0.08)' :
                            m.type === 'error' ? 'rgba(240,82,82,0.08)' : 'var(--bg2)',
                color: m.type === 'success' ? '#3dd68c' :
                       m.type === 'error' ? 'var(--red)' : 'var(--text2)',
                border: `1px solid ${m.type === 'success' ? 'rgba(61,214,140,0.2)' : m.type === 'error' ? 'rgba(240,82,82,0.2)' : 'var(--border)'}`,
              }}>
                <span style={{ color: 'var(--text3)' }}>{m.ts}</span> {m.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right: Individual notebooks */}
      <div>
        <SectionHead>Run Individual Notebooks</SectionHead>

        {clusters.length > 0 ? (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, display: 'block', marginBottom: 6 }}>
                Cluster
              </label>
              <select value={selCluster} onChange={e => setSelCluster(e.target.value)} style={{ width: '100%' }}>
                {clusters.map(c => (
                  <option key={c.cluster_id} value={c.cluster_id}>
                    {c.cluster_name} ({c.cluster_id})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {NOTEBOOKS.map(nb => (
                <div key={nb.path} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '10px 14px', background: 'var(--bg1)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                }}>
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{nb.label}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 2 }}>{nb.desc}</div>
                  </div>
                  <Btn small primary onClick={() => runNotebook(nb)} disabled={runningNb === nb.path}>
                    {runningNb === nb.path ? '⟳' : '▶ Run'}
                  </Btn>
                </div>
              ))}
            </div>
          </>
        ) : !loading ? (
          <Alert type="info">No running clusters found. Start a cluster on Databricks first.</Alert>
        ) : null}
      </div>
    </div>
  )
}
