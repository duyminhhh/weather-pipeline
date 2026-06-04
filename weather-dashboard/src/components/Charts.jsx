import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, Cell,
} from 'recharts'

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#1a1f2e', border: '1px solid #242b3d',
    borderRadius: 6, fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
    color: '#d8dde8',
  },
  labelStyle: { color: '#7a8399', fontSize: 10 },
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
export function TempLineChart({ data, height = 260 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)}°C`]} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#7a8399' }} />
        <Line type="monotone" dataKey="avg_temp_c" stroke="#4f9cf9" strokeWidth={2} dot={false} name="Avg" />
        <Line type="monotone" dataKey="temp_max_c"  stroke="#f5a623" strokeWidth={1.5} dot={false} name="Max" strokeDasharray="4 2" />
        <Line type="monotone" dataKey="temp_min_c"  stroke="#9b7ff4" strokeWidth={1.5} dot={false} name="Min" strokeDasharray="4 2" />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Bar chart with custom color per bar ───────────────────────────────────────
export function TempBarChart({ data, height = 300 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, bottom: 40, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey="city" tick={{ fill: '#4a5268', fontSize: 10 }} angle={-35} textAnchor="end" interval={0} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)}°C`]} />
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
export function MultiLineChart({ data, lines, xKey = 'date', height = 260, unit = '' }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey={xKey} tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice?.(5) ?? v} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit={unit} />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)}${unit}`]} />
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
export function PredChart({ data, height = 320 }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
        <CartesianGrid stroke="#1a1f2e" strokeDasharray="3 3" />
        <XAxis dataKey="date" tick={{ fill: '#4a5268', fontSize: 10 }} tickFormatter={v => v?.slice(5)} />
        <YAxis tick={{ fill: '#4a5268', fontSize: 10 }} unit="°" />
        <Tooltip {...TOOLTIP_STYLE} formatter={(v) => [`${fmt(v)}°C`]} />
        <Legend wrapperStyle={{ fontSize: 11, color: '#7a8399' }} />
        <Line type="monotone" dataKey="target_next_temp" stroke="#7a8399"  strokeWidth={1.5} dot={false} name="Actual" />
        <Line type="monotone" dataKey="predicted_temp"   stroke="#4f9cf9"  strokeWidth={2}   dot={false} name="Predicted" strokeDasharray="5 3" />
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
