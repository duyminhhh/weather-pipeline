/**
 * api.js — tất cả request đều đi qua Vite proxy (/api/databricks, /api/weather)
 * → Không bao giờ bị CORS block khi dùng `npm run dev`
 */

const TOKEN     = import.meta.env.VITE_DATABRICKS_TOKEN     || ''
const WAREHOUSE = import.meta.env.VITE_DATABRICKS_WAREHOUSE || ''
const CATALOG   = 'workspace'
const SCHEMA    = 'weather_pipeline'

function tbl(name) { return `${CATALOG}.${SCHEMA}.${name}` }

function dbHeaders() {
  return {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json',
  }
}

// ── Databricks REST helpers ──────────────────────────────────────────────────
export async function dbGet(path, params = {}) {
  const url = new URL('/api/databricks' + path, window.location.origin)
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  const r = await fetch(url.toString(), { headers: dbHeaders() })
  if (!r.ok) throw new Error(`GET ${path} → ${r.status}`)
  return r.json()
}

export async function dbPost(path, body = {}) {
  const r = await fetch('/api/databricks' + path, {
    method: 'POST',
    headers: dbHeaders(),
    body: JSON.stringify(body),
  })
  if (!r.ok) {
    const txt = await r.text()
    throw new Error(`POST ${path} → ${r.status}: ${txt}`)
  }
  return r.json()
}

// ── SQL Statement Execution API (polling) ────────────────────────────────────
export async function runSQL(query, timeoutMs = 60_000) {
  if (!WAREHOUSE) return null

  const resp = await dbPost('/api/2.0/sql/statements', {
    warehouse_id: WAREHOUSE,
    statement: query,
    wait_timeout: '30s',
    on_wait_timeout: 'CONTINUE',
    format: 'JSON_ARRAY',
    disposition: 'INLINE',
  })

  let data = resp
  const deadline = Date.now() + timeoutMs

  while (['PENDING', 'RUNNING'].includes(data?.status?.state)) {
    if (Date.now() > deadline) throw new Error('SQL timeout')
    await new Promise(r => setTimeout(r, 1500))
    data = await dbGet(`/api/2.0/sql/statements/${data.statement_id}`)
  }

  if (data?.status?.state !== 'SUCCEEDED') {
    throw new Error(`SQL failed: ${data?.status?.state}`)
  }

  const cols = data?.manifest?.schema?.columns?.map(c => c.name) ?? []
  const rows = data?.result?.data_array ?? []
  return rows.map(r => Object.fromEntries(cols.map((c, i) => [c, r[i]])))
}

// ── Named queries ─────────────────────────────────────────────────────────────
export const Queries = {
  goldLatest:    () => runSQL(`SELECT * FROM ${tbl('gold_weather_latest')} ORDER BY temperature_c DESC`),
  goldStats:     () => runSQL(`SELECT * FROM ${tbl('gold_city_stats')} ORDER BY overall_avg_temp DESC`),
  goldDailyAll:  () => runSQL(`SELECT city, date, avg_temp_c, avg_precipitation_mm, avg_uv_index FROM ${tbl('gold_weather_daily')} ORDER BY date ASC`),
  goldDailyCity: (city) => runSQL(`SELECT * FROM ${tbl('gold_weather_daily')} WHERE city = '${city}' ORDER BY date ASC`),
  mlMetrics:     () => runSQL(`SELECT * FROM ${tbl('ml_model_metrics')} ORDER BY rmse_test ASC`),
  mlPredictions: () => runSQL(`SELECT * FROM ${tbl('ml_predictions_full')} ORDER BY date ASC`),
  mlFeatureImp:  () => runSQL(`SELECT * FROM ${tbl('ml_feature_importance')} ORDER BY importance DESC`),
  mlForecast:    () => runSQL(`SELECT * FROM ${tbl('gold_forecast_next_day')} ORDER BY forecast_temp_next_day DESC`),
  saveSnapshot:  (values) => runSQL(`INSERT INTO ${tbl('live_weather_snapshots')} VALUES ${values}`),
}

// ── Databricks Jobs API ───────────────────────────────────────────────────────
export async function getJobId(name = 'weather-pipeline') {
  const data = await dbGet('/api/2.1/jobs/list')
  const job = data.jobs?.find(j => j.settings?.name === name)
  return job?.job_id ?? null
}

export async function triggerJob(jobId) {
  return dbPost('/api/2.1/jobs/run-now', { job_id: jobId })
}

export async function listRuns(jobId) {
  return dbGet('/api/2.1/jobs/runs/list', { job_id: jobId, limit: 15 })
}

export async function getRun(runId) {
  return dbGet('/api/2.1/jobs/runs/get', { run_id: runId })
}

export async function listClusters() {
  const data = await dbGet('/api/2.0/clusters/list')
  return (data.clusters ?? []).filter(c => c.state === 'RUNNING')
}

export async function submitNotebook(clusterId, notebookPath) {
  return dbPost('/api/2.1/jobs/runs/submit', {
    run_name: `manual_${notebookPath.split('/').pop()}`,
    existing_cluster_id: clusterId,
    notebook_task: { notebook_path: notebookPath },
  })
}

// ── Open-Meteo (Live weather qua proxy) ──────────────────────────────────────
const WMO = {
  0: '☀️ Clear', 1: '🌤 Mainly clear', 2: '⛅ Partly cloudy', 3: '☁️ Overcast',
  45: '🌫 Fog', 48: '🌫 Icy fog',
  51: '🌦 Light drizzle', 53: '🌦 Drizzle', 55: '🌧 Heavy drizzle',
  61: '🌧 Slight rain', 63: '🌧 Moderate rain', 65: '🌧 Heavy rain',
  71: '🌨 Slight snow', 73: '🌨 Moderate snow', 75: '❄️ Heavy snow',
  80: '🌦 Showers', 81: '🌧 Rain showers', 82: '⛈ Violent showers',
  95: '⛈ Thunderstorm', 96: '⛈ Thunderstorm+hail', 99: '⛈ Heavy thunderstorm',
}

export async function fetchLiveWeather(cities) {
  const results = await Promise.allSettled(cities.map(async c => {
    const params = new URLSearchParams({
      latitude: c.lat, longitude: c.lon,
      current: 'temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,surface_pressure,wind_speed_10m,cloud_cover,visibility',
      daily: 'temperature_2m_max,temperature_2m_min',
      timezone: 'auto',
      forecast_days: 1,
    })
    const r = await fetch(`/api/weather/v1/forecast?${params}`)
    if (!r.ok) throw new Error('weather fetch failed')
    const j = await r.json()
    const cur = j.current ?? {}
    const dly = j.daily ?? {}
    return {
      city: c.city, flag: c.country, lat: c.lat, lon: c.lon,
      temp:     cur.temperature_2m,
      feels:    cur.apparent_temperature,
      humidity: cur.relative_humidity_2m,
      precip:   cur.precipitation,
      wind:     cur.wind_speed_10m,
      cloud:    cur.cloud_cover,
      vis:      cur.visibility,
      pressure: cur.surface_pressure,
      code:     cur.weather_code ?? 0,
      desc:     WMO[cur.weather_code ?? 0] ?? '?',
      tmax:     dly.temperature_2m_max?.[0] ?? null,
      tmin:     dly.temperature_2m_min?.[0] ?? null,
    }
  }))
  return results.filter(r => r.status === 'fulfilled').map(r => r.value)
}

export const CITIES = [
  { city: 'Ho Chi Minh City', country: '🇻🇳', lat: 10.8231,  lon: 106.6297 },
  { city: 'Hanoi',            country: '🇻🇳', lat: 21.0285,  lon: 105.8542 },
  { city: 'Da Nang',          country: '🇻🇳', lat: 16.0544,  lon: 108.2022 },
  { city: 'Tokyo',            country: '🇯🇵', lat: 35.6762,  lon: 139.6503 },
  { city: 'London',           country: '🇬🇧', lat: 51.5074,  lon: -0.1278  },
  { city: 'New York',         country: '🇺🇸', lat: 40.7128,  lon: -74.006  },
  { city: 'Paris',            country: '🇫🇷', lat: 48.8566,  lon: 2.3522   },
  { city: 'Sydney',           country: '🇦🇺', lat: -33.8688, lon: 151.2093 },
  { city: 'Dubai',            country: '🇦🇪', lat: 25.2048,  lon: 55.2708  },
  { city: 'Singapore',        country: '🇸🇬', lat: 1.3521,   lon: 103.8198 },
  { city: 'Bangkok',          country: '🇹🇭', lat: 13.7563,  lon: 100.5018 },
  { city: 'Mumbai',           country: '🇮🇳', lat: 19.0760,  lon: 72.8777  },
  { city: 'Seoul',            country: '🇰🇷', lat: 37.5665,  lon: 126.9780 },
  { city: 'Berlin',           country: '🇩🇪', lat: 52.5200,  lon: 13.4050  },
  { city: 'São Paulo',        country: '🇧🇷', lat: -23.5505, lon: -46.6333 },
]
