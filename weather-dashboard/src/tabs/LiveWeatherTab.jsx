import { useState, useEffect } from 'react'
import { CITIES, fetchLiveWeather } from '../api'
import { Card, SectionHead, Btn, Badge, Spinner, Alert } from '../components/UI'
import { HumidityRadar, SimpleBar } from '../components/Charts'

function fmt(v, d = 1) { const n = parseFloat(v); return isNaN(n) ? '—' : n.toFixed(d) }

function tempColor(t) {
  const v = parseFloat(t)
  if (isNaN(v)) return 'var(--text2)'
  if (v >= 38) return '#f05252'
  if (v >= 32) return '#f5a623'
  if (v >= 20) return '#4f9cf9'
  if (v >= 10) return '#22d3ee'
  return '#9b7ff4'
}

function LiveCard({ w }) {
  const tc = tempColor(w.temp)
  return (
    <div style={{
      background: 'var(--bg1)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', padding: '14px 16px',
      transition: 'border-color 0.15s',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>{w.flag} {w.city}</div>
          <div style={{ fontSize: 11, color: 'var(--text2)', marginTop: 2 }}>{w.desc}</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 24, fontWeight: 700, color: tc, lineHeight: 1 }}>
            {fmt(w.temp)}°
          </div>
          <div style={{ fontSize: 10, color: 'var(--text3)', marginTop: 3, fontFamily: 'var(--mono)' }}>
            feels {fmt(w.feels)}°
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginTop: 12 }}>
        <div style={{ background: 'var(--bg2)', borderRadius: 'var(--radius)', padding: '6px 10px' }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)', letterSpacing: 1, textTransform: 'uppercase' }}>Humidity</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 14, fontWeight: 600, color: 'var(--accent2)' }}>{fmt(w.humidity, 0)}%</div>
        </div>
        <div style={{ background: 'var(--bg2)', borderRadius: 'var(--radius)', padding: '6px 10px' }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)', letterSpacing: 1, textTransform: 'uppercase' }}>Wind</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 14, fontWeight: 600, color: '#3dd68c' }}>{fmt(w.wind, 0)} km/h</div>
        </div>
        <div style={{ background: 'var(--bg2)', borderRadius: 'var(--radius)', padding: '6px 10px' }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)', letterSpacing: 1, textTransform: 'uppercase' }}>Cloud</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 14, fontWeight: 600, color: 'var(--text2)' }}>{fmt(w.cloud, 0)}%</div>
        </div>
        <div style={{ background: 'var(--bg2)', borderRadius: 'var(--radius)', padding: '6px 10px' }}>
          <div style={{ fontSize: 9, color: 'var(--text3)', fontFamily: 'var(--mono)', letterSpacing: 1, textTransform: 'uppercase' }}>Precip</div>
          <div style={{ fontFamily: 'var(--mono)', fontSize: 14, fontWeight: 600, color: '#9b7ff4' }}>{fmt(w.precip, 1)} mm</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
        <Badge color="amber">↑{w.tmax != null ? fmt(w.tmax) : '—'}°</Badge>
        <Badge color="blue">↓{w.tmin != null ? fmt(w.tmin) : '—'}°</Badge>
        {w.pressure && <Badge color="gray">{fmt(w.pressure, 0)} hPa</Badge>}
      </div>
    </div>
  )
}

export default function LiveWeatherTab() {
  const [selectedCities, setSelectedCities] = useState(CITIES.slice(0, 9).map(c => c.city))
  const [liveData, setLiveData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lastFetch, setLastFetch] = useState(null)

  async function loadWeather() {
    setLoading(true); setError(null)
    try {
      const cities = CITIES.filter(c => selectedCities.includes(c.city))
      const data = await fetchLiveWeather(cities)
      setLiveData(data)
      setLastFetch(new Date().toISOString().slice(11, 19) + ' UTC')
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadWeather() }, [selectedCities.join(',')])

  const toggleCity = (city) => {
    setSelectedCities(prev =>
      prev.includes(city) ? prev.filter(c => c !== city) : [...prev, city]
    )
  }

  return (
    <div>
      {/* City selector */}
      <Card style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)', letterSpacing: 2, textTransform: 'uppercase' }}>
            Select Cities
          </span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {lastFetch && (
              <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)' }}>
                fetched {lastFetch}
              </span>
            )}
            <Btn small primary onClick={loadWeather} disabled={loading}>
              {loading ? '…' : '↻ Refresh'}
            </Btn>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {CITIES.map(c => (
            <button key={c.city} onClick={() => toggleCity(c.city)} style={{
              padding: '4px 10px', borderRadius: 20, fontSize: 11, cursor: 'pointer',
              border: `1px solid ${selectedCities.includes(c.city) ? 'var(--accent)' : 'var(--border)'}`,
              background: selectedCities.includes(c.city) ? 'rgba(79,156,249,0.12)' : 'transparent',
              color: selectedCities.includes(c.city) ? 'var(--accent)' : 'var(--text2)',
              fontFamily: 'var(--mono)', transition: 'all 0.12s',
            }}>{c.country} {c.city}</button>
          ))}
        </div>
      </Card>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--text2)', fontFamily: 'var(--mono)', fontSize: 12, padding: '16px 0' }}>
          <Spinner /> Fetching live weather data…
        </div>
      )}
      {error && <Alert type="error">{error}</Alert>}

      {!loading && liveData.length > 0 && (
        <>
          <SectionHead>{liveData.length} cities · Open-Meteo</SectionHead>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 10, marginBottom: 20 }}>
            {liveData.map(w => <LiveCard key={w.city} w={w} />)}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
            <Card>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                Humidity Radar
              </div>
              <HumidityRadar data={liveData} height={300} />
            </Card>
            <Card>
              <div style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: 1 }}>
                Temperature Comparison
              </div>
              <SimpleBar
                data={liveData.map(w => ({ ...w, temperature_c: w.temp }))}
                dataKey="temperature_c" xKey="city"
                color="#4f9cf9" unit="°" height={300}
              />
            </Card>
          </div>

          {/* Summary table */}
          <SectionHead>Summary Table</SectionHead>
          <Card>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, fontFamily: 'var(--mono)' }}>
                <thead>
                  <tr>
                    {['City', 'Temp', 'Feels', 'Tmax', 'Tmin', 'Humidity', 'Wind', 'Cloud', 'Precip', 'Condition'].map(h => (
                      <th key={h} style={{ padding: '7px 10px', textAlign: 'left', color: 'var(--text3)', fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', borderBottom: '1px solid var(--border)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {liveData.map(w => (
                    <tr key={w.city} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '7px 10px' }}>{w.flag} {w.city}</td>
                      <td style={{ padding: '7px 10px', color: tempColor(w.temp), fontWeight: 600 }}>{fmt(w.temp)}°</td>
                      <td style={{ padding: '7px 10px', color: 'var(--text2)' }}>{fmt(w.feels)}°</td>
                      <td style={{ padding: '7px 10px', color: 'var(--amber)' }}>{fmt(w.tmax)}°</td>
                      <td style={{ padding: '7px 10px', color: 'var(--purple)' }}>{fmt(w.tmin)}°</td>
                      <td style={{ padding: '7px 10px' }}>{fmt(w.humidity, 0)}%</td>
                      <td style={{ padding: '7px 10px', color: '#3dd68c' }}>{fmt(w.wind, 0)} km/h</td>
                      <td style={{ padding: '7px 10px' }}>{fmt(w.cloud, 0)}%</td>
                      <td style={{ padding: '7px 10px' }}>{fmt(w.precip, 1)} mm</td>
                      <td style={{ padding: '7px 10px', color: 'var(--text2)' }}>{w.desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
