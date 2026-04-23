# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Gold Layer: Aggregate + ML-ready Features
# MAGIC
# MAGIC **Thay đổi:**
# MAGIC - Giữ nguyên 2 aggregate cũ (daily summary + latest snapshot)
# MAGIC - Thêm bảng `gold_ml_features`: feature-engineered, sẵn sàng cho 04_ml_train
# MAGIC - Thêm bảng `gold_city_stats`: thống kê lịch sử theo thành phố (cho dashboard)
# MAGIC - Export thêm CSV cho Streamlit: gold_ml_features.csv, gold_city_stats.csv

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
import pandas as pd
import numpy as np

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

SILVER_TABLE       = f"{CATALOG}.{SCHEMA}.silver_weather_clean"
GOLD_DAILY_TABLE   = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
GOLD_LATEST_TABLE  = f"{CATALOG}.{SCHEMA}.gold_weather_latest"
GOLD_ML_TABLE      = f"{CATALOG}.{SCHEMA}.gold_ml_features"      # ← mới
GOLD_STATS_TABLE   = f"{CATALOG}.{SCHEMA}.gold_city_stats"       # ← mới

NOTEBOOK_DIR   = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR   = "/".join(NOTEBOOK_DIR.split("/")[:-1])
EXPORT_WS_PATH = f"/Workspace{NOTEBOOK_DIR}/exports"
EXPORT_FS_PATH = f"file:{EXPORT_WS_PATH}"

# COMMAND ----------

df = spark.table(SILVER_TABLE)
print(f"Silver rows: {df.count()}")
df.printSchema()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Aggregate 1: Daily summary per city (dùng cho biểu đồ xu hướng)

# COMMAND ----------

daily = (
    df.groupBy("city", "country", "date")
    .agg(
        F.round(F.avg("temperature_c"),    2).alias("avg_temp_c"),
        F.round(F.max("temperature_c"),    2).alias("max_temp_c"),
        F.round(F.min("temperature_c"),    2).alias("min_temp_c"),
        F.round(F.avg("feels_like_c"),     2).alias("avg_feels_like_c"),
        F.round(F.avg("humidity"),         1).alias("avg_humidity"),
        F.round(F.avg("pressure_hpa"),     1).alias("avg_pressure_hpa"),
        F.round(F.avg("wind_speed_kmh"),   2).alias("avg_wind_speed_kmh"),
        F.round(F.max("wind_speed_kmh"),   2).alias("max_wind_speed_kmh"),
        F.round(F.avg("cloud_cover_pct"),  1).alias("avg_cloud_pct"),
        F.round(F.avg("precipitation_mm"), 2).alias("avg_precipitation_mm"),
        F.round(F.avg("uv_index"),         1).alias("avg_uv_index"),
        F.count("*").alias("sample_count"),
    )
    .orderBy("date", "city")
)

daily.show(10)
(
    daily.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true").saveAsTable(GOLD_DAILY_TABLE)
)
print(f"✓ Gold daily: {GOLD_DAILY_TABLE}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Aggregate 2: Latest snapshot per city (realtime dashboard)

# COMMAND ----------

w_latest = Window.partitionBy("city").orderBy(F.desc("crawled_at"))
latest = (
    df.withColumn("rn", F.row_number().over(w_latest))
    .filter(F.col("rn") == 1).drop("rn")
)

(
    latest.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true").saveAsTable(GOLD_LATEST_TABLE)
)
print(f"✓ Gold latest: {GOLD_LATEST_TABLE}")
latest.select("city", "country", "temperature_c", "humidity", "weather_desc", "crawled_at").show(truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Aggregate 3: ML Features — Feature Engineering cho 04_ml_train
# MAGIC
# MAGIC Tạo sẵn các đặc trưng:
# MAGIC - **Temporal**: month_sin/cos, doy_sin/cos, is_weekend
# MAGIC - **Lag features**: nhiệt độ/độ ẩm của 1-3-7 ngày trước (per city)
# MAGIC - **Rolling stats**: trung bình & std nhiệt độ 3/7 ngày
# MAGIC - **Derived**: heat_index, temp_range, comfort_score

# COMMAND ----------

# Dùng pandas để tính lag/rolling (Spark window + NaN phức tạp hơn)
pdf = spark.table(GOLD_DAILY_TABLE).toPandas()

if len(pdf) > 0:
    pdf["date"] = pd.to_datetime(pdf["date"])
    pdf = pdf.sort_values(["city", "date"]).reset_index(drop=True)

    # ── Temporal features ───────────────────────────────────────────────
    pdf["month"]        = pdf["date"].dt.month
    pdf["day_of_year"]  = pdf["date"].dt.dayofyear
    pdf["day_of_week"]  = pdf["date"].dt.dayofweek
    pdf["week_of_year"] = pdf["date"].dt.isocalendar().week.astype(int)
    pdf["quarter"]      = pdf["date"].dt.quarter
    pdf["is_weekend"]   = (pdf["day_of_week"] >= 5).astype(int)

    # Seasonal encoding (sin/cos)
    pdf["month_sin"]    = np.sin(2 * np.pi * pdf["month"] / 12)
    pdf["month_cos"]    = np.cos(2 * np.pi * pdf["month"] / 12)
    pdf["doy_sin"]      = np.sin(2 * np.pi * pdf["day_of_year"] / 365)
    pdf["doy_cos"]      = np.cos(2 * np.pi * pdf["day_of_year"] / 365)

    # ── Lag features (per city) ──────────────────────────────────────────
    for lag in [1, 2, 3, 7]:
        pdf[f"temp_lag{lag}"]     = pdf.groupby("city")["avg_temp_c"].shift(lag)
        pdf[f"humidity_lag{lag}"] = pdf.groupby("city")["avg_humidity"].shift(lag)

    # ── Rolling statistics ───────────────────────────────────────────────
    for w in [3, 7]:
        pdf[f"temp_roll_mean_{w}d"] = (
            pdf.groupby("city")["avg_temp_c"]
               .transform(lambda x: x.shift(1).rolling(w, min_periods=1).mean())
        )
        pdf[f"temp_roll_std_{w}d"] = (
            pdf.groupby("city")["avg_temp_c"]
               .transform(lambda x: x.shift(1).rolling(w, min_periods=1).std().fillna(0))
        )
        pdf[f"precip_roll_sum_{w}d"] = (
            pdf.groupby("city")["avg_precipitation_mm"]
               .transform(lambda x: x.shift(1).rolling(w, min_periods=1).sum())
        )

    # ── Derived features ─────────────────────────────────────────────────
    # Dải nhiệt độ trong ngày
    pdf["temp_range"] = pdf["max_temp_c"] - pdf["min_temp_c"]

    # Heat index (Steadman simplified — chỉ đúng khi T > 27°C)
    T = pdf["avg_temp_c"]
    R = pdf["avg_humidity"]
    pdf["heat_index"] = (
        -8.78469475556
        + 1.61139411 * T
        + 2.33854883889 * R
        - 0.14611605 * T * R
        - 0.012308094 * T**2
        - 0.016424828 * R**2
        + 0.002211732 * T**2 * R
        + 0.00072546 * T * R**2
        - 0.000003582 * T**2 * R**2
    ).round(1)

    # Comfort score: 0-100 (cao = dễ chịu hơn)
    # Dựa trên: nhiệt độ lý tưởng 22°C, độ ẩm 50%, gió 10 km/h
    temp_score   = np.clip(100 - 4 * abs(pdf["avg_temp_c"] - 22), 0, 100)
    humid_score  = np.clip(100 - 2 * abs(pdf["avg_humidity"] - 50), 0, 100)
    wind_score   = np.clip(100 - 3 * abs(pdf["avg_wind_speed_kmh"] - 10), 0, 100)
    pdf["comfort_score"] = ((temp_score + humid_score + wind_score) / 3).round(1)

    # Weather severity (0=calm .. 4=severe) — dùng cho UI badge
    pdf["weather_severity"] = 0
    pdf.loc[pdf["avg_precipitation_mm"] > 5,  "weather_severity"] = 1
    pdf.loc[pdf["avg_precipitation_mm"] > 15, "weather_severity"] = 2
    pdf.loc[pdf["avg_wind_speed_kmh"]   > 50, "weather_severity"] = 3
    pdf.loc[
        (pdf["avg_precipitation_mm"] > 20) & (pdf["avg_wind_speed_kmh"] > 60),
        "weather_severity"
    ] = 4

    # TARGET cho ML: nhiệt độ ngày hôm sau (shift -1)
    pdf["target_next_temp"] = pdf.groupby("city")["avg_temp_c"].shift(-1)

    print(f"✓ ML features shape: {pdf.shape}")
    print(f"   Rows có target   : {pdf['target_next_temp'].notna().sum()}")

    df_ml = spark.createDataFrame(pdf)
    (
        df_ml.write.format("delta").mode("overwrite")
        .option("overwriteSchema", "true").saveAsTable(GOLD_ML_TABLE)
    )
    print(f"✓ Gold ML features: {GOLD_ML_TABLE}")
else:
    print("⚠️  Gold daily trống — chưa có đủ data để tạo ML features")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Aggregate 4: City Statistics — cho trang Dashboard Streamlit

# COMMAND ----------

stats_pdf = (
    spark.table(GOLD_DAILY_TABLE).toPandas()
    if len(spark.table(GOLD_DAILY_TABLE).take(1)) > 0
    else pd.DataFrame()
)

if len(stats_pdf) > 0:
    city_stats = (
        stats_pdf.groupby(["city", "country"]).agg(
            days_tracked       = ("date",                "count"),
            overall_avg_temp   = ("avg_temp_c",          "mean"),
            overall_max_temp   = ("max_temp_c",          "max"),
            overall_min_temp   = ("min_temp_c",          "min"),
            temp_std           = ("avg_temp_c",          "std"),
            avg_humidity       = ("avg_humidity",        "mean"),
            avg_wind_speed     = ("avg_wind_speed_kmh",  "mean"),
            avg_precipitation  = ("avg_precipitation_mm","mean"),
            avg_uv_index       = ("avg_uv_index",        "mean"),
            avg_cloud_pct      = ("avg_cloud_pct",       "mean"),
            total_precipitation= ("avg_precipitation_mm","sum"),
            first_recorded     = ("date",                "min"),
            last_recorded      = ("date",                "max"),
        )
        .reset_index()
    )

    # Làm tròn
    num_cols = [c for c in city_stats.columns if city_stats[c].dtype in [float, "float64"]]
    city_stats[num_cols] = city_stats[num_cols].round(2)

    df_stats = spark.createDataFrame(city_stats)
    (
        df_stats.write.format("delta").mode("overwrite")
        .option("overwriteSchema", "true").saveAsTable(GOLD_STATS_TABLE)
    )
    print(f"✓ Gold city stats: {GOLD_STATS_TABLE}")
    print(city_stats[["city", "days_tracked", "overall_avg_temp", "overall_max_temp", "overall_min_temp"]].to_string(index=False))
else:
    print("⚠️  Không có data để tính city stats")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Export CSV cho Streamlit

# COMMAND ----------

dbutils.fs.mkdirs(EXPORT_FS_PATH)

def export_csv(table_name: str, filename: str):
    rows = spark.table(table_name).take(1)
    if not rows:
        print(f"⏭  {filename} — bảng trống, bỏ qua")
        return
    csv_content = spark.table(table_name).toPandas().to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/{filename}", csv_content, overwrite=True)
    print(f"✓ Exported: {filename}")

export_csv(GOLD_DAILY_TABLE,  "gold_weather_daily.csv")
export_csv(GOLD_LATEST_TABLE, "gold_weather_latest.csv")
export_csv(GOLD_ML_TABLE,     "gold_ml_features.csv")      # ← mới
export_csv(GOLD_STATS_TABLE,  "gold_city_stats.csv")       # ← mới

print(f"\n✓ Tất cả CSV tại: {EXPORT_WS_PATH}")
print("→ Download: python scripts/download_exports.py")