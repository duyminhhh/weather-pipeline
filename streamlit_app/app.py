"""
Streamlit Weather Pipeline Dashboard  —  v2
Chạy: streamlit run app.py
"""

import base64
import io
import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Weather Pipeline",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
    background-color: #070e1a;
    color: #e2e8f0;
  }

  /* Top header gradient line */
  .main > div:first-child {
    padding-top: 0;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: #0d1b2a;
    padding: 6px 8px;
    border-radius: 12px;
    border: 1px solid #1e3a5f;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 8px;
    color: #64748b;
    font-weight: 500;
    padding: 8px 18px;
    transition: all .2s;
  }
  .stTabs [aria-selected="true"] {
    background: #0f3460 !important;
    color: #38bdf8 !important;
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: #0d1b2a;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px 20px;
  }
  [data-testid="metric-container"] label {
    color: #64748b !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: .06em;
  }
  [data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem !important;
    font-weight: 600;
  }
  [data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
  }

  /* Dataframe */
  [data-testid="stDataFrame"] {
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    overflow: hidden;
  }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(135deg, #0f3460, #1a5276);
    border: 1px solid #38bdf8;
    border-radius: 8px;
    color: #38bdf8;
    font-weight: 600;
    letter-spacing: .04em;
    transition: all .2s;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #1a5276, #217dbb);
    box-shadow: 0 0 16px rgba(56,189,248,0.25);
    transform: translateY(-1px);
  }
  .stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #0369a1, #0284c7);
    border-color: #7dd3fc;
    color: #fff;
  }

  /* Select / multiselect */
  .stSelectbox > div, .stMultiSelect > div {
    background: #0d1b2a;
    border-color: #1e3a5f;
  }

  /* Input */
  .stTextInput input {
    background: #0d1b2a;
    border-color: #1e3a5f;
    color: #e2e8f0;
  }

  /* Alerts */
  .stSuccess { background: rgba(34,197,94,.12) !important; border-color: #22c55e !important; }
  .stError   { background: rgba(239,68,68,.12) !important; border-color: #ef4444 !important; }
  .stWarning { background: rgba(245,158,11,.12) !important; border-color: #f59e0b !important; }
  .stInfo    { background: rgba(56,189,248,.12) !important; border-color: #38bdf8 !important; }

  /* Divider */
  hr { border-color: #1e3a5f; }

  /* City card */
  .city-card {
    background: linear-gradient(135deg, #0d1b2a, #0f2744);
    border: 1px solid #1e3a5f;
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 12px;
    transition: border-color .2s;
  }
  .city-card:hover { border-color: #38bdf8; }
  .city-temp {
    font-size: 2.2rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    color: #38bdf8;
    line-height: 1;
  }
  .city-name  { font-size: 1rem; font-weight: 600; color: #e2e8f0; }
  .city-desc  { font-size: 0.8rem; color: #64748b; margin-top: 4px; }
  .city-meta  { font-size: 0.78rem; color: #94a3b8; margin-top: 8px; }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: .04em;
    margin-right: 4px;
  }
  .badge-blue   { background: rgba(56,189,248,.15); color: #38bdf8; border: 1px solid #0369a1; }
  .badge-green  { background: rgba(34,197,94,.15);  color: #22c55e; border: 1px solid #15803d; }
  .badge-amber  { background: rgba(245,158,11,.15); color: #f59e0b; border: 1px solid #b45309; }
  .badge-red    { background: rgba(239,68,68,.15);  color: #ef4444; border: 1px solid #b91c1c; }

  /* Section headers */
  .section-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: .1em;
    margin: 24px 0 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1e3a5f;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0d1b2a; }
  ::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)

# ── Config ────────────────────────────────────────────────────────────────────
DATABRICKS_HOST  = st.secrets.get("DATABRICKS_HOST",  os.getenv("DATABRICKS_HOST",  "")).rstrip("/")
DATABRICKS_TOKEN = st.secrets.get("DATABRICKS_TOKEN", os.getenv("DATABRICKS_TOKEN", ""))
WORKSPACE_PATH   = "/Shared/weather-pipeline"

CITIES = [
    {"city": "Ho Chi Minh City", "country": "🇻🇳", "lat": 10.8231,  "lon": 106.6297},
    {"city": "Hanoi",            "country": "🇻🇳", "lat": 21.0285,  "lon": 105.8542},
    {"city": "Da Nang",          "country": "🇻🇳", "lat": 16.0544,  "lon": 108.2022},
    {"city": "Tokyo",            "country": "🇯🇵", "lat": 35.6762,  "lon": 139.6503},
    {"city": "London",           "country": "🇬🇧", "lat": 51.5074,  "lon": -0.1278},
    {"city": "New York",         "country": "🇺🇸", "lat": 40.7128,  "lon": -74.006},
    {"city": "Paris",            "country": "🇫🇷", "lat": 48.8566,  "lon": 2.3522},
    {"city": "Sydney",           "country": "🇦🇺", "lat": -33.8688, "lon": 151.2093},
    {"city": "Dubai",            "country": "🇦🇪", "lat": 25.2048,  "lon": 55.2708},
    {"city": "Singapore",        "country": "🇸🇬", "lat": 1.3521,   "lon": 103.8198},
    {"city": "Bangkok",          "country": "🇹🇭", "lat": 13.7563,  "lon": 100.5018},
    {"city": "Mumbai",           "country": "🇮🇳", "lat": 19.0760,  "lon": 72.8777},
    {"city": "Seoul",            "country": "🇰🇷", "lat": 37.5665,  "lon": 126.9780},
    {"city": "Berlin",           "country": "🇩🇪", "lat": 52.5200,  "lon": 13.4050},
    {"city": "São Paulo",        "country": "🇧🇷", "lat": -23.5505, "lon": -46.6333},
]

WMO_CODES = {
    0: "☀️ Clear sky", 1: "🌤️ Mainly clear", 2: "⛅ Partly cloudy", 3: "☁️ Overcast",
    45: "🌫️ Fog", 48: "🌫️ Icy fog",
    51: "🌦️ Light drizzle", 53: "🌦️ Drizzle", 55: "🌧️ Dense drizzle",
    61: "🌧️ Slight rain", 63: "🌧️ Moderate rain", 65: "🌧️ Heavy rain",
    71: "🌨️ Slight snow", 73: "🌨️ Moderate snow", 75: "❄️ Heavy snow",
    80: "🌦️ Showers", 81: "🌧️ Rain showers", 82: "⛈️ Violent showers",
    95: "⛈️ Thunderstorm", 96: "⛈️ Thunderstorm+hail", 99: "⛈️ Heavy thunderstorm",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#080f1c",
    font=dict(color="#94a3b8", family="Space Grotesk"),
    xaxis=dict(gridcolor="#1e3a5f", linecolor="#1e3a5f", zerolinecolor="#1e3a5f"),
    yaxis=dict(gridcolor="#1e3a5f", linecolor="#1e3a5f", zerolinecolor="#1e3a5f"),
    margin=dict(l=10, r=10, t=36, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="#1e3a5f", font=dict(color="#94a3b8")),
)


# ── API helpers ───────────────────────────────────────────────────────────────
def hdr():
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}

def db_get(path, params=None):
    r = requests.get(f"{DATABRICKS_HOST}{path}", headers=hdr(), params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def db_post(path, payload):
    r = requests.post(f"{DATABRICKS_HOST}{path}", headers=hdr(), json=payload, timeout=20)
    r.raise_for_status()
    return r.json()

def get_job_id(name="weather-pipeline"):
    for j in db_get("/api/2.1/jobs/list").get("jobs", []):
        if j["settings"]["name"] == name:
            return j["job_id"]
    return None

def list_clusters():
    return [c for c in db_get("/api/2.0/clusters/list").get("clusters", [])
            if c.get("state") == "RUNNING"]


@st.cache_data(ttl=300, show_spinner=False)
def load_csv_from_workspace(filename: str) -> pd.DataFrame | None:
    """Đọc CSV từ Databricks Workspace qua REST API (cache 5 phút)."""
    ws_path = f"{WORKSPACE_PATH}/exports/{filename}"
    try:
        r = requests.get(
            f"{DATABRICKS_HOST}/api/2.0/workspace/export",
            headers=hdr(),
            params={"path": ws_path, "format": "SOURCE"},
            timeout=30,
        )
        if not r.ok:
            return None
        content = r.json().get("content", "")
        decoded = base64.b64decode(content).decode("utf-8")
        return pd.read_csv(io.StringIO(decoded))
    except Exception:
        return None


def temp_color(t):
    if t is None: return "#64748b"
    if t >= 38:   return "#ef4444"
    if t >= 32:   return "#f59e0b"
    if t >= 20:   return "#38bdf8"
    if t >= 10:   return "#22d3ee"
    return "#818cf8"


# ── Open-Meteo ────────────────────────────────────────────────────────────────
def fetch_weather_live(cities: list) -> list:
    results = []
    for c in cities:
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": c["lat"], "longitude": c["lon"],
                    "current": ",".join([
                        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                        "precipitation", "weather_code", "surface_pressure",
                        "wind_speed_10m", "cloud_cover", "visibility",
                    ]),
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "auto", "forecast_days": 1,
                },
                timeout=8,
            )
            if r.ok:
                d, cur = r.json(), r.json()["current"]
                results.append({
                    "city": c["city"], "flag": c["country"],
                    "temp": cur.get("temperature_2m"),
                    "feels": cur.get("apparent_temperature"),
                    "humidity": cur.get("relative_humidity_2m"),
                    "precip": cur.get("precipitation"),
                    "wind": cur.get("wind_speed_10m"),
                    "cloud": cur.get("cloud_cover"),
                    "vis": cur.get("visibility"),
                    "pressure": cur.get("surface_pressure"),
                    "code": cur.get("weather_code", 0),
                    "desc": WMO_CODES.get(cur.get("weather_code", 0), "?"),
                    "tmax": d["daily"]["temperature_2m_max"][0] if d.get("daily") else None,
                    "tmin": d["daily"]["temperature_2m_min"][0] if d.get("daily") else None,
                })
        except Exception:
            pass
    return results


# ── Page header ───────────────────────────────────────────────────────────────
col_t, col_s = st.columns([7, 3])
with col_t:
    st.markdown("""
    <div style="padding: 20px 0 8px">
      <div style="font-size:1.8rem; font-weight:700; color:#e2e8f0; letter-spacing:-.02em">
        🌤️ Weather Pipeline
      </div>
      <div style="font-size:0.85rem; color:#475569; margin-top:2px">
        Databricks · Open-Meteo · Delta Lake · MLflow · Streamlit
      </div>
    </div>
    """, unsafe_allow_html=True)
with col_s:
    st.markdown(f"""
    <div style="text-align:right; padding:20px 0 8px; font-family:'JetBrains Mono',monospace;">
      <div style="font-size:0.72rem; color:#475569">UPDATED</div>
      <div style="font-size:0.9rem; color:#38bdf8">{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
    </div>
    """, unsafe_allow_html=True)

if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
    st.error("⚠️  Thiếu credentials. Tạo `.streamlit/secrets.toml` với `DATABRICKS_HOST` và `DATABRICKS_TOKEN`.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs(["📊 Dashboard", "🤖 ML Insights", "🌍 Live Weather", "🚀 Pipeline", "📋 Workflows"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    col_r, col_ref = st.columns([8, 2])
    with col_ref:
        if st.button("🔄 Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df_latest = load_csv_from_workspace("gold_weather_latest.csv")
    df_daily  = load_csv_from_workspace("gold_weather_daily.csv")
    df_stats  = load_csv_from_workspace("gold_city_stats.csv")

    if df_latest is None:
        st.info("📂  Chưa có dữ liệu. Hãy chạy pipeline (tab Pipeline) ít nhất một lần.")
    else:
        # ── KPI row ────────────────────────────────────────────────────────
        n_cities   = len(df_latest)
        hottest    = df_latest.loc[df_latest["temperature_c"].idxmax()]
        coldest    = df_latest.loc[df_latest["temperature_c"].idxmin()]
        most_humid = df_latest.loc[df_latest["humidity"].idxmax()]
        avg_temp   = df_latest["temperature_c"].mean()

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Cities tracked",  n_cities)
        k2.metric("🌡️ Hottest city",   f"{hottest['city']}",
                  delta=f"{hottest['temperature_c']:.1f} °C")
        k3.metric("🧊 Coldest city",   f"{coldest['city']}",
                  delta=f"{coldest['temperature_c']:.1f} °C")
        k4.metric("💧 Avg global temp", f"{avg_temp:.1f} °C")

        st.markdown('<div class="section-title">Current Conditions per City</div>', unsafe_allow_html=True)

        # ── City cards (3 per row) ─────────────────────────────────────────
        sorted_latest = df_latest.sort_values("temperature_c", ascending=False).reset_index(drop=True)
        cols = st.columns(3)
        for i, row in sorted_latest.iterrows():
            flag = next((c["country"] for c in CITIES if c["city"] == row["city"]), "")
            tc   = temp_color(row.get("temperature_c"))
            with cols[i % 3]:
                st.markdown(f"""
                <div class="city-card">
                  <div class="city-name">{flag} {row['city']}</div>
                  <div class="city-temp" style="color:{tc}">{row['temperature_c']:.1f}°C</div>
                  <div class="city-desc">{row.get('weather_desc','—')}</div>
                  <div class="city-meta">
                    💧 {row.get('humidity','—')}%  &nbsp;
                    💨 {row.get('wind_speed_kmh','—')} km/h  &nbsp;
                    ☁️ {row.get('cloud_cover_pct','—')}%
                  </div>
                  <div style="margin-top:6px">
                    <span class="badge badge-blue">↑ {row.get('temp_max_c','—')}°</span>
                    <span class="badge badge-blue">↓ {row.get('temp_min_c','—')}°</span>
                    <span class="badge badge-amber">feels {row.get('feels_like_c','—')}°</span>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        # ── Temperature bar chart ──────────────────────────────────────────
        st.markdown('<div class="section-title">Temperature Comparison</div>', unsafe_allow_html=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=sorted_latest["city"],
            y=sorted_latest["temperature_c"],
            marker_color=[temp_color(t) for t in sorted_latest["temperature_c"]],
            text=[f"{t:.1f}°" for t in sorted_latest["temperature_c"]],
            textposition="outside", textfont=dict(color="#94a3b8", size=11),
            name="Current temp",
        ))
        fig_bar.add_trace(go.Scatter(
            x=sorted_latest["city"],
            y=sorted_latest["temp_max_c"],
            mode="markers", marker=dict(symbol="triangle-up", size=10, color="#f59e0b"),
            name="Max today",
        ))
        fig_bar.add_trace(go.Scatter(
            x=sorted_latest["city"],
            y=sorted_latest["temp_min_c"],
            mode="markers", marker=dict(symbol="triangle-down", size=10, color="#818cf8"),
            name="Min today",
        ))
        fig_bar.update_layout(**PLOTLY_LAYOUT, height=360, title="Current Temperature by City (°C)")
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Humidity + Wind ───────────────────────────────────────────────
        c1, c2 = st.columns(2)
        with c1:
            fig_hum = px.bar(
                sorted_latest, x="city", y="humidity",
                color="humidity",
                color_continuous_scale=["#1e3a5f", "#0369a1", "#38bdf8"],
                title="Humidity (%) by City",
            )
            fig_hum.update_layout(**PLOTLY_LAYOUT, height=300, coloraxis_showscale=False)
            st.plotly_chart(fig_hum, use_container_width=True)
        with c2:
            fig_wind = px.bar(
                sorted_latest, x="city", y="wind_speed_kmh",
                color="wind_speed_kmh",
                color_continuous_scale=["#1e3a5f", "#22c55e", "#f59e0b"],
                title="Wind Speed (km/h) by City",
            )
            fig_wind.update_layout(**PLOTLY_LAYOUT, height=300, coloraxis_showscale=False)
            st.plotly_chart(fig_wind, use_container_width=True)

        # ── Historical trend (if daily data available) ─────────────────────
        if df_daily is not None and len(df_daily) > 0:
            st.markdown('<div class="section-title">Historical Temperature Trends</div>', unsafe_allow_html=True)

            df_daily["date"] = pd.to_datetime(df_daily["date"])
            cities_sel = st.multiselect(
                "Chọn thành phố để xem lịch sử:",
                options=sorted(df_daily["city"].unique()),
                default=sorted(df_daily["city"].unique())[:5],
                key="hist_cities",
            )
            if cities_sel:
                df_filt = df_daily[df_daily["city"].isin(cities_sel)]
                fig_trend = px.line(
                    df_filt, x="date", y="avg_temp_c", color="city",
                    title="Average Daily Temperature (°C)",
                    labels={"avg_temp_c": "Temp (°C)", "date": "Date"},
                )
                fig_trend.update_traces(line=dict(width=2))
                fig_trend.update_layout(**PLOTLY_LAYOUT, height=380)
                st.plotly_chart(fig_trend, use_container_width=True)

                # Precipitation + UV
                c3, c4 = st.columns(2)
                with c3:
                    fig_precip = px.bar(
                        df_filt, x="date", y="avg_precipitation_mm", color="city",
                        title="Daily Precipitation (mm)", barmode="group",
                    )
                    fig_precip.update_layout(**PLOTLY_LAYOUT, height=280)
                    st.plotly_chart(fig_precip, use_container_width=True)
                with c4:
                    fig_uv = px.line(
                        df_filt, x="date", y="avg_uv_index", color="city",
                        title="UV Index", markers=True,
                    )
                    fig_uv.update_layout(**PLOTLY_LAYOUT, height=280)
                    st.plotly_chart(fig_uv, use_container_width=True)

        # ── City stats table ───────────────────────────────────────────────
        if df_stats is not None and len(df_stats) > 0:
            st.markdown('<div class="section-title">City Historical Statistics</div>', unsafe_allow_html=True)
            show_cols = [c for c in [
                "city", "country", "days_tracked",
                "overall_avg_temp", "overall_max_temp", "overall_min_temp",
                "avg_humidity", "avg_wind_speed", "avg_uv_index",
                "total_precipitation",
            ] if c in df_stats.columns]
            st.dataframe(
                df_stats[show_cols].sort_values("overall_avg_temp", ascending=False),
                use_container_width=True, hide_index=True,
            )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ML INSIGHTS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    col_ml, col_mlr = st.columns([8, 2])
    with col_mlr:
        if st.button("🔄 Refresh ML", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    df_summary    = load_csv_from_workspace("ml_summary.csv")
    df_metrics    = load_csv_from_workspace("ml_metrics.csv")
    df_feat_imp   = load_csv_from_workspace("ml_feature_importance.csv")
    df_full_pred  = load_csv_from_workspace("ml_full_predictions.csv")
    df_test_pred  = load_csv_from_workspace("ml_predictions.csv")
    df_forecast   = load_csv_from_workspace("ml_forecast.csv")

    if df_summary is None:
        st.info("📂  Chưa có kết quả ML. Hãy chạy notebook `04_ml_train` trước.")
    else:
        row = df_summary.iloc[0]

        # ── Model summary KPIs ─────────────────────────────────────────────
        st.markdown('<div class="section-title">Model Performance</div>', unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Best Model",        str(row.get("best_model", "—")))
        m2.metric("RMSE (test)",        f"{row.get('rmse_test', '—')} °C")
        m3.metric("MAE (test)",         f"{row.get('mae_test', '—')} °C")
        m4.metric("R² Score",           f"{row.get('r2_test', '—')}")
        m5.metric("Within ±1°C",        f"{row.get('within_1deg_pct', '—')}%")

        # ── Model comparison table ─────────────────────────────────────────
        if df_metrics is not None:
            st.markdown('<div class="section-title">Model Comparison</div>', unsafe_allow_html=True)
            df_metrics_show = df_metrics.copy()
            if "is_best" in df_metrics_show.columns:
                df_metrics_show["★"] = df_metrics_show["is_best"].map({True: "★ Best", False: ""})
                df_metrics_show = df_metrics_show.drop(columns=["is_best"])
            st.dataframe(
                df_metrics_show.sort_values("rmse_test"),
                use_container_width=True, hide_index=True,
            )

            fig_models = go.Figure()
            for metric, color, label in [
                ("rmse_test", "#ef4444", "RMSE"),
                ("mae_test",  "#f59e0b", "MAE"),
                ("r2_test",   "#22c55e", "R²"),
            ]:
                if metric in df_metrics.columns:
                    fig_models.add_trace(go.Bar(
                        name=label, x=df_metrics["model"], y=df_metrics[metric],
                        marker_color=color, text=df_metrics[metric].round(3),
                        textposition="outside",
                    ))
            fig_models.update_layout(
                **PLOTLY_LAYOUT, barmode="group", height=300,
                title="Model Metrics Comparison",
            )
            st.plotly_chart(fig_models, use_container_width=True)

        # ── Full prediction chart (actual vs predicted) ───────────────────
        if df_full_pred is not None and len(df_full_pred) > 0:
            st.markdown('<div class="section-title">Actual vs Predicted Temperature</div>', unsafe_allow_html=True)
            df_full_pred["date"] = pd.to_datetime(df_full_pred["date"])

            city_opts = sorted(df_full_pred["city"].unique())
            sel_city  = st.selectbox("Chọn thành phố:", city_opts, key="ml_city_sel")
            df_city   = df_full_pred[df_full_pred["city"] == sel_city].dropna(subset=["target_next_temp"])

            fig_avp = go.Figure()
            for split, color in [("train", "#1e3a5f"), ("test", "#0369a1")]:
                d = df_city[df_city["split"] == split]
                fig_avp.add_trace(go.Scatter(
                    x=d["date"], y=d["target_next_temp"], mode="lines",
                    name=f"Actual ({split})", line=dict(color=color, width=2),
                ))
            fig_avp.add_trace(go.Scatter(
                x=df_city["date"], y=df_city["predicted_temp"], mode="lines",
                name="Predicted", line=dict(color="#38bdf8", width=2, dash="dot"),
            ))
            # Test set boundary
            test_start = df_city[df_city["split"] == "test"]["date"].min()
            if pd.notna(test_start):
                fig_avp.add_vline(
                    x=test_start, line=dict(color="#f59e0b", dash="dash", width=1),
                    annotation_text="Test start", annotation_font_color="#f59e0b",
                )
            fig_avp.update_layout(**PLOTLY_LAYOUT, height=360, title=f"Temperature Forecast — {sel_city}")
            st.plotly_chart(fig_avp, use_container_width=True)

            # Scatter actual vs predicted (test only)
            df_test_city = df_city[df_city["split"] == "test"].dropna(subset=["target_next_temp", "predicted_temp"])
            if len(df_test_city) > 0:
                fig_scatter = px.scatter(
                    df_test_city,
                    x="target_next_temp", y="predicted_temp",
                    color="prediction_error",
                    color_continuous_scale="RdYlGn_r",
                    title=f"Actual vs Predicted — {sel_city} (Test Set)",
                    labels={"target_next_temp": "Actual (°C)", "predicted_temp": "Predicted (°C)"},
                )
                # Diagonal reference line
                min_v = df_test_city[["target_next_temp", "predicted_temp"]].min().min()
                max_v = df_test_city[["target_next_temp", "predicted_temp"]].max().max()
                fig_scatter.add_shape(type="line", x0=min_v, y0=min_v, x1=max_v, y1=max_v,
                                      line=dict(color="#64748b", dash="dash"))
                fig_scatter.update_layout(**PLOTLY_LAYOUT, height=350)
                st.plotly_chart(fig_scatter, use_container_width=True)

        # ── Feature importance ────────────────────────────────────────────
        if df_feat_imp is not None and len(df_feat_imp) > 0:
            st.markdown('<div class="section-title">Feature Importance</div>', unsafe_allow_html=True)
            top_n = st.slider("Top N features:", 5, min(30, len(df_feat_imp)), 15, key="feat_n")
            top_feats = df_feat_imp.head(top_n).sort_values("importance")
            fig_fi = go.Figure(go.Bar(
                x=top_feats["importance"],
                y=top_feats["feature"],
                orientation="h",
                marker=dict(
                    color=top_feats["importance"],
                    colorscale=[[0, "#1e3a5f"], [0.5, "#0369a1"], [1, "#38bdf8"]],
                ),
                text=top_feats["importance_pct"].apply(lambda x: f"{x:.1f}%") if "importance_pct" in top_feats.columns else None,
                textposition="outside",
            ))
            fig_fi.update_layout(
                **PLOTLY_LAYOUT, height=max(300, top_n * 28),
                title=f"Top {top_n} Feature Importances",
                xaxis_title="Importance",
            )
            st.plotly_chart(fig_fi, use_container_width=True)

        # ── Forecast ngày mai ─────────────────────────────────────────────
        if df_forecast is not None and len(df_forecast) > 0:
            st.markdown('<div class="section-title">Next Day Forecast (ML Prediction)</div>', unsafe_allow_html=True)
            df_forecast["forecast_date"] = pd.to_datetime(df_forecast["forecast_date"]).dt.date
            show_cols = [c for c in [
                "city", "country", "avg_temp_c",
                "forecast_temp_next_day", "forecast_date",
                "avg_humidity", "avg_wind_speed_kmh", "comfort_score",
            ] if c in df_forecast.columns]
            df_forecast_show = df_forecast[show_cols].copy()
            if "avg_temp_c" in df_forecast_show.columns and "forecast_temp_next_day" in df_forecast_show.columns:
                df_forecast_show["Δ temp"] = (
                    df_forecast_show["forecast_temp_next_day"] - df_forecast_show["avg_temp_c"]
                ).round(2)
            st.dataframe(
                df_forecast_show.sort_values("forecast_temp_next_day", ascending=False),
                use_container_width=True, hide_index=True,
            )

            # Forecast bar
            fig_fc = go.Figure()
            fig_fc.add_trace(go.Bar(
                x=df_forecast["city"],
                y=df_forecast["avg_temp_c"],
                name="Today", marker_color="#1e3a5f",
            ))
            fig_fc.add_trace(go.Bar(
                x=df_forecast["city"],
                y=df_forecast["forecast_temp_next_day"],
                name="Forecast tomorrow", marker_color="#38bdf8",
            ))
            fig_fc.update_layout(
                **PLOTLY_LAYOUT, barmode="group", height=320,
                title="Today vs ML Forecast Tomorrow (°C)",
            )
            st.plotly_chart(fig_fc, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — LIVE WEATHER
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="section-title">Live Weather — Open-Meteo (free, no API key)</div>', unsafe_allow_html=True)
    st.caption("Dữ liệu realtime từ api.open-meteo.com · cập nhật mỗi 15 phút")

    selected = st.multiselect(
        "Chọn thành phố:",
        options=[c["city"] for c in CITIES],
        default=[c["city"] for c in CITIES[:6]],
        key="live_cities",
    )
    selected_cities = [c for c in CITIES if c["city"] in selected]

    if st.button("🌐 Fetch Now", type="primary", key="fetch_live") and selected_cities:
        with st.spinner("Đang gọi Open-Meteo API..."):
            data = fetch_weather_live(selected_cities)

        if not data:
            st.error("Không lấy được dữ liệu. Kiểm tra kết nối mạng.")
        else:
            # Cards
            cols = st.columns(min(3, len(data)))
            for i, w in enumerate(data):
                with cols[i % 3]:
                    tc = temp_color(w["temp"])
                    st.markdown(f"""
                    <div class="city-card">
                      <div class="city-name">{w['flag']} {w['city']}</div>
                      <div class="city-temp" style="color:{tc}">{w['temp']}°C</div>
                      <div class="city-desc">{w['desc']}</div>
                      <div class="city-meta">
                        💧 {w['humidity']}%  &nbsp;
                        💨 {w['wind']} km/h  &nbsp;
                        ☁️ {w['cloud']}%
                      </div>
                      <div style="margin-top:6px">
                        <span class="badge badge-amber">feels {w['feels']}°</span>
                        <span class="badge badge-blue">↑{w.get('tmax','—')}° ↓{w.get('tmin','—')}°</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

            # Table + chart
            st.divider()
            df_live = pd.DataFrame([{
                "City":       f"{w['flag']} {w['city']}",
                "Temp (°C)":  w["temp"],
                "Feels (°C)": w["feels"],
                "Max/Min":    f"{w['tmax']}° / {w['tmin']}°" if w.get("tmax") else "—",
                "Humidity %": w["humidity"],
                "Wind km/h":  w["wind"],
                "Cloud %":    w["cloud"],
                "Precip mm":  w["precip"],
                "Condition":  w["desc"],
            } for w in data])
            st.dataframe(df_live, use_container_width=True, hide_index=True)

            # Mini radar / scatter
            fig_live = go.Figure(go.Scatterpolar(
                r=[w["humidity"] for w in data],
                theta=[w["city"] for w in data],
                fill="toself", line_color="#38bdf8",
                fillcolor="rgba(56,189,248,0.1)",
                name="Humidity %",
            ))
            fig_live.update_layout(
                polar=dict(
                    bgcolor="#080f1c",
                    radialaxis=dict(gridcolor="#1e3a5f", linecolor="#1e3a5f", tickfont=dict(color="#64748b")),
                    angularaxis=dict(linecolor="#1e3a5f", tickfont=dict(color="#94a3b8")),
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8"),
                height=380, title="Humidity Distribution",
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig_live, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.markdown('<div class="section-title">Full Pipeline</div>', unsafe_allow_html=True)
        st.markdown("""
        ```
        weather_crawler → bronze_ingest → silver_transform → gold_aggregate → ml_train
        ```
        """)
        try:
            job_id = get_job_id()
        except Exception:
            job_id = None

        if job_id:
            st.success(f"✓ Workflow **weather-pipeline** đã setup  ·  job_id: `{job_id}`")
            if st.button("▶ Trigger Full Pipeline", type="primary", use_container_width=True):
                resp = db_post("/api/2.1/jobs/run-now", {"job_id": job_id})
                st.success(f"✅ Triggered!  run_id: `{resp['run_id']}`")
                st.markdown(f"[🔗 Xem trên Databricks]({DATABRICKS_HOST}/jobs/{job_id}/runs/{resp['run_id']})")
        else:
            st.warning("Chưa có Workflow. Chạy `00_setup_workflow` trên Databricks trước.")
            st.code("Workspace → /Shared/weather-pipeline/00_setup_workflow → Run All", language="text")

    with col_r:
        st.markdown('<div class="section-title">Chạy từng notebook</div>', unsafe_allow_html=True)
        NOTEBOOKS = {
            "🕷️ Crawler":         "/Shared/weather-pipeline/weather_crawler",
            "🟤 01 Bronze":       "/Shared/weather-pipeline/01_bronze_ingest",
            "🥈 02 Silver":       "/Shared/weather-pipeline/02_silver_transform",
            "🥇 03 Gold":         "/Shared/weather-pipeline/03_gold_aggregate",
            "🤖 04 ML Train":     "/Shared/weather-pipeline/04_ml_train",
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


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 5 — WORKFLOWS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    STATE_EMOJI  = {"RUNNING": "🔵", "PENDING": "🟡", "TERMINATED": "⚪", "INTERNAL_ERROR": "🔴"}
    RESULT_EMOJI = {"SUCCESS": "✅", "FAILED": "❌", "CANCELED": "🚫", "TIMEDOUT": "⏱️"}

    st.markdown('<div class="section-title">Run History</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 4])
    with c1:
        if st.button("🔄 Refresh", use_container_width=True, key="wf_refresh"):
            st.rerun()
    with c2:
        rid_input = st.text_input("Kiểm tra run_id:", placeholder="123456")

    if rid_input:
        try:
            info   = db_get("/api/2.1/jobs/runs/get", {"run_id": int(rid_input)})
            s      = info.get("state", {})
            life, result = s.get("life_cycle_state", "?"), s.get("result_state", "—")
            m1, m2 = st.columns(2)
            m1.metric("State",  f"{STATE_EMOJI.get(life, '❓')} {life}")
            m2.metric("Result", f"{RESULT_EMOJI.get(result, '—')} {result}")
            if info.get("run_page_url"):
                st.markdown(f"[🔗 Mở trên Databricks]({info['run_page_url']})")
        except Exception as e:
            st.error(str(e))

    st.divider()
    try:
        job_id_wf = get_job_id()
        if job_id_wf:
            runs = db_get("/api/2.1/jobs/runs/list", {"job_id": job_id_wf, "limit": 10}).get("runs", [])
            rows = []
            for r in runs:
                s = r.get("state", {})
                life, result = s.get("life_cycle_state", "?"), s.get("result_state", "—")
                rows.append({
                    "run_id":   r["run_id"],
                    "state":    f"{STATE_EMOJI.get(life, '❓')} {life}",
                    "result":   f"{RESULT_EMOJI.get(result, '—')} {result}",
                    "started":  datetime.utcfromtimestamp(r.get("start_time", 0) / 1000).strftime("%Y-%m-%d %H:%M UTC"),
                    "link":     r.get("run_page_url", ""),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa tìm thấy job `weather-pipeline`.")
    except Exception as e:
        st.warning(f"Lỗi: {e}")