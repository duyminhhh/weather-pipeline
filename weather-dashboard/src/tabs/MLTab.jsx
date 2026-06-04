import { useState } from 'react'
import { useMl } from '../hooks/useData'
import { Card, StatBox, SectionHead, Btn, Spinner, Alert, Table } from '../components/UI'
import { PredChart, HBarChart, SimpleBar } from '../components/Charts'

function fmt(v, d = 3) { const n = parseFloat(v); return isNaN(n) ? '—' : n.toFixed(d) }

export default function MLTab() {
  const { metrics, preds, featImp, forecast } = useMl()
  const [selCity, setSelCity] = useState('')
  const [topN, setTopN] = useState(20)

  const metricsRows = metrics.data ?? []
  const predsRows = preds.data ?? []
  const featRows = featImp.data?.slice(0, topN) ?? []
  const forecastRows = forecast.data ?? []

  const best = metricsRows[0] ?? {}
  const cities = [...new Set(predsRows.map(r => r.city))].sort()
  const city = selCity || cities[0] || ''
  const cityPreds = predsRows.filter(r => r.city === city)

  return (
    <div>
      {/* KPIs */}
      {metricsRows.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12, marginBottom: 20 }}>
          <StatBox label="Best Model"   value={best.model ?? '—'} accent />
          <StatBox label="RMSE (test)"  value={best.rmse_test ? `${fmt(best.rmse_test)}°C` : '—'} />
          <StatBox label="MAE (test)"   value={best.mae_test  ? `${fmt(best.mae_test)}°C`  : '—'} />
          <StatBox label="R² Score"     value={best.r2_test   ? fmt(best.r2_test)            : '—'} />
          <StatBox label="Within ±1°C" value={best.within_1deg_pct ? `${parseFloat(best.within_1deg_pct).toFixed(1)}%` : '—'} />
        </div>
      )}

      {metrics.loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: 12, padding: '16px 0' }}>
          <Spinner /> Loading ML data…
        </div>
      )}
      {metrics.error && <Alert type="warn">ML data unavailable — run notebook 04_ml_train first.</Alert>}
      {!metrics.loading && metricsRows.length === 0 && !metrics.error && (
        <Alert type="info">No ML results yet — run notebook 04_ml_train first.</Alert>
      )}

      {metricsRows.length > 0 && (
        <>
          {/* Model comparison table */}
          <SectionHead>Model Comparison</SectionHead>
          <Card style={{ marginBottom: 20 }}>
            <Table rows={metricsRows.map(r => ({
              Model: r.model,
              'RMSE Train': fmt(r.rmse_train),
              'RMSE Test': fmt(r.rmse_test),
              'MAE Test': fmt(r.mae_test),
              'R² Test': fmt(r.r2_test),
              'Within±1°': r.within_1deg_pct ? `${parseFloat(r.within_1deg_pct).toFixed(1)}%` : '—',
            }))} />
          </Card>

          {/* Model metrics bar chart */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            <Card>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>RMSE by Model</div>
              <SimpleBar data={metricsRows} dataKey="rmse_test" xKey="model" color="#f05252" unit="°" height={220} label="RMSE" />
            </Card>
            <Card>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 1 }}>R² by Model</div>
              <SimpleBar data={metricsRows} dataKey="r2_test" xKey="model" color="#3dd68c" height={220} label="R²" />
            </Card>
          </div>
        </>
      )}

      {predsRows.length > 0 && (
        <>
          {/* Actual vs Predicted */}
          <SectionHead>Actual vs Predicted</SectionHead>
          <Card style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              {cities.map(c => (
                <button key={c} onClick={() => setSelCity(c)} style={{
                  padding: '4px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
                  border: `1px solid ${city === c ? 'var(--accent)' : 'var(--border)'}`,
                  background: city === c ? 'rgba(79,156,249,0.12)' : 'transparent',
                  color: city === c ? 'var(--accent)' : 'var(--text2)',
                  fontFamily: 'var(--mono)', transition: 'all 0.12s',
                }}>{c}</button>
              ))}
            </div>
            <PredChart data={cityPreds} height={300} />
          </Card>
        </>
      )}

      {featRows.length > 0 && (
        <>
          <SectionHead action={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 11, color: 'var(--text2)' }}>Top</span>
              <input type="range" min={5} max={Math.min(50, (featImp.data?.length ?? 20))} value={topN}
                onChange={e => setTopN(+e.target.value)}
                style={{ width: 100, accentColor: 'var(--accent)' }} />
              <span style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--accent)' }}>{topN}</span>
            </div>
          }>Feature Importance</SectionHead>
          <Card style={{ marginBottom: 20 }}>
            <HBarChart data={featRows} height={Math.max(200, topN * 22)} color="#4f9cf9" />
          </Card>
        </>
      )}

      {forecastRows.length > 0 && (
        <>
          <SectionHead>Next Day Forecast</SectionHead>
          <Card>
            <Table rows={forecastRows.map(r => ({
              City: `${r.country || ''} ${r.city}`,
              'Avg Temp': r.avg_temp_c ? `${parseFloat(r.avg_temp_c).toFixed(1)}°C` : '—',
              'Forecast Temp': r.forecast_temp_next_day ? `${parseFloat(r.forecast_temp_next_day).toFixed(1)}°C` : '—',
              'Forecast Date': r.forecast_date,
              'Avg Humidity': r.avg_humidity ? `${parseFloat(r.avg_humidity).toFixed(0)}%` : '—',
              'Wind': r.avg_wind_speed_kmh ? `${parseFloat(r.avg_wind_speed_kmh).toFixed(0)} km/h` : '—',
            }))} />
          </Card>
        </>
      )}
    </div>
  )
}
