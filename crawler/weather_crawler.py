"""
Weather Crawler — dùng Open-Meteo API
✅ Hoàn toàn miễn phí, không cần đăng ký, không cần API key
Docs: https://open-meteo.com/en/docs
"""

import requests
import json
import os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "raw_data")

# WMO Weather Code → mô tả tiếng Anh
# https://open-meteo.com/en/docs#weathervariables
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}

# Tọa độ hardcode — không cần gọi geocoding API mỗi lần
CITIES = [
    {"city": "Ho Chi Minh City", "country": "VN", "lat": 10.8231, "lon": 106.6297, "timezone": "Asia/Ho_Chi_Minh"},
    {"city": "Hanoi",            "country": "VN", "lat": 21.0285, "lon": 105.8542, "timezone": "Asia/Bangkok"},
    {"city": "Tokyo",            "country": "JP", "lat": 35.6762, "lon": 139.6503, "timezone": "Asia/Tokyo"},
    {"city": "London",           "country": "GB", "lat": 51.5074, "lon": -0.1278,  "timezone": "Europe/London"},
    {"city": "New York",         "country": "US", "lat": 40.7128, "lon": -74.0060, "timezone": "America/New_York"},
    {"city": "Paris",            "country": "FR", "lat": 48.8566, "lon": 2.3522,   "timezone": "Europe/Paris"},
    {"city": "Sydney",           "country": "AU", "lat": -33.8688, "lon": 151.2093,"timezone": "Australia/Sydney"},
    {"city": "Dubai",            "country": "AE", "lat": 25.2048, "lon": 55.2708,  "timezone": "Asia/Dubai"},
    {"city": "Singapore",        "country": "SG", "lat": 1.3521,  "lon": 103.8198, "timezone": "Asia/Singapore"},
    {"city": "Bangkok",          "country": "TH", "lat": 13.7563, "lon": 100.5018, "timezone": "Asia/Bangkok"},
    {"city": "Mumbai",           "country": "IN", "lat": 19.0760, "lon": 72.8777,  "timezone": "Asia/Kolkata"},
    {"city": "Seoul",            "country": "KR", "lat": 37.5665, "lon": 126.9780, "timezone": "Asia/Seoul"},
    {"city": "Berlin",           "country": "DE", "lat": 52.5200, "lon": 13.4050,  "timezone": "Europe/Berlin"},
    {"city": "São Paulo",        "country": "BR", "lat": -23.5505, "lon": -46.6333,"timezone": "America/Sao_Paulo"},
    {"city": "Cairo",            "country": "EG", "lat": 30.0444, "lon": 31.2357,  "timezone": "Africa/Cairo"},
]

# Các biến cần lấy từ Open-Meteo
CURRENT_VARS = ",".join([
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "weather_code",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "cloud_cover",
    "visibility",
    "uv_index",
])

DAILY_VARS = ",".join([
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
    "uv_index_max",
    "sunrise",
    "sunset",
])


def crawl_city(city_info: dict) -> dict | None:
    """Crawl thời tiết hiện tại + daily forecast cho 1 thành phố"""
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":  city_info["lat"],
                "longitude": city_info["lon"],
                "current":   CURRENT_VARS,
                "daily":     DAILY_VARS,
                "timezone":  city_info["timezone"],
                "forecast_days": 1,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()

        cur   = data["current"]
        daily = data["daily"]
        wcode = cur.get("weather_code", 0)

        record = {
            # Định danh
            "city":        city_info["city"],
            "country":     city_info["country"],
            "latitude":    city_info["lat"],
            "longitude":   city_info["lon"],
            "timezone":    city_info["timezone"],

            # Thời tiết hiện tại
            "temperature_c":      cur.get("temperature_2m"),
            "feels_like_c":       cur.get("apparent_temperature"),
            "humidity":           cur.get("relative_humidity_2m"),
            "pressure_hpa":       cur.get("surface_pressure"),
            "precipitation_mm":   cur.get("precipitation"),
            "rain_mm":            cur.get("rain"),
            "cloud_cover_pct":    cur.get("cloud_cover"),
            "visibility_m":       cur.get("visibility"),
            "wind_speed_kmh":     cur.get("wind_speed_10m"),
            "wind_direction_deg": cur.get("wind_direction_10m"),
            "wind_gusts_kmh":     cur.get("wind_gusts_10m"),
            "uv_index":           cur.get("uv_index"),
            "weather_code":       wcode,
            "weather_desc":       WMO_CODES.get(wcode, f"Code {wcode}"),

            # Daily summary (ngày hôm nay)
            "temp_max_c":         daily["temperature_2m_max"][0] if daily.get("temperature_2m_max") else None,
            "temp_min_c":         daily["temperature_2m_min"][0] if daily.get("temperature_2m_min") else None,
            "precip_sum_mm":      daily["precipitation_sum"][0]  if daily.get("precipitation_sum")  else None,
            "wind_max_kmh":       daily["wind_speed_10m_max"][0] if daily.get("wind_speed_10m_max") else None,
            "uv_index_max":       daily["uv_index_max"][0]       if daily.get("uv_index_max")       else None,
            "sunrise":            daily["sunrise"][0]             if daily.get("sunrise")            else None,
            "sunset":             daily["sunset"][0]              if daily.get("sunset")             else None,

            # Metadata
            "crawled_at": datetime.utcnow().isoformat(),
        }

        print(
            f"  ✓ {city_info['city']:20} "
            f"{record['temperature_c']:5.1f}°C  "
            f"💧{record['humidity']}%  "
            f"💨{record['wind_speed_kmh']} km/h  "
            f"{record['weather_desc']}"
        )
        return record

    except Exception as e:
        print(f"  ✗ {city_info['city']}: {e}")
        return None


def crawl() -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"=== Open-Meteo Crawler — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} ===")

    results = []
    for city_info in CITIES:
        record = crawl_city(city_info)
        if record:
            results.append(record)

    ts   = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"weather_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved {len(results)}/{len(CITIES)} cities → {path}")
    return path


if __name__ == "__main__":
    crawl()
