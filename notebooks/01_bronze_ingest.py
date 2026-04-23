# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Bronze Layer: Ingest raw JSON → Delta

# COMMAND ----------

import json
from pyspark.sql.functions import current_timestamp, lit

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.bronze_weather_raw"

# Đường dẫn file JSON trong Workspace (cùng thư mục với notebook)
# Upload file weather_latest.json lên /Shared/weather-pipeline/ là đọc được
NOTEBOOK_DIR  = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR  = "/".join(NOTEBOOK_DIR.split("/")[:-1])   # bỏ tên notebook, lấy thư mục
JSON_FILENAME = "weather_latest.json"
JSON_WS_PATH  = f"{NOTEBOOK_DIR}/{JSON_FILENAME}"

print(f"Thư mục notebook : {NOTEBOOK_DIR}")
print(f"Đọc file JSON từ : {JSON_WS_PATH}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✓ Schema: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# Đọc nội dung file JSON từ Workspace bằng dbutils (không dùng Spark path)
try:
    raw_text = dbutils.notebook.run(
        ".", 0,
    )
except Exception:
    pass

# Đọc trực tiếp bằng dbutils.fs — Workspace files dùng prefix "file:/Workspace"
ws_fs_path = f"file:/Workspace{JSON_WS_PATH}"
print(f"Đọc từ: {ws_fs_path}")

raw_text = dbutils.fs.head(ws_fs_path, 10_000_000)  # đọc tối đa 10MB
records  = json.loads(raw_text)

print(f"✓ Đọc được {len(records)} records từ {JSON_FILENAME}")

# COMMAND ----------

# Chuyển list JSON → Spark DataFrame
df = (
    spark.createDataFrame(records)
    .withColumn("ingested_at", current_timestamp())
    .withColumn("source_file", lit(JSON_FILENAME))
)

print(f"Schema:")
df.printSchema()
df.select("city", "country", "temperature_c", "humidity", "crawled_at").show(5, truncate=False)

# COMMAND ----------

(
    df.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")
    .saveAsTable(BRONZE_TABLE)
)

print(f"✓ Bronze table updated: {BRONZE_TABLE}")
spark.sql(f"SELECT COUNT(*) AS total FROM {BRONZE_TABLE}").show()
