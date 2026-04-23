"""
Streamlit UI — Weather Pipeline Dashboard
Chạy: streamlit run streamlit_app/app.py
Không cần API key nào ngoài Databricks token
"""

import os
import sys
from datetime import datetime

import requests
import streamlit as st

# ── Config ────────────────────────────────────────────────────────────────────
DATABRICKS_HOST  = st.secrets.get("DATABRICKS_HOST", os.getenv("DATABRICKS_HOST", "")).rstrip("/")
DATABRICKS_TOKEN = st.secrets.get("DATABRICKS_TOKEN", os.getenv("DATABRICKS_TOKEN", ""))

NOTEBOOKS = {
    "01 — Bronze":  "/Shared/weather-pipeline/01_bronze_ingest",
    "02 — Silver":  "/Shared/weather-pipeline/02_silver_transform",
    "03 — Gold":    "/Shared/weather-pipeline/03_gold_aggregate",
    "04 — ML":      "/Shared/weather-pipeline/04_ml_train",
}

CITIES = [
    {"city": "Ho Chi Minh City", "country": "🇻🇳", "lat": 10.8231,  "lon": 106.6297},
    {"city": "Hanoi",            "country": "🇻🇳", "lat": 21.0285,  "lon": 105.8542},
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
    {"city": "Cairo",            "country": "🇪🇬", "lat": 30.0444,  "lon": 31.2357 },
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

STATE_EMOJI  = {"RUNNING": "🔵", "PENDING": "🟡", "TERMINATED": "⚪", "INTERNAL_ERROR": "🔴"}
RESULT_EMOJI = {"SUCCESS": "✅", "FAILED": "❌", "CANCELED": "🚫", "TIMEDOUT": "⏱️"}


# ── Databricks helpers ────────────────────────────────────────────────────────
def hdr():
    return {"Authorization": f"Bearer {DATABRICKS_TOKEN}", "Content-Type": "application/json"}

def db_get(path, params=None):
    r = requests.get(f"{DATABRICKS_HOST}{path}", headers=hdr(), params=params, timeout=15)
    r.raise_for_status()
    return r.json()

def db_post(path, payload):
    r = requests.post(f"{DATABRICKS_HOST}{path}", headers=hdr(), json=payload, timeout=15)
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


# ── Open-Meteo helper (no API key) ────────────────────────────────────────────
def fetch_weather_open_meteo(cities: list) -> list:
    """Gọi Open-Meteo cho nhiều thành phố — hoàn toàn free, không cần key"""
    results = []
    for c in cities:
        try:
            r = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude":  c["lat"],
                    "longitude": c["lon"],
                    "current": ",".join([
                        "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                        "precipitation", "weather_code", "surface_pressure",
                        "wind_speed_10m", "cloud_cover", "visibility",
                    ]),
                    "daily": "temperature_2m_max,temperature_2m_min",
                    "timezone": "auto",
                    "forecast_days": 1,
                },
                timeout=8,
            )
            if r.status_code == 200:
                d   = r.json()
                cur = d["current"]
                results.append({
                    "city":    c["city"],
                    "flag":    c["country"],
                    "temp":    cur.get("temperature_2m"),
                    "feels":   cur.get("apparent_temperature"),
                    "humidity": cur.get("relative_humidity_2m"),
                    "precip":  cur.get("precipitation"),
                    "wind":    cur.get("wind_speed_10m"),
                    "cloud":   cur.get("cloud_cover"),
                    "vis":     cur.get("visibility"),
                    "pressure": cur.get("surface_pressure"),
                    "code":    cur.get("weather_code", 0),
                    "desc":    WMO_CODES.get(cur.get("weather_code", 0), "?"),
                    "tmax":    d["daily"]["temperature_2m_max"][0] if d.get("daily") else None,
                    "tmin":    d["daily"]["temperature_2m_min"][0] if d.get("daily") else None,
                })
        except Exception:
            pass
    return results


# ── Page ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Weather Pipeline", page_icon="🌤️", layout="wide")
st.title("🌤️ Weather Pipeline Dashboard")
st.caption("Databricks Community Edition · Open-Meteo · Delta Lake · MLflow")

if not DATABRICKS_HOST or not DATABRICKS_TOKEN:
    st.error("⚠️ Tạo `.streamlit/secrets.toml` với `DATABRICKS_HOST` và `DATABRICKS_TOKEN`.")
    st.stop()

tabs = st.tabs(["🚀 Pipeline", "📋 Workflows", "🌍 Live Weather"])

# ── Tab 1: Pipeline ────────────────────────────────────────────────────────────
with tabs[0]:
    col_l, col_r = st.columns([3, 2])

    with col_l:
        st.subheader("Chạy toàn bộ pipeline")
        try:
            job_id = get_job_id()
        except Exception:
            job_id = None

        if job_id:
            st.success(f"Workflow **weather-pipeline** đã setup · job_id: `{job_id}`")
            if st.button("▶ Trigger Full Pipeline", type="primary", use_container_width=True):
                resp = db_post("/api/2.1/jobs/run-now", {"job_id": job_id})
                st.success(f"✅ Triggered! run_id: `{resp['run_id']}`")
                st.markdown(f"[🔗 Xem trên Databricks]({DATABRICKS_HOST}/jobs/{job_id}/runs/{resp['run_id']})")
        else:
            st.warning("Chưa có Workflow. Chạy notebook `00_setup_workflow` trên Databricks trước.")
            st.code("Workspace → /Shared/weather-pipeline/00_setup_workflow → Run All", language="text")

    with col_r:
        st.subheader("Chạy từng notebook")
        try:
            clusters = list_clusters()
            if clusters:
                opts = {f"{c['cluster_name']} ({c['cluster_id']})": c["cluster_id"] for c in clusters}
                cid  = opts[st.selectbox("Cluster:", list(opts.keys()))]
                for label, path in NOTEBOOKS.items():
                    if st.button(label, use_container_width=True):
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

# ── Tab 2: Workflow status ──────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("Lịch sử runs")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with c2:
        rid_input = st.text_input("Kiểm tra run_id:", placeholder="123456")

    if rid_input:
        try:
            info   = db_get("/api/2.1/jobs/runs/get", {"run_id": int(rid_input)})
            s      = info.get("state", {})
            life, result = s.get("life_cycle_state","?"), s.get("result_state","—")
            m1, m2 = st.columns(2)
            m1.metric("State",  f"{STATE_EMOJI.get(life,'❓')} {life}")
            m2.metric("Result", f"{RESULT_EMOJI.get(result,'—')} {result}")
            if info.get("run_page_url"):
                st.markdown(f"[🔗 Mở trên Databricks]({info['run_page_url']})")
        except Exception as e:
            st.error(str(e))

    st.divider()
    try:
        job_id = get_job_id()
        if job_id:
            runs = db_get("/api/2.1/jobs/runs/list", {"job_id": job_id, "limit": 8}).get("runs", [])
            rows = []
            for r in runs:
                s = r.get("state", {})
                life, result = s.get("life_cycle_state","?"), s.get("result_state","—")
                rows.append({
                    "run_id":  r["run_id"],
                    "state":   f"{STATE_EMOJI.get(life,'❓')} {life}",
                    "result":  f"{RESULT_EMOJI.get(result,'—')} {result}",
                    "started": datetime.utcfromtimestamp(r.get("start_time",0)/1000).strftime("%Y-%m-%d %H:%M UTC"),
                    "link":    r.get("run_page_url",""),
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa tìm thấy job `weather-pipeline`.")
    except Exception as e:
        st.warning(f"Lỗi lấy runs: {e}")

# ── Tab 3: Live Weather (Open-Meteo — không cần key) ─────────────────────────
with tabs[2]:
    st.subheader("🌍 Live Weather  ·  Open-Meteo (free, no API key)")
    st.caption("Dữ liệu cập nhật mỗi 15 phút từ api.open-meteo.com")

    selected = st.multiselect(
        "Chọn thành phố:",
        options=[c["city"] for c in CITIES],
        default=[c["city"] for c in CITIES[:6]],
    )
    selected_cities = [c for c in CITIES if c["city"] in selected]

    if st.button("🌐 Fetch Now", type="primary") and selected_cities:
        with st.spinner("Đang gọi Open-Meteo API..."):
            data = fetch_weather_open_meteo(selected_cities)

        if not data:
            st.error("Không lấy được dữ liệu. Kiểm tra kết nối mạng.")
        else:
            cols = st.columns(3)
            for i, w in enumerate(data):
                with cols[i % 3]:
                    st.metric(
                        label=f"{w['flag']} {w['city']}",
                        value=f"{w['temp']}°C",
                        delta=f"↑{w['tmax']}° ↓{w['tmin']}°" if w.get("tmax") else None,
                    )
                    st.caption(w["desc"])
                    st.caption(
                        f"💧 {w['humidity']}%  "
                        f"💨 {w['wind']} km/h  "
                        f"☁️ {w['cloud']}%  "
                        f"🌡️ feels {w['feels']}°C"
                    )

            st.divider()
            st.dataframe(
                [{
                    "City":       f"{w['flag']} {w['city']}",
                    "Temp (°C)":  w["temp"],
                    "Feels (°C)": w["feels"],
                    "Max/Min":    f"{w['tmax']}° / {w['tmin']}°" if w.get("tmax") else "—",
                    "Humidity %": w["humidity"],
                    "Wind km/h":  w["wind"],
                    "Cloud %":    w["cloud"],
                    "Precip mm":  w["precip"],
                    "Condition":  w["desc"],
                } for w in data],
                use_container_width=True,
                hide_index=True,
            )
