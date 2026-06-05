/**
 * proxy.cjs — đặt tại: weather-dashboard/proxy.cjs
 *
 * Chạy trên Render Web Service, forward 2 route:
 *   /api/databricks/* → Databricks REST API
 *   /api/weather/*    → Open-Meteo API
 */

const https = require('https')
const http  = require('http')

const DATABRICKS_HOST = (process.env.DATABRICKS_HOST || '').replace('https://', '').replace('http://', '').replace(/\/$/, '')
const DATABRICKS_TOKEN = process.env.DATABRICKS_TOKEN || ''
const PORT = process.env.PORT || 3001

function setCORS(res) {
  res.setHeader('Access-Control-Allow-Origin',  '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')
}

function forward({ res, hostname, path, method, body, extraHeaders = {} }) {
  const options = {
    hostname,
    path,
    method,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  }

  const req = https.request(options, (r) => {
    res.writeHead(r.statusCode, { 'Content-Type': 'application/json' })
    r.pipe(res)
  })

  req.on('error', (e) => {
    console.error('Proxy error:', e.message)
    res.writeHead(502)
    res.end(JSON.stringify({ error: e.message }))
  })

  if (body) req.write(body)
  req.end()
}

http.createServer((req, res) => {
  setCORS(res)

  // Preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204)
    res.end()
    return
  }

  let body = ''
  req.on('data', chunk => { body += chunk })
  req.on('end', () => {

    // ── Route 1: /api/databricks/* → Databricks ──────────────────────────────
    if (req.url.startsWith('/api/databricks')) {
      const path = req.url.replace('/api/databricks', '')
      forward({
        res,
        hostname: DATABRICKS_HOST,
        path,
        method: req.method,
        body,
        extraHeaders: { Authorization: `Bearer ${DATABRICKS_TOKEN}` },
      })
      return
    }

    // ── Route 2: /api/weather/* → Open-Meteo ─────────────────────────────────
    if (req.url.startsWith('/api/weather')) {
      const path = req.url.replace('/api/weather', '')
      forward({
        res,
        hostname: 'api.open-meteo.com',
        path,
        method: req.method,
        body,
      })
      return
    }

    // ── Health check ──────────────────────────────────────────────────────────
    if (req.url === '/health') {
      res.writeHead(200)
      res.end(JSON.stringify({ status: 'ok', databricks: !!DATABRICKS_HOST }))
      return
    }

    res.writeHead(404)
    res.end(JSON.stringify({ error: 'Not found' }))
  })

}).listen(PORT, () => {
  console.log(`Proxy running on port ${PORT}`)
  console.log(`Databricks host: ${DATABRICKS_HOST || '(not set)'}`)
})
