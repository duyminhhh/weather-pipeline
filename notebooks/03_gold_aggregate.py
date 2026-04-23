# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Gold Layer: Aggregate for BI

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.window import Window

# ── Cấu hình ──────────────────────────────────────────────
CATALOG = "workspace"
SCHEMA  = "weather_pipeline"
SILVER_TABLE      = f"{CATALOG}.{SCHEMA}.silver_weather_clean"
GOLD_DAILY_TABLE  = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
GOLD_LATEST_TABLE = f"{CATALOG}.{SCHEMA}.gold_weather_latest"

# Export vào Workspace folder — không cần Volume, không cần tạo gì thêm
NOTEBOOK_DIR = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR = "/".join(NOTEBOOK_DIR.split("/")[:-1])
EXPORT_WS_PATH = f"/Workspace{NOTEBOOK_DIR}/exports"  # dùng để ghi file
EXPORT_FS_PATH = f"file:{EXPORT_WS_PATH}"             # dùng để đọc lại qua dbutils

# COMMAND ----------

df = spark.table(SILVER_TABLE)
print(f"Silver rows: {df.count()}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Aggregate 1: Daily summary per city

# COMMAND ----------

daily = (
    df.groupBy("city", "country", "date")
    .agg(
        F.round(F.avg("temperature_c"), 2).alias("avg_temp_c"),
        F.round(F.max("temperature_c"), 2).alias("max_temp_c"),
        F.round(F.min("temperature_c"), 2).alias("min_temp_c"),
        F.round(F.avg("feels_like_c"),  2).alias("avg_feels_like_c"),
        F.round(F.avg("humidity"),      1).alias("avg_humidity"),
        F.round(F.avg("pressure_hpa"),  1).alias("avg_pressure_hpa"),
        F.round(F.avg("wind_speed_kmh"),2).alias("avg_wind_speed_kmh"),
        F.round(F.max("wind_speed_kmh"),2).alias("max_wind_speed_kmh"),
        F.round(F.avg("cloud_cover_pct"),1).alias("avg_cloud_pct"),
        F.round(F.avg("precipitation_mm"),2).alias("avg_precipitation_mm"),
        F.round(F.avg("uv_index"),      1).alias("avg_uv_index"),
        F.count("*").alias("sample_count"),
    )
    .orderBy("date", "city")
)

daily.show(10)

(
    daily.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(GOLD_DAILY_TABLE)
)
print(f"✓ Gold daily: {GOLD_DAILY_TABLE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Aggregate 2: Latest snapshot per city (realtime dashboard)

# COMMAND ----------

w = Window.partitionBy("city").orderBy(F.desc("crawled_at"))

latest = (
    df
    .withColumn("rn", F.row_number().over(w))
    .filter(F.col("rn") == 1)
    .drop("rn")
)

(
    latest.write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(GOLD_LATEST_TABLE)
)
print(f"✓ Gold latest: {GOLD_LATEST_TABLE}")
latest.select("city", "country", "temperature_c", "humidity", "weather_desc", "crawled_at").show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Export CSV ra Workspace (cho Streamlit app download)

# COMMAND ----------

# Tạo thư mục exports trong Workspace
dbutils.fs.mkdirs(EXPORT_FS_PATH)
print(f"✓ Thư mục: {EXPORT_WS_PATH}")

def export_csv(table_name, filename):
    """Ghi DataFrame thành CSV vào Workspace folder."""
    csv_content = spark.table(table_name).toPandas().to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/{filename}", csv_content, overwrite=True)
    print(f"✓ Exported: {filename}")

export_csv(GOLD_DAILY_TABLE,  "gold_weather_daily.csv")
export_csv(GOLD_LATEST_TABLE, "gold_weather_latest.csv")

print(f"\n✓ Files tại Workspace: {EXPORT_WS_PATH}")
print("→ Download về local: python scripts/download_exports.py")