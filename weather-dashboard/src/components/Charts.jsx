import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, Cell,
} from 'recharts'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#0c0f14', border: '1px solid #4f9cf9',
    borderRadius: 6, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
    color: '#d8dde8',
  },
  labelStyle: { color: '#7bc8f6', fontSize: 10 },
  itemStyle: { color: '#d8dde8' },
  cursor: { fill: 'rgba(79,156,249,0.08)' },
}

function fmt(val, digits = 1) {
  if (val == null) return '—'
  const n = parseFloat(val)
  return isNaN(n) ? val : n.toFixed(digits)
}

function tempColor(t) {
  const v = parseFloat(t)
  if (isNaN(v)) return '#4f9cf9'
  if (v >= 38) return '#f05252'
  if (v >= 32) return '#f5a623'
  if (v >= 20) return '#4f9cf9'
  if (v >= 10) return '#22d3ee'
  return '#9b7ff4'
}

// ── Multi-line temperature chart ──────────────────────────────────────────────
function TempLineTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#0c0f14', border: '1px solid #4f9cf9', borderRadius: 6,
      padding: '10px 14px', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11,
    }}>
      <div style={{ color: '#7bc8f6', marginBottom: 8, fontSize: 10, letterSpacing: 1 }}>
        📅 {label}
      </div>
      {payload.map((p, i) => {
        const icons = { 'Avg': '🌡', 'Max': '🔺', 'Min': '🔻' }
        return (
          <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
            <span style={{ color: p.color }}>{icons[p.name] || '•'} {p.name}</span>
            <span style={{ color: '#d8dde8', fontWeight: 600 }}>
              {p.value != null ? `${parseFloat(p.value).toFixed(1)}°C` : '—'}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function TempLineChart({ data, height = 260 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" />
        <Tooltip content={<TempLineTooltip />} cursor={{ stroke: 'rgba(79,156,249,0.3)', strokeWidth: 1 }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#7a8399' }} />
        <Line type="monotone" dataKey="avg_temp_c" stroke="#4f9cf9" strokeWidth={2} dot={false} name="Avg" />
        <Line type="monotone" dataKey="temp_max_c"  stroke="#f5a623" strokeWidth={1.5} dot={false} name="Max" strokeDasharray="4 2" />
        <Line type="monotone" dataKey="temp_min_c"  stroke="#9b7ff4" strokeWidth={1.5} dot={false} name="Min" strokeDasharray="4 2" />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Bar chart with custom color per bar ───────────────────────────────────────
function CustomBarLabel({ x, y, width, value, name }) {
  const words = (name || '').split(' ')
  return (
    <g transform={`translate(${x + width / 2},${y + 4})`}>
      <text
        transform="rotate(-55)"
        textAnchor="end"
        fill="#94a3b8"
        fontSize={9}
        fontFamily="'IBM Plex Mono', monospace"
      >
        {words.map((w, i) => (
          <tspan key={i} x={0} dy={i === 0 ? 0 : 11}>{w}</tspan>
        ))}
      </text>
    </g>
  )
}

export function TempBarChart({ data, height = 320 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 80, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis
          dataKey="city"
          interval={0}
          tick={({ x, y, payload }) => (
            <g transform={`translate(${x},${y})`}>
              <text
                transform="rotate(-40)"
                textAnchor="end"
                fill="#94a3b8"
                fontSize={9}
                fontFamily="'IBM Plex Mono', monospace"
                dy={4}
              >
                {payload.value}
              </text>
            </g>
          )}
        />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)}°C`]} labelFormatter={(l) => `📍 ${l}`} />
        <Bar dataKey="temperature_c" name="Temp" radius={[3, 3, 0, 0]}>
          {data.map((d, i) => <Cell key={i} fill={tempColor(d.temperature_c)} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Area chart ────────────────────────────────────────────────────────────────
export function WindAreaChart({ data, height = 220 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <defs>
          <linearGradient id="windGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3dd68c" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#3dd68c" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)} km/h`]} />
        <Area type="monotone" dataKey="avg_wind_speed_kmh" stroke="#3dd68c" fill="url(#windGrad)" strokeWidth={2} name="Wind" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ── Simple bar chart ──────────────────────────────────────────────────────────
export function SimpleBar({ data, dataKey, color = '#4f9cf9', xKey = 'date', unit = '', height = 220, label }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice?.(5) ?? v} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit={unit} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)}${unit}`, label || dataKey]} />
        <Bar dataKey={dataKey} fill={color} radius={[2, 2, 0, 0]} name={label || dataKey} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Multi-line comparison chart ───────────────────────────────────────────────
const LINE_COLORS = ['#4f9cf9','#3dd68c','#f5a623','#9b7ff4','#f05252','#7bc8f6']

function MultiLineTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#0c0f14', border: '1px solid #4f9cf9', borderRadius: 6,
      padding: '10px 14px', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11,
    }}>
      <div style={{ color: '#7bc8f6', marginBottom: 8, fontSize: 10, letterSpacing: 1 }}>
        📅 {label}
      </div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
          <span style={{ color: p.color }}>🌍 {p.name}</span>
          <span style={{ color: '#d8dde8', fontWeight: 600 }}>
            {p.value != null ? `${parseFloat(p.value).toFixed(1)}°C` : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

export function MultiLineChart({ data, lines, xKey = 'date', height = 260, unit = '' }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice?.(5) ?? v} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit={unit} />
        <Tooltip content={<MultiLineTooltip />} cursor={{ stroke: 'rgba(79,156,249,0.3)', strokeWidth: 1 }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#7a8399' }} />
        {lines.map((l, i) => (
          <Line key={l} type="monotone" dataKey={l} stroke={LINE_COLORS[i % LINE_COLORS.length]}
            strokeWidth={1.5} dot={false} name={l} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Actual vs Predicted ───────────────────────────────────────────────────────
function PredTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  // Format date: trim the ISO timestamp to readable form
  const dateStr = label ? label.replace('T00:00:00.000Z', '').replace('T', ' ') : '—'
  const actual = payload.find(p => p.dataKey === 'target_next_temp')
  const predicted = payload.find(p => p.dataKey === 'predicted_temp')
  const diff = (actual?.value != null && predicted?.value != null)
    ? Math.abs(parseFloat(actual.value) - parseFloat(predicted.value)).toFixed(2)
    : null
  return (
    <div style={{
      background: '#0c0f14', border: '1px solid #4f9cf9', borderRadius: 6,
      padding: '10px 14px', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, minWidth: 180,
    }}>
      <div style={{ color: '#7bc8f6', marginBottom: 8, fontSize: 10, letterSpacing: 1 }}>
        📅 {dateStr}
      </div>
      {actual && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
          <span style={{ color: '#7a8399' }}>🌡 Thực tế</span>
          <span style={{ color: '#d8dde8', fontWeight: 600 }}>
            {actual.value != null ? `${parseFloat(actual.value).toFixed(1)}°C` : '—'}
          </span>
        </div>
      )}
      {predicted && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
          <span style={{ color: '#4f9cf9' }}>🤖 Dự đoán</span>
          <span style={{ color: '#4f9cf9', fontWeight: 600 }}>
            {predicted.value != null ? `${parseFloat(predicted.value).toFixed(1)}°C` : '—'}
          </span>
        </div>
      )}
      {diff != null && (
        <div style={{
          marginTop: 8, paddingTop: 6, borderTop: '1px solid rgba(79,156,249,0.2)',
          display: 'flex', justifyContent: 'space-between', gap: 16,
        }}>
          <span style={{ color: 'var(--text3)' }}>Sai số</span>
          <span style={{
            fontWeight: 700,
            color: parseFloat(diff) <= 1 ? '#3dd68c' : parseFloat(diff) <= 2 ? '#f5a623' : '#f05252',
          }}>±{diff}°C</span>
        </div>
      )}
    </div>
  )
}

export function PredChart({ data, height = 320 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice(5, 10)} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" />
        <Tooltip content={<PredTooltip />} cursor={{ stroke: 'rgba(79,156,249,0.3)', strokeWidth: 1 }} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#7a8399' }} />
        <Line type="monotone" dataKey="target_next_temp"        stroke="#7a8399" strokeWidth={1.5} dot={false} name="Actual" />
        <Line type="monotone" dataKey="predicted_temp"          stroke="#4f9cf9" strokeWidth={2}   dot={false} name="Predicted" strokeDasharray="5 3" />
        <Line type="monotone" dataKey="forecast_temp_next_day"  stroke="#3dd68c" strokeWidth={2}   dot={false} name="Forecast" strokeDasharray="3 3" />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Horizontal bar (feature importance) ──────────────────────────────────────
export function HBarChart({ data, dataKey = 'importance', labelKey = 'feature', height, color = '#4f9cf9' }) {
  if (!data?.length) return null
  const h = height || Math.max(200, data.length * 24)
  return (
    <ResponsiveContainer width="100%" height={h}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 20, bottom: 4, left: 100 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#4a5268', fontSize: 10 }} />
        <YAxis type="category" dataKey={labelKey} tick={{ fill: '#7a8399', fontSize: 10 }} width={95} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [fmt(v, 4)]} />
        <Bar dataKey={dataKey} fill={color} radius={[0, 2, 2, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Humidity radar ────────────────────────────────────────────────────────────
export function HumidityRadar({ data, height = 320 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data}>
        <PolarGrid stroke="#1a1f2e" />
        <PolarAngleAxis dataKey="city" tick={{ fill: '#7a8399', fontSize: 10 }} />
        <Radar name="Humidity" dataKey="humidity" stroke="#4f9cf9" fill="#4f9cf9" fillOpacity={0.2} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v, 0)}%`]} />
      </RadarChart>
    </ResponsiveContainer>
  )
}
// ── Next Day Forecast line chart ──────────────────────────────────────────────
function ForecastTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: '#0c0f14', border: '1px solid #3dd68c', borderRadius: 6,
      padding: '10px 14px', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, minWidth: 180,
    }}>
      <div style={{ color: '#3dd68c', marginBottom: 8, fontSize: 10, letterSpacing: 1 }}>
        📍 {label}
      </div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
          <span style={{ color: p.color }}>{p.name === 'Avg Temp' ? '🌡' : '🤖'} {p.name}</span>
          <span style={{ color: '#d8dde8', fontWeight: 600 }}>
            {p.value != null ? `${parseFloat(p.value).toFixed(1)}°C` : '—'}
          </span>
        </div>
      ))}
    </div>
  )
}

export function ForecastLineChart({ data, height = 320 }) {
  if (!data?.length) return null
  // Sort by forecast_temp_next_day desc để thấy rõ độ chênh
  const sorted = [...data].sort((a, b) => (b.forecast_temp_next_day ?? 0) - (a.forecast_temp_next_day ?? 0))
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={sorted} margin={{ top: 4, right: 8, bottom: 90, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis
          dataKey="city"
          interval={0}
          tick={({ x, y, payload }) => (
            <g transform={`translate(${x},${y})`}>
              <text
                transform="rotate(-40)"
                textAnchor="end"
                fill="#94a3b8"
                fontSize={9}
                fontFamily="'IBM Plex Mono', monospace"
                dy={4}
              >
                {payload.value}
              </text>
            </g>
          )}
        />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" domain={['auto', 'auto']} />
        <Tooltip
          contentStyle={{ background: '#0c0f14', border: '1px solid #3dd68c', borderRadius: 6, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}
          labelStyle={{ color: '#3dd68c', fontSize: 10 }}
          formatter={(v, name) => [`${parseFloat(v).toFixed(1)}°C`, name]}
          labelFormatter={(l) => `📍 ${l}`}
        />
        <Legend wrapperStyle={{ fontSize: 11, color: '#7a8399', paddingTop: 8 }} />
        <Bar dataKey="avg_temp_c"              name="Avg Temp"     fill="#4f9cf9" radius={[2,2,0,0]} />
        <Bar dataKey="forecast_temp_next_day"  name="Forecast"     fill="#3dd68c" radius={[2,2,0,0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}