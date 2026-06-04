import { useState } from 'react'
import Layout from './components/Layout'
import DashboardTab from './tabs/DashboardTab'
import LiveWeatherTab from './tabs/LiveWeatherTab'
import MLTab from './tabs/MLTab'
import PipelineTab from './tabs/PipelineTab'
import WorkflowsTab from './tabs/WorkflowsTab'
import DataLayersTab from './tabs/DataLayersTab'
import './index.css'

const DATABRICKS_HOST  = import.meta.env.VITE_DATABRICKS_HOST  || ''
const DATABRICKS_TOKEN = import.meta.env.VITE_DATABRICKS_TOKEN || ''

export default function App() {
  const [tab, setTab] = useState('dashboard')

  const missing = !DATABRICKS_HOST || !DATABRICKS_TOKEN

  return (
    <Layout tab={tab} setTab={setTab}>
      {/* Spin-up keyframe */}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>

      {missing && (
        <div style={{
          marginBottom: 16, padding: '10px 16px', borderRadius: 6,
          background: 'rgba(245,166,35,0.08)', border: '1px solid rgba(245,166,35,0.3)',
          color: 'var(--amber)', fontSize: 12, fontFamily: 'var(--mono)',
        }}>
          ⚠ Missing env vars — add VITE_DATABRICKS_HOST and VITE_DATABRICKS_TOKEN to .env
        </div>
      )}

      {tab === 'dashboard'    && <DashboardTab />}
      {tab === 'live'         && <LiveWeatherTab />}
      {tab === 'ml'           && <MLTab />}
      {tab === 'pipeline'     && <PipelineTab />}
      {tab === 'data-layers'  && <DataLayersTab />}
      {tab === 'workflows'    && <WorkflowsTab />}
    </Layout>
  )
}