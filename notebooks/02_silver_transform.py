# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Silver Layer: Clean & Normalize

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType
from delta.tables import DeltaTable

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

BRONZE_TABLE = f"{CATALOG}.{SCHEMA}.bronze_weather_raw"
SILVER_TABLE = f"{CATALOG}.{SCHEMA}.silver_weather_clean"

# COMMAND ----------

df = spark.table(BRONZE_TABLE)
print(f"Bronze rows: {df.count()}")
print("Columns:", df.columns)

# COMMAND ----------

# Mapping đúng với field names của crawler (weather_crawler.py)
silver = (
    df
    .select(
        # Định danh
        F.col("city").cast("string"),
        F.col("country").cast("string"),
        F.col("latitude").cast(DoubleType()),
        F.col("longitude").cast(DoubleType()),
        F.col("timezone").cast("string"),

        # Nhiệt độ hiện tại
        F.col("temperature_c").cast(DoubleType()),
        F.col("feels_like_c").cast(DoubleType()),

        # Daily min/max (từ Open-Meteo daily vars)
        F.col("temp_min_c").cast(DoubleType()),
        F.col("temp_max_c").cast(DoubleType()),

        # Khí tượng
        F.col("humidity").cast(IntegerType()),
        F.col("pressure_hpa").cast(DoubleType()),
        F.col("cloud_cover_pct").cast(IntegerType()),
        F.col("visibility_m").cast(IntegerType()),
        F.col("precipitation_mm").cast(DoubleType()),
        F.col("rain_mm").cast(DoubleType()),
        F.col("precip_sum_mm").cast(DoubleType()),   # daily total

        # Gió
        F.col("wind_speed_kmh").cast(DoubleType()),
        F.col("wind_direction_deg").cast(IntegerType()),
        F.col("wind_gusts_kmh").cast(DoubleType()),
        F.col("wind_max_kmh").cast(DoubleType()),    # daily max

        # UV & weather code
        F.col("weather_code").cast(IntegerType()),
        F.col("weather_desc").cast("string"),
        F.col("uv_index").cast(DoubleType()),
        F.col("uv_index_max").cast(DoubleType()),

        # Sunrise / Sunset
        F.col("sunrise").cast("string"),
        F.col("sunset").cast("string"),

        # Metadata
        F.to_timestamp(F.col("crawled_at")).alias("crawled_at"),
        F.col("ingested_at"),
    )
    .filter(F.col("city").isNotNull() & F.col("temperature_c").isNotNull())
    .withColumn("date",       F.to_date("crawled_at"))
    .withColumn("hour",       F.hour("crawled_at"))
    .withColumn("crawl_hour", F.date_trunc("hour", "crawled_at"))
    .dropDuplicates(["city", "crawl_hour"])
    .drop("crawl_hour")
)

print(f"Silver rows after clean: {silver.count()}")
silver.select("city", "country", "temperature_c", "temp_min_c", "temp_max_c",
              "humidity", "weather_desc", "crawled_at").show(10, truncate=False)

# COMMAND ----------

if spark.catalog.tableExists(SILVER_TABLE):
    (
        DeltaTable.forName(spark, SILVER_TABLE).alias("existing")
        .merge(
            silver.alias("new"),
            "existing.city = new.city AND existing.crawled_at = new.crawled_at"
        )
        .whenNotMatchedInsertAll()
        .execute()
    )
    print(f"✓ Silver table merged: {SILVER_TABLE}")
else:
    (
        silver.write
        .format("delta")
        .mode("overwrite")
        .partitionBy("date")
        .option("mergeSchema", "true")
        .saveAsTable(SILVER_TABLE)
    )
    print(f"✓ Silver table created: {SILVER_TABLE}")

spark.sql(f"SELECT COUNT(*) AS total FROM {SILVER_TABLE}").show()
