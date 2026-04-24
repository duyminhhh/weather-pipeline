# Databricks notebook source
# MAGIC %md
# MAGIC # 01 — Bronze Layer: Ingest raw JSON từ data_raw → Delta
# MAGIC
# MAGIC Đọc file `weather_latestX.json` mới nhất trong `data_raw/` (X lớn nhất)
# MAGIC và append vào bảng Delta bronze.

# COMMAND ----------

import json
from pyspark.sql.functions import current_timestamp, lit

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.bronze_weather_raw"

NOTEBOOK_DIR = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR = "/".join(NOTEBOOK_DIR.split("/")[:-1])

DATA_RAW_FS = f"file:/Workspace{NOTEBOOK_DIR}/data_raw"
DATA_RAW_WS = f"/Workspace{NOTEBOOK_DIR}/data_raw"

print(f"Thư mục notebook : {NOTEBOOK_DIR}")
print(f"Đọc data_raw từ  : {DATA_RAW_FS}")

# COMMAND ----------

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"✓ Schema: {CATALOG}.{SCHEMA}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Tìm file weather_latestX.json có số thứ tự lớn nhất

# COMMAND ----------

try:
    all_files = dbutils.fs.ls(DATA_RAW_FS)
except Exception as e:
    raise FileNotFoundError(
        f"Không tìm thấy thư mục data_raw: {DATA_RAW_FS}\n"
        f"Hãy chạy weather_crawler trước. Chi tiết: {e}"
    )

# Lấy tất cả weather_latestX.json và chọn X lớn nhất
numbered_files = []
for f in all_files:
    name = f.name.rstrip("/")
    if name.startswith("weather_latest") and name.endswith(".json"):
        try:
            num = int(name[len("weather_latest"):-len(".json")])
            numbered_files.append((num, f))
        except ValueError:
            pass

if not numbered_files:
    raise FileNotFoundError(
        f"Không có file weather_latestX.json trong {DATA_RAW_FS}\n"
        "Hãy chạy weather_crawler trước."
    )

# Sort và lấy file mới nhất
numbered_files.sort(key=lambda x: x[0], reverse=True)
latest_num, latest_file = numbered_files[0]
latest_name = latest_file.name.rstrip("/")

print(f"Tổng files trong data_raw: {len(numbered_files)}")
print(f"File mới nhất            : {latest_name}  (số {latest_num})")
print(f"Đường dẫn                : {latest_file.path}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Đọc JSON và tạo DataFrame

# COMMAND ----------

raw_text = dbutils.fs.head(latest_file.path, 10_000_000)   # tối đa 10 MB
records  = json.loads(raw_text)

print(f"✓ Đọc được {len(records)} records từ {latest_name}")

# Chuyển list JSON → Spark DataFrame
df = (
    spark.createDataFrame(records)
    .withColumn("ingested_at",  current_timestamp())
    .withColumn("source_file",  lit(latest_name))
    .withColumn("source_seq",   lit(latest_num))   # số thứ tự file để trace
)

print("Schema:")
df.printSchema()
df.select("city", "country", "temperature_c", "humidity", "crawled_at").show(5, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Append vào Bronze Delta Table

# COMMAND ----------

(
    df.write
    .format("delta")
    .mode("append")
    .option("mergeSchema", "true")
    .saveAsTable(BRONZE_TABLE)
)

print(f"✓ Bronze table updated: {BRONZE_TABLE}")
print(f"  File nguồn: {latest_name}")
spark.sql(f"SELECT COUNT(*) AS total_rows FROM {BRONZE_TABLE}").show()

# Hiển thị vài dòng mới nhất
spark.sql(f"""
    SELECT city, temperature_c, humidity, crawled_at, source_file, source_seq
    FROM {BRONZE_TABLE}
    ORDER BY ingested_at DESC
    LIMIT 5
""").show(truncate=False)