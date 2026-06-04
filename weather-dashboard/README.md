# WX / Weather Pipeline Dashboard

React + Vite frontend cho Databricks Weather Pipeline — thay thế hoàn toàn Streamlit.

## Tính năng

- **Dashboard** — KPI, city cards, historical trends, so sánh thành phố
- **Live Weather** — Open-Meteo real-time, radar chart, table
- **ML Insights** — Model metrics, Actual vs Predicted, Feature Importance, Forecast
- **Pipeline** — Trigger full job hoặc từng notebook
- **Workflows** — Lịch sử runs, check run_id

## Fix CORS

Tất cả request đến Databricks và Open-Meteo đều được route qua **Vite proxy** trong `vite.config.js`:

```
Browser → /api/databricks/... → Vite proxy → dbc-xxxxx.cloud.databricks.com
Browser → /api/weather/...    → Vite proxy → api.open-meteo.com
```

→ Browser không bao giờ gọi trực tiếp, không bị CORS block.

## Setup

```bash
# 1. Copy env
cp .env.example .env
# Điền VITE_DATABRICKS_HOST, VITE_DATABRICKS_TOKEN, VITE_DATABRICKS_WAREHOUSE

# 2. Cài dependencies
npm install

# 3. Chạy dev server
npm run dev
# → http://localhost:5173

# 4. Build production
npm run build
npm run preview
```

## Cấu trúc

```
src/
  api.js              # Tất cả API calls (Databricks + Open-Meteo)
  hooks/useData.js    # React hooks cho data fetching
  components/
    Layout.jsx        # Top nav
    UI.jsx            # Card, Btn, Badge, Table, Alert, ...
    Charts.jsx        # Recharts wrappers
  tabs/
    DashboardTab.jsx
    LiveWeatherTab.jsx
    MLTab.jsx
    PipelineTab.jsx
    WorkflowsTab.jsx
```

## .env.example

```
VITE_DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
VITE_DATABRICKS_TOKEN=your_token_here
VITE_DATABRICKS_WAREHOUSE=your_warehouse_id
```
