"""
Streamlit Weather Pipeline Dashboard — v4
Fix:
  1. Live weather: lỗi Timestamp integer arithmetic
  2. Backend dùng Databricks SQL Statement API (không cần thư viện ngoài)
  3. City detail charts: hiển thị đúng khi click
"""

import os
import time
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weather Pipeline",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #070e1a;
    color: #e2e8f0;
  }
  .main > div:first-child { padding-top: 0; }

  .stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: #0d1b2a; padding: 6px 8px;
    border-radius: 12px; border: 1px solid #1e3a5f;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 8px; color: #64748b;
    font-weight: 500; padding: 8px 18px; transition: all .2s;
  }
  .stTabs [aria-selected="true"] { background: #0f3460 !important; color: #38bdf8 !important; }

  [data-testid="metric-container"] {
    background: #0d1b2a; border: 1px solid #1e3a5f;
    border-radius: 12px; padding: 16px 20px;
  }
  [data-testid="metric-container"] label {
    color: #64748b !important; font-size: 0.78rem !important;
    text-transform: uppercase; letter-spacing: .06em;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #38bdf8 !important; font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem !important; font-weight: 600;
  }

  .stButton > button {
    background: linear-gradient(135deg, #0f3460, #1a5276);
    border: 1px solid #38bdf8; border-radius: 8px; color: #38bdf8;
    font-weight: 600; transition: all .2s;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #1a5276, #217dbb);
    box-shadow: 0 0 16px rgba(56,189,248,.25); transform: translateY(-1px);
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0369a1, #0284c7);
    border-color: #7dd3fc; color: #fff;
  }
  .stSelectbox > div, .stMultiSelect > div { background: #0d1b2a; border-color: #1e3a5f; }
  .stTextInput input { background: #0d1b2a; border-color: #1e3a5f; color: #e2e8f0; }
  [data-testid="stDataFrame"] { border: 1px solid #1e3a5f; border-radius: 10px; overflow: hidden; }
  hr { border-color: #1e3a5f; }

  .city-card {
    background: linear-gradient(135deg, #0d1b2a, #0f2744);
    border: 1px solid #1e3a5f; border-radius: 14px;
    padding: 18px 20px; margin-bottom: 8px; transition: border-color .2s;
  }
  .city-card:hover  { border-color: #38bdf8; }
  .city-card.sel    { border-color: #38bdf8; box-shadow: 0 0 20px rgba(56,189,248,.15); }
  .city-temp  { font-size: 2.2rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1; }
  .city-name  { font-size: 1rem;   font-weight: 600; color: #e2e8f0; }
  .city-desc  { font-size: 0.8rem; color: #64748b; margin-top: 4px; }
  .city-meta  { font-size: 0.78rem; color: #94a3b8; margin-top: 8px; }

  .badge { display:inline-block; padding:2px 10px; border-radius:20px;
           font-size:.72rem; font-weight:600; margin-right:4px; }
  .badge-blue  { background:rgba(56,189,248,.15); color:#38bdf8; border:1px solid #0369a1; }
  .badge-amber { background:rgba(245,158,11,.15);  color:#f59e0b; border:1px solid #b45309; }

  .section-title {
    font-size:1.05rem; font-weight:600; color:#94a3b8;
    text-transform:uppercase; letter-spacing:.1em;
    margin:24px 0 12px; padding-bottom:8px; border-bottom:1px solid #1e3a5f;
  }

  /* Layer banners */
  .layer-banner {
    border-radius:14px; padding:14px 20px; margin-bottom:16px; border:1px solid;
    display:flex; align-items:center; gap:14px;
  }
  .layer-banner .l-icon { font-size:2rem; line-height:1; flex-shrink:0; }
  .layer-banner .l-name { font-size:1rem; font-weight:700;
    font-family:'JetBrains Mono',monospace; letter-spacing:.06em; }
  .layer-banner .l-desc { font-size:.75rem; opacity:.75; margin-top:3px; }
  .layer-bronze { background:linear-gradient(135deg,rgba(180,83,9,.2),rgba(120,53,15,.1)); border-color:#b45309; }
  .layer-bronze .l-name { color:#fbbf24; } .layer-bronze .l-desc { color:#d97706; }
  .layer-silver { background:linear-gradient(135deg,rgba(100,116,139,.2),rgba(71,85,105,.1)); border-color:#64748b; }
  .layer-silver .l-name { color:#e2e8f0; } .layer-silver .l-desc { color:#94a3b8; }
  .layer-gold   { background:linear-gradient(135deg,rgba(234,179,8,.2),rgba(161,98,7,.1)); border-color:#ca8a04; }
  .layer-gold .l-name { color:#fde047; } .layer-gold .l-desc { color:#eab308; }

  /* Pipeline flow */
  .pipe-flow {
    display:flex; align-items:center; flex-wrap:nowrap;
    background:#0a1628; border:1px solid #1e3a5f; border-radius:12px;
    padding:14px 20px; margin-bottom:20px; overflow-x:auto; gap:0;
  }
  .pipe-step { display:flex; flex-direction:column; align-items:center;
    padding:8px 14px; border-radius:8px; border:1px solid;
    min-width:84px; flex-shrink:0; transition:transform .2s; }
  .pipe-step:hover { transform:translateY(-2px); }
  .pipe-step .ps-icon  { font-size:1.3rem; }
  .pipe-step .ps-label { font-size:.65rem; font-weight:600; letter-spacing:.06em;
                         text-transform:uppercase; margin-top:4px; }
  .pipe-arrow { font-size:1.1rem; color:#1e3a5f; margin:0 3px; flex-shrink:0; }
  .ps-raw    { background:rgba(99,102,241,.1); border-color:#4338ca; color:#818cf8; }
  .ps-bronze { background:rgba(180,83,9,.15);  border-color:#b45309; color:#fbbf24; }
  .ps-silver { background:rgba(100,116,139,.15);border-color:#64748b; color:#e2e8f0; }
  .ps-gold   { background:rgba(234,179,8,.15); border-color:#ca8a04; color:#fde047; }
  .ps-ml     { background:rgba(168,85,247,.15);border-color:#7c3aed; color:#c084fc; }

  /* City detail panel */
  .cdp {
    background:linear-gradient(135deg,#0b1a2e,#0d2040);
    border:1px solid #38bdf8; border-radius:16px;
    padding:22px 24px; margin:12px 0 20px;
    box-shadow:0 0 40px rgba(56,189,248,.08);
  }
  .cdp-title { font-size:1.3rem; font-weight:700; color:#e2e8f0; margin-bottom:4px; }
  .cdp-temp  { font-size:2.8rem; font-weight:700;
    font-family:'JetBrains Mono',monospace; line-height:1.1; }

  ::-webkit-scrollbar { width:6px; height:6px; }
  ::-webkit-scrollbar-track { background:#0d1b2a; }
  ::-webkit-scrollbar-thumb { background:#1e3a5f; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ── Config ────────────────────────────────────────────────────────────────────
DATABRICKS_HOST      = st.secrets.get("DATABRICKS_HOST",      os.getenv("DATABRICKS_HOST",      "")).rstrip("/")
DATABRICKS_TOKEN     = st.secrets.get("DATABRICKS_TOKEN",     os.getenv("DATABRICKS_TOKEN",     ""))
DATABRICKS_WAREHOUSE = st.secrets.get("DATABRICKS_WAREHOUSE", os.getenv("DATABRICKS_WAREHOUSE", ""))

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

CITIES = [
    {"city": "Ho Chi Minh City", "country": "🇻🇳", "lat": 10.8231,  "lon": 106.6297},
    {"city": "Hanoi",            "country": "🇻🇳", "lat": 21.0285,  "lon": 105.8542},
    {"city": "Da Nang",          "country": "🇻🇳", "lat": 16.0544,  "lon": 108.2022},
    {"city": "Tokyo",            "country": "🇯🇵", "lat": 35.6762,  "lon": 139.6503},
    {"city": "London",           "country": "🇬🇧", "lat": 51.5074,  "lon": -0.1278 },
    {"city": "New York",         "country": "🇺🇸", "lat": 40.7128,  "lon": -74.006 },
    {"city": "Paris",            "country": "🇫🇷", "lat": 48.8566,  "lon": 2.3522  },
    {"city": "Sydney",           "country": "🇦🇺", "lat": -33.8688, "lon": 151.2093},
    {"city": "Dubai",            "country": "🇦🇪", "lat": 25.2048,  "lon": 55.2708 },
    {"city": "Singapore",        "country": "🇸🇬", "lat": 1.3521,   "lon": 103.8198},
    {"city": "Bangkok",          "country": "🇹🇭", "lat": 13.7563,  "lon": 100.5018},
    {"city": "Mumbai",           "country": "🇮🇳", "lat": 19.0760,  "lon": 72.8777 },
    {"city": "Seoul",            "country": "🇰🇷", "lat": 37.5665,  "lon": 126.9780},
    {"city": "Berlin",           "country": "🇩🇪", "lat": 52.5200,  "lon": 13.4050 },
    {"city": "São Paulo",        "country": "🇧🇷", "lat": -23.5505, "lon": -46.6333},
]

WMO_CODES = {
    0:"☀️ Clear sky",1:"🌤️ Mainly clear",2:"⛅ Partly cloudy",3:"☁️ Overcast",
    45:"🌫️ Fog",48:"🌫️ Icy fog",
    51:"🌦️ Light drizzle",53:"🌦️ Drizzle",55:"🌧️ Dense drizzle",
    61:"🌧️ Slight rain",63:"🌧️ Moderate rain",65:"🌧️ Heavy rain",
    71:"🌨️ Slight snow",73:"🌨️ Moderate snow",75:"❄️ Heavy snow",
    80:"🌦️ Showers",81:"🌧️ Rain showers",82:"⛈️ Violent showers",
    95:"⛈️ Thunderstorm",96:"⛈️ Thunderstorm+hail",99:"⛈️ Heavy thunderstorm",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#080f1c",
    font=dict(color="#94a3b8", family="Space Grotesk"),
    xaxis=dict(gridcolor="#1e3a5f", linecolor="#1e3a5f", zerolinecolor="#1e3a5f"),
    yaxis=dict(gridcolor="#1e3a5f", linecolor="#1e3a5f", zerolinecolor="#1e3a5f"),
    margin=dict(l=10, r=10, t=36, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e3a5f", font=dict(color="#94a3b8")),
)


# ════════════════════════════════════════════════════════════════════════════
# BACKEND — Databricks SQL Statement Execution API
# Không cần thư viện ngoài, chỉ dùng requests
# ════════════════════════════════════════════════════════════════════════════

def _sql_headers():
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}


def run_sql(query: str, timeout_s: int = 60) -> pd.DataFrame | None:
    """
    Thực thi SQL query qua Databricks Statement Execution API.
    Trả về DataFrame hoặc None nếu lỗi.
    Tự động poll cho đến khi query xong (PENDING → RUNNING → SUCCEEDED).
    """
    if not DATABRICKS_WAREHOUSE:
        return None

    url_exec  = f"{DATABRICKS_HOST}/api/2.0/sql/statements"
    url_check = f"{DATABRICKS_HOST}/api/2.0/sql/statements/{{sid}}"

    payload = {
        "warehouse_id": DATABRICKS_WAREHOUSE,
        "statement": query,
        "wait_timeout": "30s",   # server-side wait
        "on_wait_timeout": "CONTINUE",
        "format": "JSON_ARRAY",
        "disposition": "INLINE",
    }

    try:
        resp = requests.post(url_exec, headers=_sql_headers(), json=payload, timeout=40)
        if not resp.ok:
            return None
        data = resp.json()
        sid  = data.get("statement_id")
        if not sid:
            return None

        # Poll nếu chưa xong
        deadline = time.time() + timeout_s
        while data.get("status", {}).get("state") in ("PENDING", "RUNNING"):
            if time.time() > deadline:
                return None
            time.sleep(1.5)
            r2 = requests.get(url_check.format(sid=sid), headers=_sql_headers(), timeout=15)
            if not r2.ok:
                return None
            data = r2.json()

        if data.get("status", {}).get("state") != "SUCCEEDED":
            return None

        result = data.get("result", {})
        columns = [c["name"] for c in data.get("manifest", {}).get("schema", {}).get("columns", [])]
        rows    = result.get("data_array", [])

        if not columns:
            return pd.DataFrame()
        return pd.DataFrame(rows, columns=columns)

    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def sql_query(query: str) -> pd.DataFrame | None:
    """Cached wrapper quanh run_sql."""
    return run_sql(query)


def table(name: str) -> str:
    """Shorthand: tên bảng đầy đủ."""
    return f"{CATALOG}.{SCHEMA}.{name}"


# ════════════════════════════════════════════════════════════════════════════
# LIVE WEATHER — Open-Meteo
# Fix: không dùng integer arithmetic với Timestamp
# ════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=900, show_spinner=False)
def fetch_weather_live(city_keys: tuple) -> list:
    cities  = [c for c in CITIES if c["city"] in city_keys]
    results = []
    for c in cities:
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": c["lat"], "longitude": c["lon"],
                    "current": ",".join([
                        "temperature_2m","relative_humidity_2m","apparent_temperature",
                        "precipitation","weather_code","surface_pressure",
                        "wind_speed_10m","cloud_cover","visibility",
                    ]),
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
                timeout=8,
            )
            if not r.ok:
                continue
            j   = r.json()
            cur = j.get("current", {})
            dly = j.get("daily", {})

            results.append({
                "city":     c["city"],
                "flag":     c["country"],
                "lat":      c["lat"],
                "lon":      c["lon"],
                "temp":     cur.get("temperature_2m"),
                "feels":    cur.get("apparent_temperature"),
                "humidity": cur.get("relative_humidity_2m"),
                "precip":   cur.get("precipitation"),
                "wind":     cur.get("wind_speed_10m"),
                "cloud":    cur.get("cloud_cover"),
                "vis":      cur.get("visibility"),
                "pressure": cur.get("surface_pressure"),
                "code":     cur.get("weather_code", 0),
                "desc":     WMO_CODES.get(cur.get("weather_code", 0), "?"),
                # FIX: lấy trực tiếp từ list, không cộng trừ Timestamp
                "tmax":     dly["temperature_2m_max"][0] if dly.get("temperature_2m_max") else None,
                "tmin":     dly["temperature_2m_min"][0] if dly.get("temperature_2m_min") else None,
                # FIX: dùng datetime thuần, không phụ thuộc freq
                "fetched_at": datetime.now(timezone.utc).strftime("%H:%M UTC"),
            })
        except Exception:
            pass
    return results


def temp_color(t):
    if t is None: return "#64748b"
    t = float(t)
    if t >= 38: return "#ef4444"
    if t >= 32: return "#f59e0b"
    if t >= 20: return "#38bdf8"
    if t >= 10: return "#22d3ee"
    return "#818cf8"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _hdr():
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}

def db_get(path, params=None):
    r = requests.get(f"{DATABRICKS_HOST}{path}", headers=_hdr(), params=params, timeout=20)
    r.raise_for_status(); return r.json()

def db_post(path, payload):
    r = requests.post(f"{DATABRICKS_HOST}{path}", headers=_hdr(), json=payload, timeout=20)
    r.raise_for_status(); return r.json()

def get_job_id(name="weather-pipeline"):
    for j in db_get("/api/2.1/jobs/list").get("jobs", []):
        if j["settings"]["name"] == name: return j["job_id"]
    return None

def list_clusters():
    return [c for c in db_get("/api/2.0/clusters/list").get("clusters", [])
            if c.get("state") == "RUNNING"]


# ── Page header ───────────────────────────────────────────────────────────────
c_title, c_time = st.columns([7, 3])
with c_title:
    st.markdown("""
    <div style="padding:20px 0 8px">
      <div style="font-size:1.8rem;font-weight:700;color:#e2e8f0;letter-spacing:-.02em">🌤️ Weather Pipeline</div>
      <div style="font-size:.85rem;color:#475569;margin-top:2px">
        Databricks SQL · Open-Meteo · Delta Lake · MLflow · Streamlit
      </div>
    </div>""", unsafe_allow_html=True)
with c_time:
    wh_ok = "✅ Warehouse OK" if DATABRICKS_WAREHOUSE else "⚠️ Chưa có warehouse"
    st.markdown(f"""
    <div style="text-align:right;padding:20px 0 8px;font-family:'JetBrains Mono',monospace;">
      <div style="font-size:.72rem;color:#475569">UPDATED</div>
      <div style="font-size:.9rem;color:#38bdf8">{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
      <div style="font-size:.7rem;color:#475569;margin-top:2px">{wh_ok}</div>
    </div>""", unsafe_allow_html=True)

if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
    st.error("⚠️ Thiếu credentials. Thêm DATABRICKS_HOST và DATABRICKS_TOKEN vào `.streamlit/secrets.toml`")
    st.stop()

if not DATABRICKS_WAREHOUSE:
    st.warning("""⚠️ Chưa có DATABRICKS_WAREHOUSE_ID trong secrets.toml.
Dashboard sẽ không load dữ liệu từ Databricks SQL.
Thêm dòng: `DATABRICKS_WAREHOUSE = "your_warehouse_id"`""")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["📊 Dashboard", "🤖 ML Insights", "🌍 Live Weather", "🚀 Pipeline", "📋 Workflows"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    _, col_ref = st.columns([8, 2])
    with col_ref:
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    # Pipeline flow
    st.markdown("""
    <div class="pipe-flow">
      <div class="pipe-step ps-raw"><span class="ps-icon">🕷️</span><span class="ps-label">Crawler</span></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step ps-bronze"><span class="ps-icon">🟤</span><span class="ps-label">Bronze</span></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step ps-silver"><span class="ps-icon">🥈</span><span class="ps-label">Silver</span></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step ps-gold"><span class="ps-icon">🥇</span><span class="ps-label">Gold</span></div>
      <span class="pipe-arrow">→</span>
      <div class="pipe-step ps-ml"><span class="ps-icon">🤖</span><span class="ps-label">ML</span></div>
    </div>""", unsafe_allow_html=True)

    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown("""<div class="layer-banner layer-bronze"><span class="l-icon">🟤</span>
          <div><div class="l-name">BRONZE</div>
          <div class="l-desc">Raw JSON · Lưu nguyên bản · Không transform<br>→ 01_bronze_ingest.py</div></div></div>""",
          unsafe_allow_html=True)
    with b2:
        st.markdown("""<div class="layer-banner layer-silver"><span class="l-icon">🥈</span>
          <div><div class="l-name">SILVER</div>
          <div class="l-desc">Validate · Chuẩn hóa · Loại null/dup<br>→ 02_silver_transform.py</div></div></div>""",
          unsafe_allow_html=True)
    with b3:
        st.markdown("""<div class="layer-banner layer-gold"><span class="l-icon">🥇</span>
          <div><div class="l-name">GOLD</div>
          <div class="l-desc">Aggregate · KPIs · Analytics-ready<br>→ 03_gold_aggregate.py</div></div></div>""",
          unsafe_allow_html=True)

    # ── Load dữ liệu từ Databricks SQL ────────────────────────────────────
    with st.spinner("🔌 Đang tải dữ liệu từ Databricks SQL..."):
        df_latest = sql_query(f"SELECT * FROM {table('gold_weather_latest')} ORDER BY temperature_c DESC")
        df_stats  = sql_query(f"SELECT * FROM {table('gold_city_stats')} ORDER BY overall_avg_temp DESC")

    if df_latest is None or (isinstance(df_latest, pd.DataFrame) and df_latest.empty):
        st.info("📂 Chưa có dữ liệu trong Databricks. Hãy chạy pipeline ít nhất một lần (tab Pipeline).")
    else:
        # Đổi kiểu số
        for col in ["temperature_c","temp_max_c","temp_min_c","feels_like_c","humidity","wind_speed_kmh","cloud_cover_pct"]:
            if col in df_latest.columns:
                df_latest[col] = pd.to_numeric(df_latest[col], errors="coerce")

        hottest  = df_latest.loc[df_latest["temperature_c"].idxmax()]
        coldest  = df_latest.loc[df_latest["temperature_c"].idxmin()]
        avg_temp = df_latest["temperature_c"].mean()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Cities tracked",   len(df_latest))
        k2.metric("🌡️ Hottest",        hottest["city"], delta=f"{hottest['temperature_c']:.1f} °C")
        k3.metric("🧊 Coldest",         coldest["city"], delta=f"{coldest['temperature_c']:.1f} °C")
        k4.metric("💧 Avg global temp", f"{avg_temp:.1f} °C")

        st.markdown('<div class="section-title">Current Conditions — Click để xem biểu đồ</div>', unsafe_allow_html=True)

        # Session state
        if "selected_city" not in st.session_state:
            st.session_state["selected_city"] = None

        # City cards
        cols3 = st.columns(3)
        for i, row in df_latest.reset_index(drop=True).iterrows():
            flag   = next((c["country"] for c in CITIES if c["city"] == row["city"]), "")
            tc     = temp_color(row.get("temperature_c"))
            is_sel = st.session_state["selected_city"] == row["city"]
            with cols3[i % 3]:
                st.markdown(f"""
                <div class="city-card {'sel' if is_sel else ''}">
                  <div class="city-name">{flag} {row['city']}</div>
                  <div class="city-temp" style="color:{tc}">{float(row['temperature_c']):.1f}°C</div>
                  <div class="city-desc">{row.get('weather_desc','—')}</div>
                  <div class="city-meta">💧{row.get('humidity','—')}% &nbsp; 💨{row.get('wind_speed_kmh','—')}km/h &nbsp; ☁️{row.get('cloud_cover_pct','—')}%</div>
                  <div style="margin-top:6px">
                    <span class="badge badge-blue">↑{row.get('temp_max_c','—')}°</span>
                    <span class="badge badge-blue">↓{row.get('temp_min_c','—')}°</span>
                    <span class="badge badge-amber">feels {row.get('feels_like_c','—')}°</span>
                  </div>
                </div>""", unsafe_allow_html=True)
                lbl = "✅ Đang xem" if is_sel else "📊 Xem biểu đồ"
                if st.button(lbl, key=f"sel_{row['city']}", use_container_width=True):
                    st.session_state["selected_city"] = None if is_sel else row["city"]
                    st.rerun()

        # ── FIX: City detail charts — load từ SQL khi click ───────────────
        sel = st.session_state.get("selected_city")
        if sel:
            city_row = df_latest[df_latest["city"] == sel]
            flag_s   = next((c["country"] for c in CITIES if c["city"] == sel), "")
            temp_s   = f"{float(city_row.iloc[0]['temperature_c']):.1f}" if len(city_row) else "—"
            tc_s     = temp_color(city_row.iloc[0]["temperature_c"] if len(city_row) else None)
            desc_s   = city_row.iloc[0].get("weather_desc", "—") if len(city_row) else "—"

            st.markdown(f"""
            <div class="cdp">
              <div class="cdp-title">{flag_s} {sel}</div>
              <div class="cdp-temp" style="color:{tc_s}">{temp_s}°C
                <span style="font-size:1rem;font-weight:400;color:#64748b;margin-left:12px">{desc_s}</span>
              </div>
            </div>""", unsafe_allow_html=True)

            with st.spinner(f"Đang tải lịch sử {sel}..."):
                df_c = sql_query(f"""
                    SELECT * FROM {table('gold_weather_daily')}
                    WHERE city = '{sel}'
                    ORDER BY date ASC
                """)

            if df_c is None or df_c.empty:
                st.info(f"Chưa có dữ liệu lịch sử cho **{sel}**. Pipeline cần chạy ít nhất 2 lần.")
            else:
                # Ép kiểu
                df_c["date"] = pd.to_datetime(df_c["date"])
                for col in df_c.columns:
                    if col != "date" and col not in ("city","country","weather_desc"):
                        df_c[col] = pd.to_numeric(df_c[col], errors="coerce")

                # Hàng 1: Nhiệt độ + Độ ẩm
                r1, r2 = st.columns(2)
                with r1:
                    fig = go.Figure()
                    for cname, nm, clr in [
                        ("avg_temp_c","Avg","#38bdf8"),
                        ("temp_max_c","Max","#f59e0b"),
                        ("temp_min_c","Min","#818cf8"),
                    ]:
                        if cname in df_c.columns:
                            fig.add_trace(go.Scatter(x=df_c["date"], y=df_c[cname],
                                mode="lines+markers", name=nm,
                                line=dict(color=clr, width=2), marker=dict(size=4)))
                    fig.update_layout(**PLOTLY_LAYOUT, height=270, title="🌡️ Nhiệt độ (°C)")
                    st.plotly_chart(fig, use_container_width=True)
                with r2:
                    hcol = next((c for c in ["avg_humidity","humidity"] if c in df_c.columns), None)
                    if hcol:
                        fig = go.Figure(go.Bar(x=df_c["date"], y=df_c[hcol], marker_color="#0369a1"))
                        fig.update_layout(**PLOTLY_LAYOUT, height=270, title="💧 Độ ẩm (%)")
                        st.plotly_chart(fig, use_container_width=True)

                # Hàng 2: Gió + Mưa
                r3, r4 = st.columns(2)
                with r3:
                    wcol = next((c for c in ["avg_wind_speed_kmh","wind_speed_kmh"] if c in df_c.columns), None)
                    if wcol:
                        fig = go.Figure(go.Scatter(x=df_c["date"], y=df_c[wcol],
                            fill="tozeroy", line=dict(color="#22c55e", width=2),
                            fillcolor="rgba(34,197,94,.1)"))
                        fig.update_layout(**PLOTLY_LAYOUT, height=250, title="💨 Tốc độ gió (km/h)")
                        st.plotly_chart(fig, use_container_width=True)
                with r4:
                    pcol = next((c for c in ["avg_precipitation_mm","precipitation_mm","total_precip_mm"] if c in df_c.columns), None)
                    if pcol:
                        fig = go.Figure(go.Bar(x=df_c["date"], y=df_c[pcol], marker_color="#818cf8"))
                        fig.update_layout(**PLOTLY_LAYOUT, height=250, title="🌧️ Lượng mưa (mm)")
                        st.plotly_chart(fig, use_container_width=True)

                # Hàng 3: UV + Mây
                r5, r6 = st.columns(2)
                with r5:
                    uvcol = next((c for c in ["avg_uv_index","uv_index"] if c in df_c.columns), None)
                    if uvcol:
                        fig = go.Figure(go.Scatter(x=df_c["date"], y=df_c[uvcol],
                            mode="lines+markers", line=dict(color="#fde047", width=2),
                            marker=dict(size=4, color="#fde047")))
                        fig.update_layout(**PLOTLY_LAYOUT, height=240, title="☀️ UV Index")
                        st.plotly_chart(fig, use_container_width=True)
                with r6:
                    cccol = next((c for c in ["avg_cloud_cover_pct","cloud_cover_pct","cloud_cover"] if c in df_c.columns), None)
                    if cccol:
                        fig = go.Figure(go.Bar(x=df_c["date"], y=df_c[cccol], marker_color="#475569"))
                        fig.update_layout(**PLOTLY_LAYOUT, height=240, title="☁️ Độ phủ mây (%)")
                        st.plotly_chart(fig, use_container_width=True)

        # ── So sánh tất cả thành phố ───────────────────────────────────────
        st.markdown('<div class="section-title">So sánh tất cả thành phố</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=df_latest["city"], y=df_latest["temperature_c"],
            marker_color=[temp_color(t) for t in df_latest["temperature_c"]],
            text=[f"{float(t):.1f}°" for t in df_latest["temperature_c"]],
            textposition="outside", textfont=dict(color="#94a3b8", size=11), name="Temp",
        ))
        if "temp_max_c" in df_latest.columns:
            fig_bar.add_trace(go.Scatter(x=df_latest["city"], y=df_latest["temp_max_c"],
                mode="markers", marker=dict(symbol="triangle-up", size=10, color="#f59e0b"), name="Max"))
        if "temp_min_c" in df_latest.columns:
            fig_bar.add_trace(go.Scatter(x=df_latest["city"], y=df_latest["temp_min_c"],
                mode="markers", marker=dict(symbol="triangle-down", size=10, color="#818cf8"), name="Min"))
        fig_bar.update_layout(**PLOTLY_LAYOUT, height=360, title="Nhiệt độ hiện tại (°C)")
        st.plotly_chart(fig_bar, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            if "humidity" in df_latest.columns:
                fig = px.bar(df_latest, x="city", y="humidity", color="humidity",
                    color_continuous_scale=["#1e3a5f","#0369a1","#38bdf8"], title="Humidity (%)")
                fig.update_layout(**PLOTLY_LAYOUT, height=300, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if "wind_speed_kmh" in df_latest.columns:
                fig = px.bar(df_latest, x="city", y="wind_speed_kmh", color="wind_speed_kmh",
                    color_continuous_scale=["#1e3a5f","#22c55e","#f59e0b"], title="Wind Speed (km/h)")
                fig.update_layout(**PLOTLY_LAYOUT, height=300, coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)

        # ── Historical trends ──────────────────────────────────────────────
        st.markdown('<div class="section-title">Historical Temperature Trends</div>', unsafe_allow_html=True)
        with st.spinner("Đang tải dữ liệu lịch sử..."):
            df_daily_all = sql_query(f"""
                SELECT city, date, avg_temp_c, avg_precipitation_mm, avg_uv_index
                FROM {table('gold_weather_daily')}
                ORDER BY date ASC
            """)

        if df_daily_all is not None and not df_daily_all.empty:
            df_daily_all["date"] = pd.to_datetime(df_daily_all["date"])
            for col in ["avg_temp_c","avg_precipitation_mm","avg_uv_index"]:
                if col in df_daily_all.columns:
                    df_daily_all[col] = pd.to_numeric(df_daily_all[col], errors="coerce")

            city_opts = sorted(df_daily_all["city"].unique())
            hist_sel  = st.multiselect("Chọn thành phố:", city_opts, default=city_opts[:5], key="hist_cities")
            if hist_sel:
                df_filt = df_daily_all[df_daily_all["city"].isin(hist_sel)]
                fig_trend = px.line(df_filt, x="date", y="avg_temp_c", color="city",
                    title="Avg Daily Temperature (°C)")
                fig_trend.update_traces(line=dict(width=2))
                fig_trend.update_layout(**PLOTLY_LAYOUT, height=380)
                st.plotly_chart(fig_trend, use_container_width=True)

                ca, cb = st.columns(2)
                with ca:
                    if "avg_precipitation_mm" in df_filt.columns:
                        fig = px.bar(df_filt, x="date", y="avg_precipitation_mm", color="city",
                            title="Daily Precipitation (mm)", barmode="group")
                        fig.update_layout(**PLOTLY_LAYOUT, height=280)
                        st.plotly_chart(fig, use_container_width=True)
                with cb:
                    if "avg_uv_index" in df_filt.columns:
                        fig = px.line(df_filt, x="date", y="avg_uv_index", color="city",
                            title="UV Index", markers=True)
                        fig.update_layout(**PLOTLY_LAYOUT, height=280)
                        st.plotly_chart(fig, use_container_width=True)

        # ── City stats ─────────────────────────────────────────────────────
        if df_stats is not None and not df_stats.empty:
            st.markdown('<div class="section-title">City Historical Statistics</div>', unsafe_allow_html=True)
            show_cols = [c for c in [
                "city","country","days_tracked","overall_avg_temp","overall_max_temp",
                "overall_min_temp","avg_humidity","avg_wind_speed","avg_uv_index","total_precipitation",
            ] if c in df_stats.columns]
            st.dataframe(df_stats[show_cols], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — ML INSIGHTS
# ════════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    _, col_mlr = st.columns([8, 2])
    with col_mlr:
        if st.button("🔄 Refresh ML", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    with st.spinner("Đang tải kết quả ML..."):
        df_metrics   = sql_query(f"SELECT * FROM {table('gold_ml_metrics')}")
        df_feat_imp  = sql_query(f"SELECT * FROM {table('gold_ml_feature_importance')} ORDER BY importance DESC")
        df_full_pred = sql_query(f"SELECT * FROM {table('gold_ml_full_predictions')} ORDER BY date ASC")
        df_forecast  = sql_query(f"SELECT * FROM {table('gold_ml_forecast')} ORDER BY forecast_temp_next_day DESC")

    if df_metrics is None or df_metrics.empty:
        st.info("📂 Chưa có kết quả ML. Hãy chạy notebook `04_ml_train` trước.")
    else:
        # Summary từ metrics table
        best_row = df_metrics.sort_values("rmse_test").iloc[0] if "rmse_test" in df_metrics.columns else df_metrics.iloc[0]
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("Best Model",   str(best_row.get("model","—")))
        m2.metric("RMSE (test)",  f"{float(best_row.get('rmse_test',0)):.3f} °C" if best_row.get("rmse_test") else "—")
        m3.metric("MAE (test)",   f"{float(best_row.get('mae_test',0)):.3f} °C"  if best_row.get("mae_test")  else "—")
        m4.metric("R² Score",     f"{float(best_row.get('r2_test',0)):.3f}"      if best_row.get("r2_test")   else "—")
        m5.metric("Within ±1°C", f"{float(best_row.get('within_1deg_pct',0)):.1f}%" if best_row.get("within_1deg_pct") else "—")

        st.markdown('<div class="section-title">Model Comparison</div>', unsafe_allow_html=True)
        for col in ["rmse_test","mae_test","r2_test","within_1deg_pct"]:
            if col in df_metrics.columns:
                df_metrics[col] = pd.to_numeric(df_metrics[col], errors="coerce")
        st.dataframe(df_metrics, use_container_width=True, hide_index=True)

        fig_m = go.Figure()
        for metric, color, label in [("rmse_test","#ef4444","RMSE"),("mae_test","#f59e0b","MAE"),("r2_test","#22c55e","R²")]:
            if metric in df_metrics.columns:
                fig_m.add_trace(go.Bar(name=label, x=df_metrics["model"], y=df_metrics[metric],
                    marker_color=color, text=df_metrics[metric].round(3), textposition="outside"))
        fig_m.update_layout(**PLOTLY_LAYOUT, barmode="group", height=300, title="Model Metrics")
        st.plotly_chart(fig_m, use_container_width=True)

        if df_full_pred is not None and not df_full_pred.empty:
            st.markdown('<div class="section-title">Actual vs Predicted</div>', unsafe_allow_html=True)
            df_full_pred["date"] = pd.to_datetime(df_full_pred["date"])
            for col in ["target_next_temp","predicted_temp","prediction_error"]:
                if col in df_full_pred.columns:
                    df_full_pred[col] = pd.to_numeric(df_full_pred[col], errors="coerce")
            city_opts_ml = sorted(df_full_pred["city"].unique())
            sel_ml = st.selectbox("Thành phố:", city_opts_ml, key="ml_city_sel")
            df_mc  = df_full_pred[df_full_pred["city"] == sel_ml].dropna(subset=["target_next_temp"])

            fig_avp = go.Figure()
            for split, clr in [("train","#1e3a5f"),("test","#0369a1")]:
                d = df_mc[df_mc["split"] == split]
                fig_avp.add_trace(go.Scatter(x=d["date"], y=d["target_next_temp"],
                    mode="lines", name=f"Actual ({split})", line=dict(color=clr, width=2)))
            fig_avp.add_trace(go.Scatter(x=df_mc["date"], y=df_mc["predicted_temp"],
                mode="lines", name="Predicted", line=dict(color="#38bdf8", width=2, dash="dot")))
            ts = df_mc[df_mc["split"]=="test"]["date"].min()
            if pd.notna(ts):
                fig_avp.add_vline(x=ts, line=dict(color="#f59e0b", dash="dash", width=1),
                    annotation_text="Test start", annotation_font_color="#f59e0b")
            fig_avp.update_layout(**PLOTLY_LAYOUT, height=360, title=f"Forecast — {sel_ml}")
            st.plotly_chart(fig_avp, use_container_width=True)

        if df_feat_imp is not None and not df_feat_imp.empty:
            st.markdown('<div class="section-title">Feature Importance</div>', unsafe_allow_html=True)
            df_feat_imp["importance"] = pd.to_numeric(df_feat_imp["importance"], errors="coerce")
            top_n = st.slider("Top N:", 5, min(30,len(df_feat_imp)), 15, key="feat_n")
            top   = df_feat_imp.head(top_n).sort_values("importance")
            fig_fi = go.Figure(go.Bar(x=top["importance"], y=top["feature"], orientation="h",
                marker=dict(color=top["importance"],
                    colorscale=[[0,"#1e3a5f"],[0.5,"#0369a1"],[1,"#38bdf8"]]),
                textposition="outside"))
            fig_fi.update_layout(**PLOTLY_LAYOUT, height=max(300,top_n*28), title="Feature Importances")
            st.plotly_chart(fig_fi, use_container_width=True)

        if df_forecast is not None and not df_forecast.empty:
            st.markdown('<div class="section-title">Next Day Forecast</div>', unsafe_allow_html=True)
            if "forecast_date" in df_forecast.columns:
                df_forecast["forecast_date"] = pd.to_datetime(df_forecast["forecast_date"]).dt.date
            for col in ["avg_temp_c","forecast_temp_next_day"]:
                if col in df_forecast.columns:
                    df_forecast[col] = pd.to_numeric(df_forecast[col], errors="coerce")
            show_cols = [c for c in ["city","country","avg_temp_c","forecast_temp_next_day","forecast_date",
                "avg_humidity","avg_wind_speed_kmh","comfort_score"] if c in df_forecast.columns]
            st.dataframe(df_forecast[show_cols], use_container_width=True, hide_index=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — LIVE WEATHER  (auto-load, Timestamp fix)
# ════════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">🌍 Live Weather — Open-Meteo · cache 15 phút</div>', unsafe_allow_html=True)

    col_sel, col_btn = st.columns([5, 1])
    with col_sel:
        selected = st.multiselect(
            "Chọn thành phố:",
            options=[c["city"] for c in CITIES],
            default=[c["city"] for c in CITIES[:6]],
            key="live_cities",
        )
    with col_btn:
        st.markdown("<div style='margin-top:28px'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh", type="primary", key="fetch_live", use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    city_keys = tuple(selected) if selected else tuple(c["city"] for c in CITIES[:6])

    with st.spinner("🌐 Đang tải dữ liệu thời tiết realtime..."):
        live_data = fetch_weather_live(city_keys)

    if not live_data:
        st.error("❌ Không lấy được dữ liệu. Kiểm tra kết nối mạng.")
    else:
        st.caption(f"✅ {len(live_data)} thành phố · {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")

        cols3 = st.columns(min(3, len(live_data)))
        for i, w in enumerate(live_data):
            with cols3[i % 3]:
                tc = temp_color(w["temp"])
                # FIX: format trực tiếp float, không dùng Timestamp arithmetic
                temp_str = f"{w['temp']}°C" if w["temp"] is not None else "—°C"
                tmax_str = f"{w['tmax']}°" if w["tmax"] is not None else "—"
                tmin_str = f"{w['tmin']}°" if w["tmin"] is not None else "—"
                st.markdown(f"""
                <div class="city-card">
                  <div class="city-name">{w['flag']} {w['city']}</div>
                  <div class="city-temp" style="color:{tc}">{temp_str}</div>
                  <div class="city-desc">{w['desc']}</div>
                  <div class="city-meta">💧{w['humidity']}% &nbsp; 💨{w['wind']}km/h &nbsp; ☁️{w['cloud']}%</div>
                  <div style="margin-top:6px">
                    <span class="badge badge-amber">feels {w['feels']}°</span>
                    <span class="badge badge-blue">↑{tmax_str} ↓{tmin_str}</span>
                  </div>
                </div>""", unsafe_allow_html=True)

        st.divider()

        # Table — xây từ scalar Python, không có Timestamp
        rows_live = []
        for w in live_data:
            rows_live.append({
                "City":       f"{w['flag']} {w['city']}",
                "Temp (°C)":  w["temp"],
                "Feels (°C)": w["feels"],
                "Tmax°":      w["tmax"],
                "Tmin°":      w["tmin"],
                "Humidity %": w["humidity"],
                "Wind km/h":  w["wind"],
                "Cloud %":    w["cloud"],
                "Precip mm":  w["precip"],
                "Condition":  w["desc"],
            })
        # Tạo DataFrame từ plain dict — không có index Timestamp
        df_live = pd.DataFrame(rows_live)
        st.dataframe(df_live, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            # Radar humidity
            fig_rad = go.Figure(go.Scatterpolar(
                r=[w["humidity"] for w in live_data if w["humidity"] is not None],
                theta=[w["city"] for w in live_data if w["humidity"] is not None],
                fill="toself", line_color="#38bdf8", fillcolor="rgba(56,189,248,.1)",
            ))
            fig_rad.update_layout(
                polar=dict(bgcolor="#080f1c",
                    radialaxis=dict(gridcolor="#1e3a5f", linecolor="#1e3a5f", tickfont=dict(color="#64748b")),
                    angularaxis=dict(linecolor="#1e3a5f", tickfont=dict(color="#94a3b8"))),
                paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a3b8"),
                height=380, title="Humidity (%)", margin=dict(l=10,r=10,t=40,b=10),
            )
            st.plotly_chart(fig_rad, use_container_width=True)
        with c2:
            fig_lt = go.Figure(go.Bar(
                x=[w["city"] for w in live_data],
                y=[w["temp"] for w in live_data],
                marker_color=[temp_color(w["temp"]) for w in live_data],
                text=[f"{w['temp']}°" for w in live_data],
                textposition="outside", textfont=dict(color="#94a3b8", size=10),
            ))
            fig_lt.update_layout(**PLOTLY_LAYOUT, height=380, title="Live Temperature (°C)")
            st.plotly_chart(fig_lt, use_container_width=True)

        # Lưu live data vào Databricks SQL (nếu có warehouse)
        if DATABRICKS_WAREHOUSE and live_data:
            with st.expander("💾 Lưu live data vào Databricks"):
                st.caption(f"Sẽ INSERT {len(live_data)} dòng vào `{table('live_weather_snapshots')}`")
                if st.button("💾 Save to Databricks", key="save_live"):
                    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    values = ", ".join([
                        f"('{w['city']}', '{w['flag']}', "
                        f"{w['temp'] or 'NULL'}, {w['feels'] or 'NULL'}, "
                        f"{w['humidity'] or 'NULL'}, {w['wind'] or 'NULL'}, "
                        f"{w['cloud'] or 'NULL'}, {w['precip'] or 'NULL'}, "
                        f"'{w['desc']}', '{now_ts}')"
                        for w in live_data
                    ])
                    create_q = f"""
                        CREATE TABLE IF NOT EXISTS {table('live_weather_snapshots')} (
                            city STRING, flag STRING,
                            temperature DOUBLE, feels_like DOUBLE,
                            humidity DOUBLE, wind_speed DOUBLE,
                            cloud_cover DOUBLE, precipitation DOUBLE,
                            weather_desc STRING, snapshot_time TIMESTAMP
                        ) USING DELTA
                    """
                    insert_q = f"""
                        INSERT INTO {table('live_weather_snapshots')} VALUES {values}
                    """
                    run_sql(create_q)
                    result = run_sql(insert_q)
                    if result is not None:
                        st.success(f"✅ Đã lưu {len(live_data)} bản ghi vào Databricks!")
                    else:
                        st.error("❌ Lỗi khi lưu. Kiểm tra warehouse ID.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — PIPELINE
# ════════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown('<div class="section-title">Full Pipeline</div>', unsafe_allow_html=True)
        st.code("crawler → bronze → silver → gold → ml", language="text")
        try:
            job_id = get_job_id()
        except Exception:
            job_id = None
        if job_id:
            st.success(f"✓ Workflow **weather-pipeline** · job_id: `{job_id}`")
            if st.button("▶ Trigger Full Pipeline", type="primary", use_container_width=True):
                resp = db_post("/api/2.1/jobs/run-now", {"job_id": job_id})
                st.success(f"✅ Triggered! run_id: `{resp['run_id']}`")
                st.markdown(f"[🔗 Xem trên Databricks]({DATABRICKS_HOST}/jobs/{job_id}/runs/{resp['run_id']})")
        else:
            st.warning("Chưa có Workflow. Chạy `00_setup_workflow` trên Databricks trước.")

    with col_r:
        st.markdown('<div class="section-title">Chạy từng notebook</div>', unsafe_allow_html=True)
        NOTEBOOKS = {
            "🕷️ Crawler":     "/Shared/weather-pipeline/weather_crawler",
            "🟤 01 Bronze":   "/Shared/weather-pipeline/01_bronze_ingest",
            "🥈 02 Silver":   "/Shared/weather-pipeline/02_silver_transform",
            "🥇 03 Gold":     "/Shared/weather-pipeline/03_gold_aggregate",
            "🤖 04 ML Train": "/Shared/weather-pipeline/04_ml_train",
        }
        try:
            clusters = list_clusters()
            if clusters:
                opts = {f"{c['cluster_name']} ({c['cluster_id']})": c["cluster_id"] for c in clusters}
                cid  = opts[st.selectbox("Cluster:", list(opts.keys()))]
                for label, path in NOTEBOOKS.items():
                    if st.button(label, use_container_width=True, key=f"run_{label}"):
                        resp = db_post("/api/2.1/jobs/runs/submit", {
                            "run_name": f"manual_{path.split('/')[-1]}",
                            "existing_cluster_id": cid,
                            "notebook_task": {"notebook_path": path},
                        })
                        st.success(f"run_id: `{resp['run_id']}`")
            else:
                st.info("Không có cluster nào đang chạy.")
        except Exception as e:
            st.warning(f"Lỗi: {e}")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5 — WORKFLOWS
# ════════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    STATE_EMOJI  = {"RUNNING":"🔵","PENDING":"🟡","TERMINATED":"⚪","INTERNAL_ERROR":"🔴"}
    RESULT_EMOJI = {"SUCCESS":"✅","FAILED":"❌","CANCELED":"🚫","TIMEDOUT":"⏱️"}

    st.markdown('<div class="section-title">Run History</div>', unsafe_allow_html=True)
    cc1, cc2 = st.columns([2, 4])
    with cc1:
        if st.button("🔄 Refresh", use_container_width=True, key="wf_refresh"):
            st.rerun()
    with cc2:
        rid_input = st.text_input("Kiểm tra run_id:", placeholder="123456")

    if rid_input:
        try:
            info = db_get("/api/2.1/jobs/runs/get", {"run_id": int(rid_input)})
            s = info.get("state", {})
            life, result = s.get("life_cycle_state","?"), s.get("result_state","—")
            m1, m2 = st.columns(2)
            m1.metric("State",  f"{STATE_EMOJI.get(life,'❓')} {life}")
            m2.metric("Result", f"{RESULT_EMOJI.get(result,'—')} {result}")
            if info.get("run_page_url"):
                st.markdown(f"[🔗 Xem trên Databricks]({info['run_page_url']})")
        except Exception as e:
            st.error(str(e))

    st.divider()
    try:
        job_id_wf = get_job_id()
        if job_id_wf:
            runs = db_get("/api/2.1/jobs/runs/list", {"job_id": job_id_wf, "limit": 10}).get("runs", [])
            rows = [{
                "run_id":  r["run_id"],
                "state":   f"{STATE_EMOJI.get(r.get('state',{}).get('life_cycle_state',''),'❓')} {r.get('state',{}).get('life_cycle_state','?')}",
                "result":  f"{RESULT_EMOJI.get(r.get('state',{}).get('result_state',''),'—')} {r.get('state',{}).get('result_state','—')}",
                "started": datetime.utcfromtimestamp(r.get("start_time",0)/1000).strftime("%Y-%m-%d %H:%M UTC"),
                "link":    r.get("run_page_url",""),
            } for r in runs]
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa tìm thấy job `weather-pipeline`.")
    except Exception as e:
        st.warning(f"Lỗi: {e}")