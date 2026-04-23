# 🌤️ Weather Pipeline

Thu thập dữ liệu thời tiết các thành phố lớn → xử lý trên Databricks Delta Lake → train ML model → hiển thị trên Streamlit.

> ✅ Chỉ dùng **Databricks Community Edition** (miễn phí) — không cần Docker, không cần Airflow.

---

## Kiến trúc

```
OpenWeatherMap API
       │
       ▼
Python Crawler (local)
       │ databricks fs cp
       ▼
DBFS: dbfs:/FileStore/weather/raw/
       │
       ▼  Databricks Notebooks
  [Bronze] ──► [Silver] ──► [Gold]
                                │
                    ┌───────────┴──────────┐
                    ▼                      ▼
             ML + MLflow              Power BI
                    │
       Databricks Workflows (schedule tự động)
                    │
             Streamlit UI (trigger + monitor)
```

---

## Cấu trúc thư mục

```
weather-pipeline/
├── crawler/
│   ├── weather_crawler.py       # Crawl từ OpenWeatherMap
│   └── requirements.txt
├── notebooks/                   # Upload lên Databricks Workspace
│   ├── 00_setup_workflow.py     # Tạo Workflow + schedule (chạy 1 lần)
│   ├── 01_bronze_ingest.py
│   ├── 02_silver_transform.py
│   ├── 03_gold_aggregate.py
│   └── 04_ml_train.py
├── streamlit_app/
│   └── app.py                   # UI điều khiển pipeline
├── .streamlit/
│   └── secrets.toml.example
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Hướng dẫn cài đặt & chạy

### Bước 1 — Chuẩn bị tài khoản

| Service | Link | Ghi chú |
|---|---|---|
| Databricks Community Edition | https://community.cloud.databricks.com | Miễn phí |
| Open-Meteo | https://open-meteo.com | **Miễn phí, không cần đăng ký, không cần API key** |

---

### Bước 2 — Cài đặt local

```bash
python -m pip install --upgrade pip setuptools wheel
pip install numpy
pip install -r requirements.txt
pip install databricks-cli
```

---

### Bước 3 — Cấu hình biến môi trường

```bash
cp .env.example .env
# Mở .env và điền:
#   OWM_API_KEY   → lấy tại openweathermap.org/api_keys
#   DATABRICKS_HOST  → https://community.cloud.databricks.com
#   DATABRICKS_TOKEN → xem hướng dẫn bên dưới
```

**Lấy Databricks Token:**
1. Đăng nhập Databricks → click avatar → **Settings**
2. Tab **Developer** → **Access tokens** → **Generate new token**
3. Copy token dán vào `.env`

---

### Bước 4 — Kết nối Databricks CLI

```bash
databricks configure --token
# Host:  https://community.cloud.databricks.com
# Token: (paste token)

# Kiểm tra
databricks fs ls dbfs:/
```

---

### Bước 5 — Upload notebooks lên Databricks Workspace

```bash
databricks workspace mkdirs /Shared/weather-pipeline

databricks workspace import /Shared/weather-pipeline/00_setup_workflow --file notebooks/00_setup_workflow.py --language PYTHON --overwrite
databricks workspace import /Shared/weather-pipeline/01_bronze_ingest --file notebooks/01_bronze_ingest.py --language PYTHON --overwrite
databricks workspace import /Shared/weather-pipeline/02_silver_transform --file notebooks/02_silver_transform.py --language PYTHON --overwrite
databricks workspace import /Shared/weather-pipeline/03_gold_aggregate --file notebooks/03_gold_aggregate.py --language PYTHON --overwrite
databricks workspace import /Shared/weather-pipeline/04_ml_train --file notebooks/04_ml_train.py --language PYTHON --overwrite
```

---

### Bước 6 — Crawl dữ liệu lần đầu

```bash
# Không cần API key — chạy thẳng luôn
python crawler/weather_crawler.py
# → Lưu vào raw_data/weather_YYYYMMDD_HHMMSS.json
```

---

### Bước 7 — Upload raw data thủ công bằng Databricks UI


### Bước 8 — Setup Workflow tự động (chạy 1 lần)

1. Đăng nhập **Databricks UI** → **Workspace** → `/Shared/weather-pipeline/`
2. Mở notebook **`00_setup_workflow`**
3. Nhấn **Run All** ▶

Notebook này sẽ:
- Tạo **Databricks Workflow** với 4 tasks (bronze → silver → gold → ml)
- Đặt **schedule mỗi 6 giờ** (0:00, 6:00, 12:00, 18:00 giờ Việt Nam)
- Trigger chạy ngay lần đầu

> Xem kết quả tại **Databricks → Workflows → weather-pipeline**

---

### Bước 9 — Khởi động Streamlit UI

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Điền DATABRICKS_HOST và DATABRICKS_TOKEN vào secrets.toml
# (Open-Meteo không cần key)

streamlit run streamlit_app/app.py
# → Mở http://localhost:8501
```

**Streamlit có 3 tab:**
- **Pipeline**: Trigger toàn bộ pipeline hoặc chạy từng notebook
- **Workflows**: Xem lịch sử runs, trạng thái từng bước
- **Live Weather**: Preview dữ liệu thời tiết realtime

---

### Bước 10 — Kết nối Power BI (tùy chọn)

1. **Power BI Desktop** → **Get Data** → **Databricks**
2. **Server hostname** + **HTTP Path**: lấy từ Databricks → Compute → cluster → **Advanced Options** → **JDBC/ODBC**
3. **Authentication**: Token → paste Databricks token
4. Chọn table: `hive_metastore → default → weather_daily`

---

## Lưu ý Free Edition

| Giới hạn | Giải pháp |
|---|---|
| Cluster tự tắt sau 2h idle | Restart cluster trước khi chạy notebook |
| Chỉ 1 cluster | Workflow chạy tasks tuần tự (đã cấu hình sẵn) |
| Không có Databricks SQL Warehouse | Query qua cluster thường, hoặc export CSV cho Power BI |
| DBFS có thể reset | Giữ backup `raw_data/` trên máy local |

---

## Troubleshooting

**Upload notebook bị lỗi encoding:**
```bash
# Thêm flag --overwrite và kiểm tra encoding UTF-8
databricks workspace import notebooks/01_bronze_ingest.py /Shared/weather-pipeline/01_bronze_ingest --language PYTHON --overwrite --format SOURCE
```

**Workflow báo lỗi "cluster not found":**
- Vào Databricks → Compute → Start cluster
- Chạy lại `00_setup_workflow` để update cluster ID mới

**Crawler không lấy được dữ liệu:**
- Kiểm tra kết nối mạng: `curl https://api.open-meteo.com/v1/forecast?latitude=10.82&longitude=106.63&current=temperature_2m`
- Open-Meteo không cần key, lỗi thường là do mạng hoặc timeout

**Delta table không tìm thấy:**
```python
# Chạy lệnh này trong notebook Databricks để kiểm tra
display(dbutils.fs.ls("dbfs:/delta/"))
```
