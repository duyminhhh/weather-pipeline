/**
 * server.cjs — đặt tại: weather-dashboard/server.cjs
 *
 * 1 service duy nhất:
 *   - Serve static files từ /dist
 *   - /api/databricks/* → Databricks
 *   - /api/weather/*    → Open-Meteo
 *   - /* → index.html  (SPA fallback)
 */

const https = require('https')
const http  = require('http')
const fs    = require('fs')
const path  = require('path')

const DATABRICKS_HOST  = (process.env.DATABRICKS_HOST || '').replace(/https?:\/\//, '').replace(/\/$/, '')
const DATABRICKS_TOKEN = process.env.DATABRICKS_TOKEN || ''
const PORT             = process.env.PORT || 3000
const DIST             = path.join(__dirname, 'dist')

const MIME = {
  '.html': 'text/html',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
  '.json': 'application/json',
  '.woff2':'font/woff2',
}

function setCORS(res) {
  res.setHeader('Access-Control-Allow-Origin',  '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization')
}

function forward({ res, hostname, path, method, body, extraHeaders = {} }) {
  const opts = {
    hostname, path, method,
    headers: { 'Content-Type': 'application/json', ...extraHeaders },
  }
  const req = https.request(opts, r => {
    res.writeHead(r.statusCode, { 'Content-Type': 'application/json' })
    r.pipe(res)
  })
  req.on('error', e => { res.writeHead(502); res.end(JSON.stringify({ error: e.message })) })
  if (body) req.write(body)
  req.end()
}

function serveStatic(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      // SPA fallback → index.html
      fs.readFile(path.join(DIST, 'index.html'), (e, d) => {
        if (e) { res.writeHead(404); res.end('Not found'); return }
        res.writeHead(200, { 'Content-Type': 'text/html' })
        res.end(d)
      })
      return
    }
    const ext = path.extname(filePath)
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' })
    res.end(data)
  })
}

http.createServer((req, res) => {
  setCORS(res)

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return }

  let body = ''
  req.on('data', chunk => { body += chunk })
  req.on('end', () => {

    // ── Proxy: Databricks ──────────────────────────────────────────────────
    if (req.url.startsWith('/api/databricks')) {
      const p = req.url.replace('/api/databricks', '')
      forward({ res, hostname: DATABRICKS_HOST, path: p, method: req.method, body,
        extraHeaders: { Authorization: `Bearer ${DATABRICKS_TOKEN}` } })
      return
    }

    // ── Proxy: Open-Meteo ──────────────────────────────────────────────────
    if (req.url.startsWith('/api/weather')) {
      const p = req.url.replace('/api/weather', '')
      forward({ res, hostname: 'api.open-meteo.com', path: p, method: req.method, body })
      return
    }

    // ── Health check ───────────────────────────────────────────────────────
    if (req.url === '/health') {
      res.writeHead(200)
      res.end(JSON.stringify({ status: 'ok', databricks: !!DATABRICKS_HOST }))
      return
    }

    // ── Static files ───────────────────────────────────────────────────────
    const urlPath = req.url.split('?')[0]
    const filePath = path.join(DIST, urlPath === '/' ? 'index.html' : urlPath)
    serveStatic(res, filePath)
  })

}).listen(PORT, () => {
  console.log(`Server running on port ${PORT}`)
  console.log(`Databricks: ${DATABRICKS_HOST || '(not set)'}`)
})
