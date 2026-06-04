import { useState } from 'react'
import { useDashboard } from '../hooks/useData'
import { useQuery } from '../hooks/useData'
import { Queries } from '../api'
import { Card, StatBox, SectionHead, Btn, Badge, Spinner, Alert, PipeNode } from '../components/UI'
import { TempBarChart, SimpleBar, TempLineChart, WindAreaChart, MultiLineChart } from '../components/Charts'

function fmt(v, d = 1) {
  const n = parseFloat(v)
  return isNaN(n) ? '—' : n.toFixed(d)
}

function tempColor(t) {
  const v = parseFloat(t)
  if (isNaN(v)) return 'var(--text2)'
  if (v >= 38) return '#f05252'
  if (v >= 32) return '#f5a623'
  if (v >= 20) return '#4f9cf9'
  if (v >= 10) return '#22d3ee'
  return '#9b7ff4'
}

function CityCard({ row, selected, onSelect }) {
  const tc = tempColor(row.temperature_c)
  const flag = row.country || ''
  return (
    <div onClick={onSelect} style={{
      background: selected ? 'rgba(79,156,249,0.07)' : 'var(--bg1)',
      border: `1px solid ${selected ? 'var(--accent)' : 'var(--border)'}`,
      borderRadius: 'var(--radius-lg)', padding: '14px 16px', cursor: 'pointer',
      transition: 'all 0.15s',
      boxShadow: selected ? '0 0 16px rgba(79,156,249,0.12)' : 'none',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>
            {flag} {row.city}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text2)' }}>{row.weather_desc || '—'}</div>
        </div>
        <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 22, color: tc, lineHeight: 1 }}>
          {fmt(row.temperature_c)}°
        </div>
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
        <Badge color="gray">💧{fmt(row.humidity, 0)}%</Badge>
        <Badge color="gray">💨{fmt(row.wind_speed_kmh, 0)}km/h</Badge>
        <Badge color="gray">☁️{fmt(row.cloud_cover_pct, 0)}%</Badge>
        <Badge color="amber">feels {fmt(row.feels_like_c)}°</Badge>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
        <Badge color="blue">↑{fmt(row.temp_max_c)}°</Badge>
        <Badge color="blue">↓{fmt(row.temp_min_c)}°</Badge>
      </div>
    </div>
  )
}

function CityDetail({ city, onClose }) {
  const { data, loading, error } = useQuery(() => Queries.goldDailyCity(city), [city])

  return (
    <div style={{
      background: 'var(--bg1)', border: '1px solid var(--accent)',
      borderRadius: 'var(--radius-lg)', padding: '18px 20px', marginBottom: 20,
      boxShadow: '0 0 32px rgba(79,156,249,0.08)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: 14, color: 'var(--accent)' }}>
          ◎ {city} — Historical
        </span>
        <Btn small onClick={onClose}>✕ Close</Btn>
      </div>
      {loading && <div style={{ textAlign: 'center', padding: 24 }}><Spinner /></div>}
      {error && <Alert type="warn">No historical data: {error}</Alert>}
      {data && data.length === 0 && <Alert type="info">Run pipeline first to get historical data.</Alert>}
      {data && data.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Temperature (°C)</div>
            <TempLineChart data={data} height={220} />
          </div>
          <div>
            <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Humidity (%)</div>
            <SimpleBar data={data} dataKey="avg_humidity" color="#4f9cf9" unit="%" height={220} xKey="date" />
          </div>
          <div>
            <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Wind Speed (km/h)</div>
            <WindAreaChart data={data} height={200} />
          </div>
          <div>
            <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 1 }}>Precipitation (mm)</div>
            <SimpleBar data={data} dataKey="avg_precipitation_mm" color="#9b7ff4" unit="mm" height={200} xKey="date" />
          </div>
        </div>
      )}
    </div>
  )
}

export default function DashboardTab() {
  const { latest, dailyAll } = useDashboard()
  const [selectedCity, setSelectedCity] = useState(null)
  const [histCities, setHistCities] = useState([])

  const rows = latest.data ?? []
  const hottest = rows.reduce((a, b) => parseFloat(a.temperature_c) > parseFloat(b.temperature_c) ? a : b, rows[0] || {})
  const coldest = rows.reduce((a, b) => parseFloat(a.temperature_c) < parseFloat(b.temperature_c) ? a : b, rows[0] || {})
  const avgTemp = rows.length ? rows.reduce((s, r) => s + parseFloat(r.temperature_c || 0), 0) / rows.length : null

  // Build multi-city line chart data
  const dailyRows = dailyAll.data ?? []
  const allCities = [...new Set(dailyRows.map(r => r.city))].sort()
  const selCities = histCities.length ? histCities : allCities.slice(0, 5)
  const pivoted = {}
  dailyRows.forEach(r => {
    if (!selCities.includes(r.city)) return
    if (!pivoted[r.date]) pivoted[r.date] = { date: r.date }
    pivoted[r.date][r.city] = parseFloat(r.avg_temp_c)
  })
  const multiData = Object.values(pivoted).sort((a, b) => a.date.localeCompare(b.date))

  return (
    <div>
      {/* Pipeline flow */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        background: 'var(--bg1)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: '12px 18px',
        marginBottom: 20, overflowX: 'auto',
      }}>
        <PipeNode icon="🕷️" label="Crawler" color="indigo" />
        <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)' }}>→</span>
        <PipeNode icon="🟤" label="Bronze" color="amber" />
        <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)' }}>→</span>
        <PipeNode icon="🥈" label="Silver" color="gray" />
        <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)' }}>→</span>
        <PipeNode icon="🥇" label="Gold" color="gold" />
        <span style={{ color: 'var(--border2)', fontFamily: 'var(--mono)' }}>→</span>
        <PipeNode icon="🤖" label="ML" color="purple" />
      </div>

      {/* KPI row */}
      {rows.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
          <StatBox label="Cities Tracked" value={rows.length} accent />
          <StatBox label="🌡 Hottest" value={hottest.city} sub={`${fmt(hottest.temperature_c)}°C`} />
          <StatBox label="🧊 Coldest" value={coldest.city} sub={`${fmt(coldest.temperature_c)}°C`} />
          <StatBox label="Global Avg" value={avgTemp ? `${fmt(avgTemp)}°C` : '—'} />
        </div>
      )}

      {/* Loading / Error */}
      {latest.loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: 12, padding: '20px 0' }}>
          <Spinner /> Loading Databricks data…
        </div>
      )}
      {latest.error && <Alert type="warn" style={{ marginBottom: 16 }}>SQL error: {latest.error}</Alert>}
      {!latest.loading && rows.length === 0 && !latest.error && (
        <Alert type="info">No data yet — run the pipeline first (Pipeline tab).</Alert>
      )}

      {rows.length > 0 && (
        <>
          {/* City grid */}
          <SectionHead action={
            <Btn small onClick={() => { latest.refetch(); dailyAll.refetch() }}>↻ Refresh</Btn>
          }>Current Conditions — click city for details</SectionHead>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10, marginBottom: 20 }}>
            {rows.map(r => (
              <CityCard key={r.city} row={r}
                selected={selectedCity === r.city}
                onSelect={() => setSelectedCity(selectedCity === r.city ? null : r.city)}
              />
            ))}
          </div>

          {selectedCity && <CityDetail city={selectedCity} onClose={() => setSelectedCity(null)} />}

          {/* Bar chart comparison */}
          <SectionHead>Temperature Comparison</SectionHead>
          <Card style={{ marginBottom: 20 }}>
            <TempBarChart data={rows} height={280} />
          </Card>

          {/* Historical trends */}
          {dailyAll.data && dailyAll.data.length > 0 && (
            <>
              <SectionHead>Historical Trends</SectionHead>
              <Card style={{ marginBottom: 20 }}>
                <div style={{ marginBottom: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {allCities.map(c => (
                    <button key={c} onClick={() => {
                      setHistCities(prev =>
                        prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]
                      )
                    }} style={{
                      padding: '3px 10px', borderRadius: 20, fontSize: 11,
                      border: `1px solid ${selCities.includes(c) ? 'var(--accent)' : 'var(--border)'}`,
                      background: selCities.includes(c) ? 'rgba(79,156,249,0.12)' : 'transparent',
                      color: selCities.includes(c) ? 'var(--accent)' : 'var(--text2)',
                      cursor: 'pointer', fontFamily: 'var(--mono)',
                    }}>{c}</button>
                  ))}
                </div>
                <MultiLineChart data={multiData} lines={selCities} height={280} unit="°" />
              </Card>
            </>
          )}
        </>
      )}
    </div>
  )
}
