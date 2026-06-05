import { useState } from 'react'
import { Card, Badge } from '../components/UI'

// ═══════════════════════════════════════════════════════════════════════════════
// RAW DATA — 10 records thực từ crawler 2026-04-22T07:59 (27 fields mỗi record)
// ═══════════════════════════════════════════════════════════════════════════════
const RAW = [
  { city:'Ho Chi Minh City',country:'VN',latitude:10.8231,longitude:106.6297,timezone:'Asia/Ho_Chi_Minh',temperature_c:34.6,feels_like_c:37.5,humidity:46,pressure_hpa:1005.4,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:65,visibility_m:24140,wind_speed_kmh:12.5,wind_direction_deg:147,wind_gusts_kmh:27.7,uv_index:6.7,weather_code:2,weather_desc:'Partly cloudy',temp_max_c:34.8,temp_min_c:25.2,precip_sum_mm:0.0,wind_max_kmh:13.7,uv_index_max:9.2,sunrise:'2026-04-22T05:39',sunset:'2026-04-22T18:05',crawled_at:'2026-04-22T07:59:30' },
  { city:'Hanoi',country:'VN',latitude:21.0285,longitude:105.8542,timezone:'Asia/Bangkok',temperature_c:33.8,feels_like_c:39.7,humidity:61,pressure_hpa:1000.4,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:54,visibility_m:24140,wind_speed_kmh:10.2,wind_direction_deg:135,wind_gusts_kmh:20.9,uv_index:6.65,weather_code:2,weather_desc:'Partly cloudy',temp_max_c:33.8,temp_min_c:24.4,precip_sum_mm:0.3,wind_max_kmh:14.7,uv_index_max:7.8,sunrise:'2026-04-22T05:32',sunset:'2026-04-22T18:17',crawled_at:'2026-04-22T07:59:31' },
  { city:'Tokyo',country:'JP',latitude:35.6762,longitude:139.6503,timezone:'Asia/Tokyo',temperature_c:18.3,feels_like_c:17.1,humidity:61,pressure_hpa:1008.2,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:68,visibility_m:24140,wind_speed_kmh:9.8,wind_direction_deg:188,wind_gusts_kmh:47.9,uv_index:0.95,weather_code:2,weather_desc:'Partly cloudy',temp_max_c:20.6,temp_min_c:7.4,precip_sum_mm:0.0,wind_max_kmh:11.3,uv_index_max:7.2,sunrise:'2026-04-22T05:00',sunset:'2026-04-22T18:19',crawled_at:'2026-04-22T07:59:31' },
  { city:'London',country:'GB',latitude:51.5074,longitude:-0.1278,timezone:'Europe/London',temperature_c:10.0,feels_like_c:6.6,humidity:74,pressure_hpa:1024.0,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:10,visibility_m:12940,wind_speed_kmh:15.5,wind_direction_deg:60,wind_gusts_kmh:34.2,uv_index:0.9,weather_code:0,weather_desc:'Clear sky',temp_max_c:16.0,temp_min_c:6.9,precip_sum_mm:0.0,wind_max_kmh:21.2,uv_index_max:4.15,sunrise:'2026-04-22T05:49',sunset:'2026-04-22T20:08',crawled_at:'2026-04-22T07:59:32' },
  { city:'New York',country:'US',latitude:40.7128,longitude:-74.006,timezone:'America/New_York',temperature_c:7.1,feels_like_c:3.9,humidity:73,pressure_hpa:1017.6,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:100,visibility_m:22400,wind_speed_kmh:10.8,wind_direction_deg:165,wind_gusts_kmh:31.7,uv_index:0.0,weather_code:3,weather_desc:'Overcast',temp_max_c:12.3,temp_min_c:6.8,precip_sum_mm:0.2,wind_max_kmh:22.3,uv_index_max:3.3,sunrise:'2026-04-22T06:06',sunset:'2026-04-22T19:42',crawled_at:'2026-04-22T07:59:33' },
  { city:'Paris',country:'FR',latitude:48.8566,longitude:2.3522,timezone:'Europe/Paris',temperature_c:10.2,feels_like_c:6.0,humidity:53,pressure_hpa:1016.8,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:0,visibility_m:40340,wind_speed_kmh:15.1,wind_direction_deg:65,wind_gusts_kmh:31.0,uv_index:2.05,weather_code:0,weather_desc:'Clear sky',temp_max_c:19.1,temp_min_c:8.0,precip_sum_mm:0.0,wind_max_kmh:21.0,uv_index_max:6.0,sunrise:'2026-04-22T06:45',sunset:'2026-04-22T20:52',crawled_at:'2026-04-22T07:59:33' },
  { city:'Sydney',country:'AU',latitude:-33.8688,longitude:151.2093,timezone:'Australia/Sydney',temperature_c:17.6,feels_like_c:16.9,humidity:66,pressure_hpa:1015.6,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:16,visibility_m:24140,wind_speed_kmh:7.4,wind_direction_deg:157,wind_gusts_kmh:25.9,uv_index:0.05,weather_code:1,weather_desc:'Mainly clear',temp_max_c:21.4,temp_min_c:13.3,precip_sum_mm:0.0,wind_max_kmh:15.3,uv_index_max:5.15,sunrise:'2026-04-22T06:23',sunset:'2026-04-22T17:24',crawled_at:'2026-04-22T07:59:34' },
  { city:'Dubai',country:'AE',latitude:25.2048,longitude:55.2708,timezone:'Asia/Dubai',temperature_c:31.7,feels_like_c:35.3,humidity:50,pressure_hpa:1006.1,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:100,visibility_m:24140,wind_speed_kmh:13.5,wind_direction_deg:25,wind_gusts_kmh:23.0,uv_index:8.2,weather_code:3,weather_desc:'Overcast',temp_max_c:32.7,temp_min_c:26.6,precip_sum_mm:0.0,wind_max_kmh:16.0,uv_index_max:8.8,sunrise:'2026-04-22T05:50',sunset:'2026-04-22T18:44',crawled_at:'2026-04-22T07:59:35' },
  { city:'Singapore',country:'SG',latitude:1.3521,longitude:103.8198,timezone:'Asia/Singapore',temperature_c:31.1,feels_like_c:35.9,humidity:60,pressure_hpa:1001.3,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:100,visibility_m:24140,wind_speed_kmh:2.2,wind_direction_deg:180,wind_gusts_kmh:5.8,uv_index:6.1,weather_code:3,weather_desc:'Overcast',temp_max_c:31.2,temp_min_c:24.7,precip_sum_mm:0.0,wind_max_kmh:7.7,uv_index_max:8.0,sunrise:'2026-04-22T06:58',sunset:'2026-04-22T19:07',crawled_at:'2026-04-22T07:59:36' },
  { city:'Bangkok',country:'TH',latitude:13.7563,longitude:100.5018,timezone:'Asia/Bangkok',temperature_c:34.3,feels_like_c:40.0,humidity:56,pressure_hpa:1005.6,precipitation_mm:0.0,rain_mm:0.0,cloud_cover_pct:31,visibility_m:24140,wind_speed_kmh:13.3,wind_direction_deg:167,wind_gusts_kmh:34.6,uv_index:7.4,weather_code:1,weather_desc:'Mainly clear',temp_max_c:34.6,temp_min_c:28.6,precip_sum_mm:0.4,wind_max_kmh:13.7,uv_index_max:9.2,sunrise:'2026-04-22T06:00',sunset:'2026-04-22T18:32',crawled_at:'2026-04-22T07:59:36' },
]

// ═══════════════════════════════════════════════════════════════════════════════
// SILVER — Bronze + cast types + date/hour/crawl_hour + is_valid + processed_at
// ═══════════════════════════════════════════════════════════════════════════════
const SILVER = RAW.map(r => ({
  ...r,
  // thêm sau khi cast
  date:         r.crawled_at.slice(0,10),
  hour:         parseInt(r.crawled_at.slice(11,13)),
  crawl_hour:   r.crawled_at.slice(0,13) + ':00',
  is_valid:     r.temperature_c >= -60 && r.temperature_c <= 60 && r.humidity >= 0 && r.humidity <= 100,
  processed_at: '2026-04-22T08:02:15',
}))

// ═══════════════════════════════════════════════════════════════════════════════
// Helpers tính derived features (dùng đúng công thức trong 03_gold_aggregate.py)
// ═══════════════════════════════════════════════════════════════════════════════
function heatIndex(T, R) {
  return parseFloat((-8.78469475556 + 1.61139411*T + 2.33854883889*R
    - 0.14611605*T*R - 0.012308094*T**2 - 0.016424828*R**2
    + 0.002211732*T**2*R + 0.00072546*T*R**2 - 0.000003582*T**2*R**2).toFixed(1))
}
function comfortScore(T, R, W) {
  const ts = Math.min(100, Math.max(0, 100 - 4*Math.abs(T-22)))
  const hs = Math.min(100, Math.max(0, 100 - 2*Math.abs(R-50)))
  const ws = Math.min(100, Math.max(0, 100 - 3*Math.abs(W-10)))
  return parseFloat(((ts+hs+ws)/3).toFixed(1))
}
function severity(precip, wind) {
  if (precip > 20 && wind > 60) return 4
  if (wind > 50) return 3
  if (precip > 15) return 2
  if (precip > 5) return 1
  return 0
}

// ═══════════════════════════════════════════════════════════════════════════════
// GOLD 1 — gold_weather_daily: GROUP BY city+date → avg/max/min + derived
// ═══════════════════════════════════════════════════════════════════════════════
const GOLD_DAILY = SILVER.map(r => ({
  date:                 r.date,
  city:                 r.city,
  country:              r.country,
  avg_temp_c:           r.temperature_c,
  max_temp_c:           r.temp_max_c,
  min_temp_c:           r.temp_min_c,
  avg_feels_like_c:     r.feels_like_c,
  avg_humidity:         r.humidity,
  avg_pressure_hpa:     r.pressure_hpa,
  avg_wind_speed_kmh:   r.wind_speed_kmh,
  max_wind_speed_kmh:   r.wind_gusts_kmh,
  avg_cloud_pct:        r.cloud_cover_pct,
  avg_precipitation_mm: r.precipitation_mm,
  avg_uv_index:         r.uv_index,
  temp_range:           parseFloat((r.temp_max_c - r.temp_min_c).toFixed(2)),
  heat_index:           heatIndex(r.temperature_c, r.humidity),
  comfort_score:        comfortScore(r.temperature_c, r.humidity, r.wind_speed_kmh),
  weather_severity:     severity(r.precipitation_mm, r.wind_speed_kmh),
  sample_count:         1,
}))

// ═══════════════════════════════════════════════════════════════════════════════
// GOLD 2 — gold_weather_latest: snapshot mới nhất mỗi city (từ silver)
// ═══════════════════════════════════════════════════════════════════════════════
const GOLD_LATEST = SILVER.map(r => ({
  city:             r.city,
  country:          r.country,
  temperature_c:    r.temperature_c,
  feels_like_c:     r.feels_like_c,
  temp_max_c:       r.temp_max_c,
  temp_min_c:       r.temp_min_c,
  humidity:         r.humidity,
  pressure_hpa:     r.pressure_hpa,
  wind_speed_kmh:   r.wind_speed_kmh,
  wind_gusts_kmh:   r.wind_gusts_kmh,
  precipitation_mm: r.precipitation_mm,
  cloud_cover_pct:  r.cloud_cover_pct,
  uv_index:         r.uv_index,
  weather_desc:     r.weather_desc,
  sunrise:          r.sunrise,
  sunset:           r.sunset,
  crawled_at:       r.crawled_at,
}))

// ═══════════════════════════════════════════════════════════════════════════════
// GOLD 3 — gold_ml_features: daily + temporal encoding + lag + rolling
// (lag/rolling = null vì mới 1 ngày dữ liệu — fillna khi train)
// ═══════════════════════════════════════════════════════════════════════════════
const GOLD_ML = GOLD_DAILY.map(r => ({
  date:               r.date,
  city:               r.city,
  avg_temp_c:         r.avg_temp_c,
  avg_humidity:       r.avg_humidity,
  avg_wind_speed_kmh: r.avg_wind_speed_kmh,
  avg_precipitation_mm: r.avg_precipitation_mm,
  // Temporal encoding (tháng 4, ngày 112/365)
  month_sin:          parseFloat(Math.sin(2*Math.PI*4/12).toFixed(4)),
  month_cos:          parseFloat(Math.cos(2*Math.PI*4/12).toFixed(4)),
  doy_sin:            parseFloat(Math.sin(2*Math.PI*112/365).toFixed(4)),
  doy_cos:            parseFloat(Math.cos(2*Math.PI*112/365).toFixed(4)),
  is_weekend:         0,
  // Lag features (null khi chưa đủ lịch sử)
  temp_lag1:          null,
  temp_lag2:          null,
  temp_lag3:          null,
  temp_lag7:          null,
  humidity_lag1:      null,
  // Rolling features (null khi chưa đủ lịch sử)
  temp_roll_mean_3d:  null,
  temp_roll_mean_7d:  null,
  temp_roll_std_3d:   null,
  temp_roll_std_7d:   null,
  precip_roll_sum_3d: null,
  // Derived
  temp_range:         r.temp_range,
  heat_index:         r.heat_index,
  comfort_score:      r.comfort_score,
  weather_severity:   r.weather_severity,
  // Target (null = ngày cuối, không có ngày hôm sau)
  target_next_temp:   null,
}))

// ═══════════════════════════════════════════════════════════════════════════════
// GOLD 4 — gold_city_stats: aggregate toàn bộ lịch sử mỗi city
// ═══════════════════════════════════════════════════════════════════════════════
const GOLD_STATS = GOLD_DAILY.map(r => ({
  city:                r.city,
  country:             r.country,
  days_tracked:        1,
  overall_avg_temp:    r.avg_temp_c,
  overall_max_temp:    r.max_temp_c,
  overall_min_temp:    r.min_temp_c,
  temp_std:            0.0,
  avg_humidity:        r.avg_humidity,
  avg_wind_speed:      r.avg_wind_speed_kmh,
  avg_precipitation:   r.avg_precipitation_mm,
  avg_uv_index:        r.avg_uv_index,
  avg_cloud_pct:       r.avg_cloud_pct,
  total_precipitation: r.avg_precipitation_mm,
  first_recorded:      r.date,
  last_recorded:       r.date,
}))

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIG: 4 Gold sub-tables
// ═══════════════════════════════════════════════════════════════════════════════
const GOLD_TABLES = [
  {
    id: 'daily',
    label: 'gold_weather_daily',
    desc: 'Lịch sử tích lũy theo ngày · GROUP BY (city, date) từ Silver · Chiến lược: append + dedup',
    rows: GOLD_DAILY,
    cols: [
      {k:'date',w:95},{k:'city',w:130},{k:'country',w:60},
      {k:'avg_temp_c',w:78},{k:'max_temp_c',w:78},{k:'min_temp_c',w:78},
      {k:'avg_feels_like_c',w:100},{k:'avg_humidity',w:85},
      {k:'avg_pressure_hpa',w:105},{k:'avg_wind_speed_kmh',w:110},
      {k:'avg_cloud_pct',w:90},{k:'avg_precipitation_mm',w:115},
      {k:'avg_uv_index',w:80},{k:'temp_range',w:90},
      {k:'heat_index',w:90},{k:'comfort_score',w:100},
      {k:'weather_severity',w:105},{k:'sample_count',w:85},
    ],
  },
  {
    id: 'latest',
    label: 'gold_weather_latest',
    desc: 'Snapshot thời tiết mới nhất mỗi thành phố · Window ROW_NUMBER() OVER (PARTITION BY city ORDER BY crawled_at DESC) · Chiến lược: overwrite',
    rows: GOLD_LATEST,
    cols: [
      {k:'city',w:130},{k:'country',w:60},
      {k:'temperature_c',w:90},{k:'feels_like_c',w:85},
      {k:'temp_max_c',w:80},{k:'temp_min_c',w:80},
      {k:'humidity',w:75},{k:'pressure_hpa',w:95},
      {k:'wind_speed_kmh',w:95},{k:'wind_gusts_kmh',w:100},
      {k:'precipitation_mm',w:105},{k:'cloud_cover_pct',w:90},
      {k:'uv_index',w:68},{k:'weather_desc',w:120},
      {k:'sunrise',w:130},{k:'sunset',w:130},{k:'crawled_at',w:145},
    ],
  },
  {
    id: 'ml',
    label: 'gold_ml_features',
    desc: 'Feature engineering cho ML · Temporal encoding sin/cos, lag 1/2/3/7d, rolling mean/std 3d/7d · Chiến lược: overwrite (tính lại từ full history)',
    rows: GOLD_ML,
    cols: [
      {k:'date',w:95},{k:'city',w:130},
      {k:'avg_temp_c',w:85},{k:'avg_humidity',w:90},
      {k:'avg_wind_speed_kmh',w:115},{k:'avg_precipitation_mm',w:120},
      {k:'month_sin',w:90},{k:'month_cos',w:90},
      {k:'doy_sin',w:80},{k:'doy_cos',w:80},{k:'is_weekend',w:80},
      {k:'temp_lag1',w:80},{k:'temp_lag3',w:80},{k:'temp_lag7',w:80},
      {k:'humidity_lag1',w:95},
      {k:'temp_roll_mean_3d',w:125},{k:'temp_roll_mean_7d',w:125},
      {k:'temp_roll_std_3d',w:120},{k:'temp_roll_std_7d',w:120},
      {k:'precip_roll_sum_3d',w:130},
      {k:'temp_range',w:90},{k:'heat_index',w:90},
      {k:'comfort_score',w:105},{k:'weather_severity',w:110},
      {k:'target_next_temp',w:120},
    ],
  },
  {
    id: 'stats',
    label: 'gold_city_stats',
    desc: 'Thống kê tổng hợp toàn bộ lịch sử mỗi thành phố · dùng cho Dashboard "Historical Stats" · Chiến lược: overwrite',
    rows: GOLD_STATS,
    cols: [
      {k:'city',w:130},{k:'country',w:60},
      {k:'days_tracked',w:95},{k:'overall_avg_temp',w:115},
      {k:'overall_max_temp',w:115},{k:'overall_min_temp',w:115},
      {k:'temp_std',w:80},{k:'avg_humidity',w:90},
      {k:'avg_wind_speed',w:100},{k:'avg_precipitation',w:115},
      {k:'avg_uv_index',w:90},{k:'avg_cloud_pct',w:90},
      {k:'total_precipitation',w:120},
      {k:'first_recorded',w:110},{k:'last_recorded',w:110},
    ],
  },
]

// ═══════════════════════════════════════════════════════════════════════════════
// Layer metadata
// ═══════════════════════════════════════════════════════════════════════════════
const LAYERS = {
  bronze: {
    icon:'🟤', label:'Bronze', subtitle:'Raw Ingestion Layer',
    color:{ bg:'rgba(180,83,9,0.10)', border:'#b45309', text:'#fbbf24' },
    notebook:'01_bronze_ingest', storage:'weather_bronze.bronze_weather_raw',
    strategy:'append-only — giữ toàn bộ lịch sử',
    description:'Đọc file JSON từ crawler và ghi thẳng vào Delta Table mà không chỉnh sửa bất kỳ field nào. Toàn bộ 27 fields từ API được giữ nguyên cộng thêm 3 metadata. Append-only đảm bảo có thể replay lại toàn bộ pipeline từ đầu nếu cần.',
    bullets:[
      {ok:false, text:'✗ Không validate kiểu dữ liệu'},
      {ok:false, text:'✗ Không loại bỏ bản ghi trùng'},
      {ok:true,  text:'✓ Giữ toàn bộ 27 fields gốc từ API'},
      {ok:true,  text:'✓ Thêm metadata: ingested_at, source_file, source_seq'},
      {ok:true,  text:'✓ mergeSchema=true để tự động mở rộng schema'},
    ],
    cols:[
      {k:'city',w:130},{k:'country',w:60},
      {k:'latitude',w:75},{k:'longitude',w:80},{k:'timezone',w:130},
      {k:'temperature_c',w:90},{k:'feels_like_c',w:85},
      {k:'humidity',w:75},{k:'pressure_hpa',w:95},
      {k:'precipitation_mm',w:105},{k:'rain_mm',w:75},
      {k:'cloud_cover_pct',w:90},{k:'visibility_m',w:90},
      {k:'wind_speed_kmh',w:95},{k:'wind_direction_deg',w:115},
      {k:'wind_gusts_kmh',w:100},{k:'uv_index',w:68},
      {k:'weather_code',w:95},{k:'weather_desc',w:120},
      {k:'temp_max_c',w:80},{k:'temp_min_c',w:80},
      {k:'precip_sum_mm',w:100},{k:'wind_max_kmh',w:90},
      {k:'uv_index_max',w:90},{k:'sunrise',w:130},{k:'sunset',w:130},
      {k:'crawled_at',w:145},
    ],
    rows: RAW,
  },
  silver: {
    icon:'🥈', label:'Silver', subtitle:'Cleansed & Validated Layer',
    color:{ bg:'rgba(100,116,139,0.10)', border:'#64748b', text:'#cbd5e1' },
    notebook:'02_silver_transform', storage:'weather_silver.silver_weather_clean',
    strategy:'Delta MERGE (upsert) theo (city, crawled_at)',
    description:'Đọc Bronze, cast toàn bộ kiểu dữ liệu tường minh (STRING→DOUBLE/INT/TIMESTAMP), lọc NULL ở các cột quan trọng, tách thêm date/hour từ crawled_at, rồi dùng Delta MERGE để upsert — đảm bảo không trùng dữ liệu dù pipeline chạy lại nhiều lần.',
    bullets:[
      {ok:true,  text:'✓ Cast tất cả 27 fields sang đúng kiểu (Double/Int/Timestamp)'},
      {ok:true,  text:'✓ Filter: city IS NOT NULL AND temperature_c IS NOT NULL'},
      {ok:true,  text:'✓ Thêm cột date, hour tách từ crawled_at'},
      {ok:true,  text:'✓ Delta MERGE dedup theo (city, crawled_at)'},
      {ok:true,  text:'✓ Gắn cờ is_valid: temp ∈ [−60,60] và humidity ∈ [0,100]'},
    ],
    cols:[
      {k:'city',w:130},{k:'country',w:60},
      {k:'latitude',w:75},{k:'longitude',w:80},{k:'timezone',w:130},
      {k:'temperature_c',w:90},{k:'feels_like_c',w:85},
      {k:'temp_max_c',w:80},{k:'temp_min_c',w:80},
      {k:'humidity',w:75},{k:'pressure_hpa',w:95},
      {k:'cloud_cover_pct',w:90},{k:'visibility_m',w:90},
      {k:'precipitation_mm',w:105},{k:'rain_mm',w:75},
      {k:'precip_sum_mm',w:100},{k:'wind_speed_kmh',w:95},
      {k:'wind_direction_deg',w:115},{k:'wind_gusts_kmh',w:100},
      {k:'wind_max_kmh',w:90},{k:'weather_code',w:95},
      {k:'weather_desc',w:120},{k:'uv_index',w:68},{k:'uv_index_max',w:90},
      {k:'sunrise',w:130},{k:'sunset',w:130},
      {k:'crawled_at',w:145},
      {k:'date',w:95},{k:'hour',w:55},{k:'crawl_hour',w:145},
      {k:'is_valid',w:68},{k:'processed_at',w:145},
    ],
    rows: SILVER,
  },
}

// ═══════════════════════════════════════════════════════════════════════════════
// Cell formatting & color
// ═══════════════════════════════════════════════════════════════════════════════
function cellColor(k, v) {
  if (k === 'is_valid') return v ? '#3dd68c' : '#f05252'
  if (['temperature_c','avg_temp_c','overall_avg_temp'].includes(k)) {
    if (v >= 35) return '#f05252'
    if (v >= 28) return '#f5a623'
    if (v >= 18) return '#3dd68c'
    return '#7bc8f6'
  }
  if (k === 'weather_severity') return ['#3dd68c','#f5a623','#f05252','#b91c1c','#7f1d1d'][v] ?? 'var(--text2)'
  if (k === 'comfort_score') {
    const n = parseFloat(v); if(n>=70) return '#3dd68c'; if(n>=40) return '#f5a623'; return '#f05252'
  }
  if (k === 'heat_index' && v !== null) {
    if (v >= 40) return '#f05252'; if (v >= 32) return '#f5a623'; return 'var(--text2)'
  }
  return 'var(--text2)'
}

function fmtCell(k, v) {
  if (v === null || v === undefined)
    return <span style={{ color:'var(--text3)', fontStyle:'italic' }}>null</span>
  if (k === 'is_valid')
    return <span style={{ color: v ? '#3dd68c' : '#f05252', fontWeight:700 }}>{v ? '✓ true' : '✗ false'}</span>
  if (k === 'weather_severity') {
    const labels = ['0 Normal','1 Light','2 Moderate','3 Severe','4 Extreme']
    return <span>{labels[v] ?? v}</span>
  }
  return String(v)
}

// ═══════════════════════════════════════════════════════════════════════════════
// SampleTable
// ═══════════════════════════════════════════════════════════════════════════════
function SampleTable({ cols, rows, borderColor }) {
  return (
    <div style={{ overflowX:'auto', borderRadius:'var(--radius)', border:`1px solid ${borderColor}44` }}>
      <table style={{ borderCollapse:'collapse', fontSize:11, fontFamily:'var(--mono)', minWidth:'100%' }}>
        <thead>
          <tr style={{ background:`${borderColor}18` }}>
            {cols.map(c => (
              <th key={c.k} style={{
                padding:'7px 10px', textAlign:'left', whiteSpace:'nowrap',
                color:'var(--text3)', fontSize:10, fontWeight:700, letterSpacing:0.8,
                borderBottom:`1px solid ${borderColor}55`, minWidth:c.w,
              }}>{c.k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} style={{ background: i%2===0?'transparent':'rgba(255,255,255,0.02)', borderBottom:'1px solid var(--border)' }}>
              {cols.map(c => (
                <td key={c.k} style={{
                  padding:'5px 10px', whiteSpace:'nowrap',
                  color: cellColor(c.k, row[c.k]),
                  fontWeight: ['city','country'].includes(c.k) ? 600 : 400,
                }}>
                  {fmtCell(c.k, row[c.k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Bronze / Silver card (tab: data | schema)
// ═══════════════════════════════════════════════════════════════════════════════
function BronzeSilverCard({ id }) {
  const [tab, setTab] = useState('data')
  const m = LAYERS[id]
  return (
    <div style={{ marginBottom:32 }}>
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:12, paddingBottom:10, borderBottom:'1px solid var(--border)' }}>
        <span style={{ fontSize:26 }}>{m.icon}</span>
        <div>
          <div style={{ fontFamily:'var(--mono)', fontSize:14, fontWeight:700, color:m.color.text }}>{m.label} Layer</div>
          <div style={{ fontSize:11, color:'var(--text2)' }}>{m.subtitle}</div>
        </div>
        <div style={{ marginLeft:'auto', display:'flex', gap:8, flexWrap:'wrap', justifyContent:'flex-end' }}>
          <Badge color="gray">📓 {m.notebook}</Badge>
          <Badge color="gray">🗄 {m.storage}</Badge>
          <Badge color="gray">⚡ {m.strategy}</Badge>
        </div>
      </div>
      <p style={{ fontSize:12, color:'var(--text2)', lineHeight:1.75, marginBottom:12, marginTop:0 }}>{m.description}</p>
      <div style={{ display:'flex', flexWrap:'wrap', gap:6, marginBottom:14 }}>
        {m.bullets.map((b,i) => (
          <div key={i} style={{
            padding:'4px 10px', borderRadius:'var(--radius)', fontSize:11, fontFamily:'var(--mono)',
            background: b.ok ? 'rgba(61,214,140,0.07)' : 'rgba(240,82,82,0.07)',
            border:`1px solid ${b.ok ? 'rgba(61,214,140,0.25)' : 'rgba(240,82,82,0.25)'}`,
            color: b.ok ? '#3dd68c' : '#f05252',
          }}>{b.text}</div>
        ))}
      </div>
      {/* Tab switcher */}
      <div style={{ display:'flex', gap:4, marginBottom:12 }}>
        {[{id:'data',label:`📊 Sample Data (10 rows · ${m.cols.length} fields)`},{id:'schema',label:`📋 Schema`}].map(t => (
          <button key={t.id} onClick={()=>setTab(t.id)} style={{
            padding:'5px 14px', borderRadius:'var(--radius)', cursor:'pointer', transition:'all 0.15s',
            border: tab===t.id ? `1px solid ${m.color.border}` : '1px solid var(--border)',
            background: tab===t.id ? m.color.bg : 'transparent',
            color: tab===t.id ? m.color.text : 'var(--text3)',
            fontFamily:'var(--mono)', fontSize:11, fontWeight: tab===t.id ? 700 : 400,
          }}>{t.label}</button>
        ))}
      </div>
      <Card style={{ padding:0 }}>
        <div style={{ padding:'7px 14px', borderBottom:`1px solid ${m.color.border}33`, fontSize:10, fontFamily:'var(--mono)', color:'var(--text3)', display:'flex', gap:8 }}>
          <span style={{ color:m.color.text, fontWeight:700 }}>{m.icon} {m.label}</span>
          <span>—</span>
          {tab==='data'
            ? <span>10 bản ghi thực · crawler 2026-04-22T07:59 · <span style={{color:m.color.text}}>{m.cols.length} fields</span></span>
            : <span>Tất cả columns và kiểu dữ liệu</span>}
        </div>
        <div style={{ padding:12 }}>
          {tab==='data'
            ? <SampleTable cols={m.cols} rows={m.rows} borderColor={m.color.border} />
            : (
              <table style={{ width:'100%', borderCollapse:'collapse', fontSize:11, fontFamily:'var(--mono)' }}>
                <thead><tr>{['Column','Width','Note'].map(h=>(
                  <th key={h} style={{ padding:'6px 10px', textAlign:'left', color:'var(--text3)', fontSize:10, fontWeight:700, letterSpacing:1, textTransform:'uppercase', borderBottom:'1px solid var(--border)' }}>{h}</th>
                ))}</tr></thead>
                <tbody>{m.cols.map(c=>(
                  <tr key={c.k} style={{ borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding:'5px 10px', color:'var(--accent)', fontWeight:600 }}>{c.k}</td>
                    <td style={{ padding:'5px 10px', color:'#3dd68c' }}>{c.w}px</td>
                    <td style={{ padding:'5px 10px', color:'var(--text3)' }}>—</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
        </div>
      </Card>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Gold card — 4 sub-tables
// ═══════════════════════════════════════════════════════════════════════════════
const GOLD_COLOR = { bg:'rgba(234,179,8,0.10)', border:'#ca8a04', text:'#fde047' }

const GOLD_TABLE_ICONS = { daily:'📅', latest:'📍', ml:'🧪', stats:'📊' }
const GOLD_TABLE_LABELS = {
  daily:  'Lịch sử tích lũy theo ngày',
  latest: 'Snapshot mới nhất mỗi city',
  ml:     'Features sẵn sàng cho ML',
  stats:  'Thống kê tổng hợp toàn lịch sử',
}

function GoldCard() {
  const [activeTable, setActiveTable] = useState('daily')
  const [tab, setTab] = useState('data')
  const tbl = GOLD_TABLES.find(t => t.id === activeTable)

  return (
    <div style={{ marginBottom:32 }}>
      {/* Header */}
      <div style={{ display:'flex', alignItems:'center', gap:12, marginBottom:12, paddingBottom:10, borderBottom:'1px solid var(--border)' }}>
        <span style={{ fontSize:26 }}>🥇</span>
        <div>
          <div style={{ fontFamily:'var(--mono)', fontSize:14, fontWeight:700, color:GOLD_COLOR.text }}>Gold Layer</div>
          <div style={{ fontSize:11, color:'var(--text2)' }}>Aggregated Business Layer — 4 tables</div>
        </div>
        <div style={{ marginLeft:'auto', display:'flex', gap:8, flexWrap:'wrap', justifyContent:'flex-end' }}>
          <Badge color="gray">📓 03_gold_aggregate</Badge>
          <Badge color="gray">🗄 weather_gold.*</Badge>
        </div>
      </div>

      <p style={{ fontSize:12, color:'var(--text2)', lineHeight:1.75, marginBottom:12, marginTop:0 }}>
        Silver được aggregate theo ngày + thành phố, tính toán các chỉ số phân tích và ML-ready features.
        Tạo ra <strong style={{color:GOLD_COLOR.text}}>4 bảng riêng biệt</strong> phục vụ các mục đích khác nhau.
      </p>

      {/* 4 table selector */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:8, marginBottom:14 }}>
        {GOLD_TABLES.map(t => (
          <button key={t.id} onClick={()=>{ setActiveTable(t.id); setTab('data') }} style={{
            padding:'10px 12px', borderRadius:'var(--radius)', cursor:'pointer', textAlign:'left', transition:'all 0.15s',
            border: activeTable===t.id ? `1px solid ${GOLD_COLOR.border}` : '1px solid var(--border)',
            background: activeTable===t.id ? GOLD_COLOR.bg : 'var(--bg2)',
          }}>
            <div style={{ fontSize:16, marginBottom:4 }}>{GOLD_TABLE_ICONS[t.id]}</div>
            <div style={{ fontFamily:'var(--mono)', fontSize:10, fontWeight:700, color: activeTable===t.id ? GOLD_COLOR.text : 'var(--text2)', letterSpacing:0.5 }}>{t.label}</div>
            <div style={{ fontSize:10, color:'var(--text3)', marginTop:2 }}>{GOLD_TABLE_LABELS[t.id]}</div>
          </button>
        ))}
      </div>

      {/* Active table description */}
      <div style={{
        padding:'8px 14px', marginBottom:12, borderRadius:'var(--radius)',
        background:GOLD_COLOR.bg, border:`1px solid ${GOLD_COLOR.border}44`,
        fontSize:11, fontFamily:'var(--mono)', color:'var(--text2)', lineHeight:1.65,
      }}>
        <span style={{ color:GOLD_COLOR.text, fontWeight:700 }}>{GOLD_TABLE_ICONS[tbl.id]} {tbl.label}</span>
        {' — '}{tbl.desc}
      </div>

      {/* Tab switcher */}
      <div style={{ display:'flex', gap:4, marginBottom:12 }}>
        {[{id:'data',label:`📊 Sample Data (10 rows · ${tbl.cols.length} fields)`},{id:'schema',label:`📋 Columns`}].map(t => (
          <button key={t.id} onClick={()=>setTab(t.id)} style={{
            padding:'5px 14px', borderRadius:'var(--radius)', cursor:'pointer', transition:'all 0.15s',
            border: tab===t.id ? `1px solid ${GOLD_COLOR.border}` : '1px solid var(--border)',
            background: tab===t.id ? GOLD_COLOR.bg : 'transparent',
            color: tab===t.id ? GOLD_COLOR.text : 'var(--text3)',
            fontFamily:'var(--mono)', fontSize:11, fontWeight: tab===t.id ? 700 : 400,
          }}>{t.label}</button>
        ))}
      </div>

      <Card style={{ padding:0 }}>
        <div style={{ padding:'7px 14px', borderBottom:`1px solid ${GOLD_COLOR.border}33`, fontSize:10, fontFamily:'var(--mono)', color:'var(--text3)', display:'flex', gap:8, alignItems:'center' }}>
          <span style={{ color:GOLD_COLOR.text, fontWeight:700 }}>🥇 {tbl.label}</span>
          <span>—</span>
          <span>10 bản ghi mẫu · <span style={{color:GOLD_COLOR.text}}>{tbl.cols.length} fields</span></span>
        </div>
        <div style={{ padding:12 }}>
          {tab==='data'
            ? <SampleTable cols={tbl.cols} rows={tbl.rows} borderColor={GOLD_COLOR.border} />
            : (
              <table style={{ width:'100%', borderCollapse:'collapse', fontSize:11, fontFamily:'var(--mono)' }}>
                <thead><tr>{['Column','Note'].map(h=>(
                  <th key={h} style={{ padding:'6px 10px', textAlign:'left', color:'var(--text3)', fontSize:10, fontWeight:700, letterSpacing:1, textTransform:'uppercase', borderBottom:'1px solid var(--border)' }}>{h}</th>
                ))}</tr></thead>
                <tbody>{tbl.cols.map(c=>(
                  <tr key={c.k} style={{ borderBottom:'1px solid rgba(255,255,255,0.04)' }}>
                    <td style={{ padding:'5px 10px', color:'var(--accent)', fontWeight:600 }}>{c.k}</td>
                    <td style={{ padding:'5px 10px', color:'var(--text3)' }}>—</td>
                  </tr>
                ))}</tbody>
              </table>
            )}
        </div>
      </Card>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main export
// ═══════════════════════════════════════════════════════════════════════════════
export default function DataLayersTab() {
  return (
    <div>
      {/* Architecture bar */}
      <div style={{ background:'var(--bg1)', border:'1px solid var(--border)', borderRadius:'var(--radius-lg)', padding:'14px 20px', marginBottom:28 }}>
        <div style={{ fontSize:10, fontFamily:'var(--mono)', color:'var(--text3)', textTransform:'uppercase', letterSpacing:2, marginBottom:10 }}>
          Medallion Architecture — Data Flow
        </div>
        <div style={{ display:'flex', alignItems:'center', gap:8, flexWrap:'wrap' }}>
          {[
            { icon:'🟤', label:'Bronze', sub:'27 fields raw', color:{ bg:'rgba(180,83,9,0.10)', border:'#b45309', text:'#fbbf24' } },
            { icon:'🥈', label:'Silver', sub:'27 fields clean', color:{ bg:'rgba(100,116,139,0.10)', border:'#64748b', text:'#cbd5e1' } },
            { icon:'🥇', label:'Gold',   sub:'4 tables', color:{ bg:'rgba(234,179,8,0.10)', border:'#ca8a04', text:'#fde047' } },
          ].map((m, i) => (
            <div key={m.label} style={{ display:'flex', alignItems:'center', gap:8 }}>
              <div style={{ display:'flex', alignItems:'center', gap:8, padding:'10px 16px', borderRadius:'var(--radius)', background:m.color.bg, border:`1px solid ${m.color.border}` }}>
                <span style={{ fontSize:20 }}>{m.icon}</span>
                <div>
                  <div style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:12, color:m.color.text, letterSpacing:1 }}>{m.label}</div>
                  <div style={{ fontSize:10, color:'var(--text3)' }}>{m.sub}</div>
                </div>
              </div>
              {i < 2 && (
                <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:1 }}>
                  <span style={{ color:'var(--border2)', fontSize:20 }}>→</span>
                  <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>transform</span>
                </div>
              )}
            </div>
          ))}
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:1 }}>
              <span style={{ color:'var(--border2)', fontSize:20 }}>→</span>
              <span style={{ fontSize:9, color:'var(--text3)', fontFamily:'var(--mono)' }}>train</span>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:8, padding:'10px 16px', borderRadius:'var(--radius)', background:'rgba(168,85,247,0.10)', border:'1px solid #7c3aed' }}>
              <span style={{ fontSize:20 }}>🤖</span>
              <div>
                <div style={{ fontFamily:'var(--mono)', fontWeight:700, fontSize:12, color:'#c084fc', letterSpacing:1 }}>ML</div>
                <div style={{ fontSize:10, color:'var(--text3)' }}>Forecast Model</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <BronzeSilverCard id="bronze" />
      <BronzeSilverCard id="silver" />
      <GoldCard />
    </div>
  )
}