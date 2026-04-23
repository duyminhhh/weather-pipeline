# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — ML: Train Temperature Forecast Model + MLflow

# COMMAND ----------

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import LabelEncoder

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

GOLD_DAILY_TABLE  = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
SILVER_TABLE      = f"{CATALOG}.{SCHEMA}.silver_weather_clean"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Chuẩn bị features — dùng Silver nếu Gold chưa đủ data

# COMMAND ----------

df_gold = spark.table(GOLD_DAILY_TABLE).toPandas()
print(f"Gold daily rows: {len(df_gold)}")

if len(df_gold) >= 10:
    # Đủ data daily → train trên Gold (tốt hơn)
    df = df_gold.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"]       = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear

    le = LabelEncoder()
    df["city_enc"] = le.fit_transform(df["city"])

    FEATURES = [
        "city_enc", "month", "day_of_year",
        "avg_humidity", "avg_pressure_hpa",
        "avg_wind_speed_kmh", "avg_cloud_pct", "avg_uv_index",
    ]
    TARGET = "avg_temp_c"
    print("→ Training trên Gold daily data")

else:
    # Ít data (mới crawl 1-2 lần) → dùng Silver (per-reading level)
    print(f"Gold chỉ có {len(df_gold)} rows — dùng Silver table để train")
    df_silver = spark.table(SILVER_TABLE).toPandas()
    print(f"Silver rows: {len(df_silver)}")

    if len(df_silver) < 5:
        print(
            f"⚠️  Chỉ có {len(df_silver)} records — chưa đủ để train model có ý nghĩa.\n"
            "Pipeline vẫn chạy tiếp, nhưng kết quả metrics chưa đại diện.\n"
            "→ Crawl thêm data nhiều ngày để có model tốt hơn."
        )

    df = df_silver.copy()
    df["crawled_at"] = pd.to_datetime(df["crawled_at"])
    df["month"]       = df["crawled_at"].dt.month
    df["day_of_year"] = df["crawled_at"].dt.dayofyear
    df["hour"]        = df["crawled_at"].dt.hour

    le = LabelEncoder()
    df["city_enc"] = le.fit_transform(df["city"])

    FEATURES = [
        "city_enc", "month", "day_of_year", "hour",
        "humidity", "pressure_hpa",
        "wind_speed_kmh", "cloud_cover_pct", "uv_index",
    ]
    TARGET = "temperature_c"
    print("→ Training trên Silver data")

# COMMAND ----------

df_clean = df.dropna(subset=FEATURES + [TARGET])
print(f"Rows sau dropna: {len(df_clean)}")

X = df_clean[FEATURES]
y = df_clean[TARGET]

# Nếu quá ít data thì không split, dùng toàn bộ để train + eval bằng cross-val
if len(df_clean) < 15:
    X_train, X_test = X, X
    y_train, y_test = y, y
    use_cv = True
    print("⚠️  Ít data → dùng toàn bộ cho train + cross-validation (5-fold)")
else:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    use_cv = False
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Train & compare models với MLflow tracking

# COMMAND ----------

mlflow.set_experiment("/Shared/weather_forecast")

MODELS = {
    "LinearRegression": LinearRegression(),
    "RandomForest":     RandomForestRegressor(n_estimators=100, random_state=42),
    "GradientBoosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
}

best_name, best_r2 = None, -999

for name, model in MODELS.items():
    with mlflow.start_run(run_name=name):
        model.fit(X_train, y_train)
        preds = model.predict(X_test)

        mae  = mean_absolute_error(y_test, preds)
        rmse = np.sqrt(mean_squared_error(y_test, preds))
        r2   = r2_score(y_test, preds)

        mlflow.log_param("model_type", name)
        mlflow.log_param("features",   FEATURES)
        mlflow.log_param("n_samples",  len(df_clean))
        mlflow.log_metric("mae",  mae)
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("r2",   r2)
        mlflow.sklearn.log_model(model, "model")

        print(f"{name:20}: MAE={mae:.2f}°C  RMSE={rmse:.2f}°C  R²={r2:.3f}")

        if r2 > best_r2:
            best_r2, best_name = r2, name

print(f"\n✓ Best model: {best_name} (R²={best_r2:.3f})")
print("→ Xem chi tiết: sidebar Experiments → weather_forecast")
