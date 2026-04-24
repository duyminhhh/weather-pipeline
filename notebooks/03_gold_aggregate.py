# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Gold Layer: Aggregate + ML-ready Features
# MAGIC
# MAGIC **Chiến lược lưu trữ:**
# MAGIC - `gold_weather_daily`  → TÍCH LŨY (append + dedup): mỗi lần crawl thêm 1 ngày vào lịch sử
# MAGIC - `gold_weather_latest` → OVERWRITE: chỉ giữ snapshot mới nhất mỗi city
# MAGIC - `gold_ml_features`    → OVERWRITE: tính lại toàn bộ từ daily history (đã tích lũy đủ)
# MAGIC - `gold_city_stats`     → OVERWRITE: aggregate summary từ toàn bộ daily history
# MAGIC
# MAGIC **CSV export cho Streamlit:**
# MAGIC   gold_weather_latest.csv, gold_weather_daily.csv, gold_ml_features.csv, gold_city_stats.csv

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window
import pandas as pd
import numpy as np

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

SILVER_TABLE      = f"{CATALOG}.{SCHEMA}.silver_weather_clean"
GOLD_DAILY_TABLE  = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
GOLD_LATEST_TABLE = f"{CATALOG}.{SCHEMA}.gold_weather_latest"
GOLD_ML_TABLE     = f"{CATALOG}.{SCHEMA}.gold_ml_features"
GOLD_STATS_TABLE  = f"{CATALOG}.{SCHEMA}.gold_city_stats"

NOTEBOOK_DIR   = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR   = "/".join(NOTEBOOK_DIR.split("/")[:-1])
EXPORT_WS_PATH = f"/Workspace{NOTEBOOK_DIR}/exports"
EXPORT_FS_PATH = f"file:{EXPORT_WS_PATH}"

dbutils.fs.mkdirs(EXPORT_FS_PATH)

# COMMAND ----------

df_silver = spark.table(SILVER_TABLE)
silver_count = df_silver.count()
print(f"Silver rows: {silver_count}")
if silver_count == 0:
    raise ValueError("Silver table rỗng! Hãy chạy 01_bronze và 02_silver trước.")
df_silver.printSchema()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bước 1: Daily summary — TÍCH LŨY (append + dedup)
# MAGIC
# MAGIC Mỗi lần pipeline chạy (crawl mỗi 6 tiếng), aggregate silver → daily rồi
# MAGIC append vào bảng lịch sử. Dedup đảm bảo cùng city+date chỉ có 1 hàng
# MAGIC (giữ hàng có sample_count cao nhất = lần crawl đầy đủ nhất trong ngày).

# COMMAND ----------

daily_new = (
    df_silver
    .groupBy("city", "country", "date")
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

print(f"Daily rows mới từ silver: {daily_new.count()}")
daily_new.show(5)

# Append vào bảng lịch sử
(
    daily_new.write.format("delta").mode("append")
    .option("mergeSchema", "true")
    .saveAsTable(GOLD_DAILY_TABLE)
)

# Dedup: cùng (city, date) → giữ hàng sample_count cao nhất
dedup_daily = (
    spark.table(GOLD_DAILY_TABLE)
    .withColumn("_rn", F.row_number().over(
        Window.partitionBy("city", "date").orderBy(F.desc("sample_count"))
    ))
    .filter(F.col("_rn") == 1)
    .drop("_rn")
)
(
    dedup_daily.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(GOLD_DAILY_TABLE)
)

total_daily = spark.table(GOLD_DAILY_TABLE).count()
print(f"gold_weather_daily (tich luy): {total_daily} rows")

# Kiểm tra số ngày lịch sử mỗi city
days_per_city_spark = (
    spark.table(GOLD_DAILY_TABLE)
    .groupBy("city")
    .agg(F.countDistinct("date").alias("n_days"), F.min("date").alias("first"), F.max("date").alias("last"))
    .orderBy("n_days")
)
days_per_city_spark.show(truncate=False)
min_days = days_per_city_spark.agg(F.min("n_days")).collect()[0][0]
print(f"City it ngay nhat: {min_days} ngay")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bước 2: Latest snapshot — OVERWRITE
# MAGIC Snapshot mới nhất mỗi city, dùng cho Dashboard realtime.

# COMMAND ----------

w_latest = Window.partitionBy("city").orderBy(F.desc("crawled_at"))
df_latest = (
    df_silver
    .withColumn("_rn", F.row_number().over(w_latest))
    .filter(F.col("_rn") == 1)
    .drop("_rn")
)

(
    df_latest.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(GOLD_LATEST_TABLE)
)

print(f"gold_weather_latest: {df_latest.count()} cities")
df_latest.select("city", "country", "temperature_c", "humidity", "weather_desc", "crawled_at").show(truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bước 3: ML Features — OVERWRITE
# MAGIC
# MAGIC Tính lại toàn bộ từ gold_daily (đã tích lũy đủ lịch sử).
# MAGIC Features: temporal encoding, lag 1/2/3/7 ngày, rolling 3/7 ngày,
# MAGIC derived (heat_index, comfort_score, weather_severity), target_next_temp.
# MAGIC
# MAGIC NaN ở lag/rolling là bình thường ở những ngày đầu tiên —
# MAGIC 04_ml_train sẽ fillna(mean) trước khi train.

# COMMAND ----------

pdf = spark.table(GOLD_DAILY_TABLE).toPandas()
print(f"Daily rows de tinh ML features: {len(pdf)}")

if len(pdf) == 0:
    print("gold_weather_daily trong — bo qua buoc ML features.")
else:
    pdf["date"] = pd.to_datetime(pdf["date"])
    pdf = pdf.sort_values(["city", "date"]).reset_index(drop=True)

    days_report = pdf.groupby("city")["date"].nunique()
    print(f"So ngay lich su per city:\n{days_report.to_string()}")

    # ── Temporal features ────────────────────────────────────────────────────────
    pdf["month"]        = pdf["date"].dt.month
    pdf["day_of_year"]  = pdf["date"].dt.dayofyear
    pdf["day_of_week"]  = pdf["date"].dt.dayofweek
    pdf["week_of_year"] = pdf["date"].dt.isocalendar().week.astype(int)
    pdf["quarter"]      = pdf["date"].dt.quarter
    pdf["is_weekend"]   = (pdf["day_of_week"] >= 5).astype(int)
    # Sin/cos encoding — giữ tính tuần hoàn
    pdf["month_sin"]    = np.sin(2 * np.pi * pdf["month"] / 12)
    pdf["month_cos"]    = np.cos(2 * np.pi * pdf["month"] / 12)
    pdf["doy_sin"]      = np.sin(2 * np.pi * pdf["day_of_year"] / 365)
    pdf["doy_cos"]      = np.cos(2 * np.pi * pdf["day_of_year"] / 365)

    # ── Lag features (per city) ──────────────────────────────────────────────────
    # Lag 1/2/3/7 ngày — NaN ở đầu city là bình thường, fillna khi train
    for lag in [1, 2, 3, 7]:
        pdf[f"temp_lag{lag}"]     = pdf.groupby("city")["avg_temp_c"].shift(lag)
        pdf[f"humidity_lag{lag}"] = pdf.groupby("city")["avg_humidity"].shift(lag)

    # ── Rolling statistics (per city, lookback không bao gồm ngày hiện tại) ──────
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

    # ── Derived features ─────────────────────────────────────────────────────────
    pdf["temp_range"] = (pdf["max_temp_c"] - pdf["min_temp_c"]).round(2)

    # Heat index — Steadman simplified
    T = pdf["avg_temp_c"]
    R = pdf["avg_humidity"]
    pdf["heat_index"] = (
        -8.78469475556
        + 1.61139411    * T
        + 2.33854883889 * R
        - 0.14611605    * T * R
        - 0.012308094   * T**2
        - 0.016424828   * R**2
        + 0.002211732   * T**2 * R
        + 0.00072546    * T    * R**2
        - 0.000003582   * T**2 * R**2
    ).round(1)

    # Comfort score 0–100 (nhiệt độ lý tưởng 22°C, độ ẩm 50%, gió 10 km/h)
    temp_score  = np.clip(100 - 4 * abs(T - 22), 0, 100)
    humid_score = np.clip(100 - 2 * abs(R - 50), 0, 100)
    wind_score  = np.clip(100 - 3 * abs(pdf["avg_wind_speed_kmh"] - 10), 0, 100)
    pdf["comfort_score"] = ((temp_score + humid_score + wind_score) / 3).round(1)

    # Weather severity: 0 = calm → 4 = extreme
    pdf["weather_severity"] = 0
    pdf.loc[pdf["avg_precipitation_mm"] > 5,  "weather_severity"] = 1
    pdf.loc[pdf["avg_precipitation_mm"] > 15, "weather_severity"] = 2
    pdf.loc[pdf["avg_wind_speed_kmh"]   > 50, "weather_severity"] = 3
    pdf.loc[
        (pdf["avg_precipitation_mm"] > 20) & (pdf["avg_wind_speed_kmh"] > 60),
        "weather_severity"
    ] = 4

    # ── Target ───────────────────────────────────────────────────────────────────
    # Nhiệt độ trung bình ngày hôm sau (ngày cuối mỗi city sẽ là NaN — bỏ qua khi train)
    pdf["target_next_temp"] = pdf.groupby("city")["avg_temp_c"].shift(-1)

    n_with_target = pdf["target_next_temp"].notna().sum()
    print(f"ML features shape: {pdf.shape}")
    print(f"   Rows co target_next_temp: {n_with_target} / {len(pdf)}")

    if n_with_target == 0:
        print("Chua co row nao co target — can it nhat 2 ngay lien tiep moi city. "
              "04_ml_train se bao loi neu chay luc nay.")
    else:
        df_ml = spark.createDataFrame(pdf)
        (
            df_ml.write.format("delta").mode("overwrite")
            .option("overwriteSchema", "true")
            .saveAsTable(GOLD_ML_TABLE)
        )
        print(f"gold_ml_features: {GOLD_ML_TABLE}  ({len(pdf)} rows, {n_with_target} trainable)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bước 4: City Statistics — OVERWRITE
# MAGIC Aggregate summary toàn bộ lịch sử mỗi city, dùng cho Dashboard tab "Historical Stats".

# COMMAND ----------

stats_pdf = spark.table(GOLD_DAILY_TABLE).toPandas()

if len(stats_pdf) == 0:
    print("gold_weather_daily trong — bo qua city stats.")
else:
    city_stats = (
        stats_pdf.groupby(["city", "country"]).agg(
            days_tracked        = ("date",                 "count"),
            overall_avg_temp    = ("avg_temp_c",           "mean"),
            overall_max_temp    = ("max_temp_c",           "max"),
            overall_min_temp    = ("min_temp_c",           "min"),
            temp_std            = ("avg_temp_c",           "std"),
            avg_humidity        = ("avg_humidity",         "mean"),
            avg_wind_speed      = ("avg_wind_speed_kmh",   "mean"),
            avg_precipitation   = ("avg_precipitation_mm", "mean"),
            avg_uv_index        = ("avg_uv_index",         "mean"),
            avg_cloud_pct       = ("avg_cloud_pct",        "mean"),
            total_precipitation = ("avg_precipitation_mm", "sum"),
            first_recorded      = ("date",                 "min"),
            last_recorded       = ("date",                 "max"),
        )
        .reset_index()
    )
    float_cols = city_stats.select_dtypes(include="float").columns.tolist()
    city_stats[float_cols] = city_stats[float_cols].round(2)

    (
        spark.createDataFrame(city_stats)
        .write.format("delta").mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(GOLD_STATS_TABLE)
    )
    print(f"gold_city_stats: {GOLD_STATS_TABLE}")
    print(city_stats[["city", "days_tracked", "overall_avg_temp",
                       "overall_max_temp", "overall_min_temp"]].to_string(index=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Bước 5: Export CSV cho Streamlit

# COMMAND ----------

def export_csv(table_name: str, filename: str) -> bool:
    """Export Delta table sang CSV trong Workspace. Trả về True nếu thành công."""
    try:
        rows = spark.table(table_name).take(1)
    except Exception as e:
        print(f"  SKIP {filename} — khong doc duoc bang: {e}")
        return False
    if not rows:
        print(f"  SKIP {filename} — bang trong")
        return False
    csv_str = spark.table(table_name).toPandas().to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/{filename}", csv_str, overwrite=True)
    n_rows = len(csv_str.splitlines()) - 1
    print(f"  OK   {filename}  ({n_rows} rows)")
    return True

print("=== Exporting CSVs ===")
export_csv(GOLD_LATEST_TABLE, "gold_weather_latest.csv")
export_csv(GOLD_DAILY_TABLE,  "gold_weather_daily.csv")
export_csv(GOLD_ML_TABLE,     "gold_ml_features.csv")
export_csv(GOLD_STATS_TABLE,  "gold_city_stats.csv")

print(f"\nTat ca CSV tai: {EXPORT_WS_PATH}")
print("Download: python scripts/download_exports.py")