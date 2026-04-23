# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — ML: Weather Forecast Model
# MAGIC
# MAGIC **Thay đổi:**
# MAGIC - Đọc từ `gold_ml_features` (bảng đã feature-engineered ở 03_gold)
# MAGIC - Pipeline đơn giản, đầy đủ: load → train → evaluate → predict
# MAGIC - So sánh 3 model: Ridge / RandomForest / GradientBoosting
# MAGIC - Lưu kết quả predict ra `ml_weather_predictions` + export CSV cho Streamlit
# MAGIC - Export thêm `ml_model_metrics.csv` và `ml_forecast_7d.csv` cho dashboard

# COMMAND ----------

import warnings
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import mlflow
import mlflow.sklearn

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings("ignore")

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

GOLD_ML_TABLE    = f"{CATALOG}.{SCHEMA}.gold_ml_features"
GOLD_DAILY_TABLE = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
PRED_TABLE       = f"{CATALOG}.{SCHEMA}.ml_weather_predictions"
METRICS_TABLE    = f"{CATALOG}.{SCHEMA}.ml_model_metrics"

NOTEBOOK_DIR   = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR   = "/".join(NOTEBOOK_DIR.split("/")[:-1])
EXPORT_FS_PATH = f"file:/Workspace{NOTEBOOK_DIR}/exports"

print("✓ Imports OK")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Load data từ Gold ML Features

# COMMAND ----------

df_ml    = spark.table(GOLD_ML_TABLE).toPandas()
df_daily = spark.table(GOLD_DAILY_TABLE).toPandas()

print(f"Gold ML features : {len(df_ml)} rows,  {df_ml.shape[1]} columns")
print(f"Gold daily       : {len(df_daily)} rows")
print(f"Thành phố        : {df_ml['city'].nunique()}")
print(f"\nCác cột:\n{list(df_ml.columns)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Chuẩn bị features & target

# COMMAND ----------

# Label encode city
le = LabelEncoder()
df_ml["city_enc"] = le.fit_transform(df_ml["city"])
known_cities = list(le.classes_)
print(f"✓ Cities ({len(known_cities)}): {known_cities}")

# Danh sách features dùng cho huấn luyện
FEATURE_COLS = [
    # Categorical/encoded
    "city_enc",
    # Temporal
    "month", "day_of_year", "day_of_week", "week_of_year", "quarter", "is_weekend",
    "month_sin", "month_cos", "doy_sin", "doy_cos",
    # Weather condition
    "avg_humidity", "avg_pressure_hpa", "avg_wind_speed_kmh",
    "avg_cloud_pct", "avg_uv_index", "avg_precipitation_mm",
    # Lag features
    "temp_lag1", "temp_lag2", "temp_lag3", "temp_lag7",
    "humidity_lag1", "humidity_lag2",
    # Rolling stats
    "temp_roll_mean_3d", "temp_roll_mean_7d",
    "temp_roll_std_3d",
    # Derived
    "temp_range", "heat_index", "comfort_score",
]

TARGET_COL = "target_next_temp"   # nhiệt độ ngày hôm sau

# Chỉ giữ features thực sự có trong bảng
FEATURE_COLS = [f for f in FEATURE_COLS if f in df_ml.columns]
print(f"\n✓ Features sử dụng ({len(FEATURE_COLS)}):")
for f in FEATURE_COLS:
    print(f"  - {f}")

# Lọc rows có đủ target + features
df_clean = df_ml.dropna(subset=[TARGET_COL] + FEATURE_COLS)
print(f"\n✓ Rows sạch: {len(df_clean)} / {len(df_ml)}")

if len(df_clean) < 5:
    print("⚠️  Chưa đủ data để train (cần ≥5 rows). Pipeline tiếp tục nhưng metrics chưa có ý nghĩa.")
    print("   → Crawl thêm dữ liệu nhiều ngày để model tốt hơn.")

X = df_clean[FEATURE_COLS]
y = df_clean[TARGET_COL]

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Train/Test Split

# COMMAND ----------

n = len(df_clean)
if n < 10:
    # Quá ít: dùng toàn bộ làm train (không split)
    X_train, X_test = X, X
    y_train, y_test = y, y
    CV_FOLDS = min(3, n) if n >= 3 else 2
    print(f"⚠️  Chỉ {n} rows — dùng toàn bộ làm train+test")
elif n < 30:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    CV_FOLDS = 3
else:
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    CV_FOLDS = 5

print(f"Train : {len(X_train)} rows")
print(f"Test  : {len(X_test)} rows")
print(f"CV    : {CV_FOLDS}-fold")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Định nghĩa Models

# COMMAND ----------

def make_pipeline(estimator):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model",   estimator),
    ])

MODELS = {
    "Ridge": make_pipeline(
        Ridge(alpha=10.0)
    ),
    "RandomForest": make_pipeline(
        RandomForestRegressor(n_estimators=200, max_depth=15, random_state=42, n_jobs=-1)
    ),
    "GradientBoosting": make_pipeline(
        GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42)
    ),
}

print(f"✓ Định nghĩa {len(MODELS)} models: {list(MODELS.keys())}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Training + Evaluation

# COMMAND ----------
from sklearn.model_selection import KFold

mlflow.set_experiment("/Shared/weather-pipeline/weather_forecast")

results  = {}
cv_folds = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=42) if CV_FOLDS >= 2 else None


print(f"\n{'Model':<20} {'MAE':>8} {'RMSE':>8} {'R²':>7} {'CV MAE':>10}")
print("-" * 60)

for name, pipeline in MODELS.items():
    with mlflow.start_run(run_name=name):
        # Train
        pipeline.fit(X_train, y_train)

        # Test metrics
        y_pred = pipeline.predict(X_test)
        mae  = mean_absolute_error(y_test, y_pred)
        rmse = mean_squared_error(y_test, y_pred) ** 0.5
        r2   = r2_score(y_test, y_pred)

        # Cross-validation MAE
        if cv_folds and len(X) >= CV_FOLDS * 2:
            cv_scores = cross_val_score(
                pipeline, X, y,
                cv=cv_folds, scoring="neg_mean_absolute_error", n_jobs=-1
            )
            cv_mae_mean = -cv_scores.mean()
            cv_mae_std  = cv_scores.std()
        else:
            cv_mae_mean = mae
            cv_mae_std  = 0.0

        # MLflow logging
        mlflow.log_params({"model_type": name, "n_features": len(FEATURE_COLS), "cv_folds": CV_FOLDS})
        mlflow.log_metrics({"mae": mae, "rmse": rmse, "r2": r2, "cv_mae": cv_mae_mean})
        mlflow.sklearn.log_model(pipeline, f"model_{name}")

        results[name] = {
            "model": pipeline, "mae": mae, "rmse": rmse, "r2": r2,
            "cv_mae_mean": cv_mae_mean, "cv_mae_std": cv_mae_std,
        }
        print(f"{name:<20} {mae:>8.3f} {rmse:>8.3f} {r2:>7.3f} {cv_mae_mean:>10.3f}°C")

# Chọn model tốt nhất (MAE thấp nhất)
best_name  = min(results, key=lambda k: results[k]["mae"])
best_model = results[best_name]["model"]
best_mae   = results[best_name]["mae"]

print(f"\n✅ Model tốt nhất: {best_name}  (MAE = {best_mae:.3f}°C)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Lưu metrics vào Delta

# COMMAND ----------

metrics_rows = []
for name, m in results.items():
    metrics_rows.append({
        "model_name":    name,
        "mae":           round(m["mae"], 4),
        "rmse":          round(m["rmse"], 4),
        "r2":            round(m["r2"], 4),
        "cv_mae_mean":   round(m["cv_mae_mean"], 4),
        "cv_mae_std":    round(m["cv_mae_std"], 4),
        "is_best":       (name == best_name),
        "trained_at":    datetime.now().isoformat(),
        "n_train":       len(X_train),
        "n_test":        len(X_test),
        "n_features":    len(FEATURE_COLS),
    })

df_metrics = spark.createDataFrame(pd.DataFrame(metrics_rows))
(
    df_metrics.write.format("delta").mode("overwrite")
    .option("overwriteSchema", "true").saveAsTable(METRICS_TABLE)
)
print(f"✓ Model metrics saved: {METRICS_TABLE}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Predict — Dự đoán thời tiết tương lai

# COMMAND ----------

def get_city_baseline(city: str) -> dict:
    """Lấy giá trị thời tiết gần nhất của thành phố làm input dự đoán."""
    city_rows = df_daily[df_daily["city"] == city].sort_values("date", ascending=False)
    if len(city_rows) == 0:
        return {
            "avg_humidity": 70, "avg_pressure_hpa": 1013,
            "avg_wind_speed_kmh": 15, "avg_cloud_pct": 50,
            "avg_uv_index": 5, "avg_precipitation_mm": 0,
            "recent_temps": [25.0],
        }
    recent = city_rows.head(7)
    latest = recent.iloc[0]
    return {
        "avg_humidity":         float(latest.get("avg_humidity", 70)),
        "avg_pressure_hpa":     float(latest.get("avg_pressure_hpa", 1013)),
        "avg_wind_speed_kmh":   float(latest.get("avg_wind_speed_kmh", 15)),
        "avg_cloud_pct":        float(latest.get("avg_cloud_pct", 50)),
        "avg_uv_index":         float(latest.get("avg_uv_index", 5)),
        "avg_precipitation_mm": float(latest.get("avg_precipitation_mm", 0)),
        "temp_range":           float(latest.get("max_temp_c", 28) - latest.get("min_temp_c", 22)),
        "recent_temps":         recent["avg_temp_c"].tolist(),
    }


def predict_city(city: str, days_ahead: int) -> dict | None:
    """Dự đoán nhiệt độ cho city vào N ngày tới."""
    if city not in known_cities:
        return None

    baseline    = get_city_baseline(city)
    target_date = datetime.now() + timedelta(days=days_ahead)
    temps       = baseline["recent_temps"]
    avg_temp    = np.mean(temps) if temps else 25.0

    # Build feature row
    row = {
        "city_enc":             le.transform([city])[0],
        "month":                target_date.month,
        "day_of_year":          target_date.timetuple().tm_yday,
        "day_of_week":          target_date.weekday(),
        "week_of_year":         int(target_date.isocalendar()[1]),
        "quarter":              (target_date.month - 1) // 3 + 1,
        "is_weekend":           int(target_date.weekday() >= 5),
        "month_sin":            np.sin(2 * np.pi * target_date.month / 12),
        "month_cos":            np.cos(2 * np.pi * target_date.month / 12),
        "doy_sin":              np.sin(2 * np.pi * target_date.timetuple().tm_yday / 365),
        "doy_cos":              np.cos(2 * np.pi * target_date.timetuple().tm_yday / 365),
        "avg_humidity":         baseline["avg_humidity"],
        "avg_pressure_hpa":     baseline["avg_pressure_hpa"],
        "avg_wind_speed_kmh":   baseline["avg_wind_speed_kmh"],
        "avg_cloud_pct":        baseline["avg_cloud_pct"],
        "avg_uv_index":         baseline["avg_uv_index"],
        "avg_precipitation_mm": baseline["avg_precipitation_mm"],
        "temp_lag1":            temps[0] if len(temps) > 0 else avg_temp,
        "temp_lag2":            temps[1] if len(temps) > 1 else avg_temp,
        "temp_lag3":            temps[2] if len(temps) > 2 else avg_temp,
        "temp_lag7":            temps[-1] if temps else avg_temp,
        "humidity_lag1":        baseline["avg_humidity"],
        "humidity_lag2":        baseline["avg_humidity"],
        "temp_roll_mean_3d":    np.mean(temps[:3]) if len(temps) >= 3 else avg_temp,
        "temp_roll_mean_7d":    np.mean(temps),
        "temp_roll_std_3d":     float(np.std(temps[:3])) if len(temps) >= 3 else 0.5,
        "temp_range":           baseline.get("temp_range", 6.0),
        "heat_index":           avg_temp + 2.0,   # ước tính đơn giản
        "comfort_score":        max(0, min(100, 100 - 4 * abs(avg_temp - 22))),
    }

    X_pred = pd.DataFrame([{f: row.get(f, 0.0) for f in FEATURE_COLS}])
    pred   = best_model.predict(X_pred)[0]

    # Khoảng tin cậy: MAE × (1 + 10% mỗi ngày thêm)
    margin = best_mae * (1 + (days_ahead - 1) * 0.10)

    # Điều kiện ước tính từ cloud cover
    cloud = baseline["avg_cloud_pct"]
    if   cloud < 20: cond = "Nắng đẹp ☀️"
    elif cloud < 50: cond = "Ít mây 🌤️"
    elif cloud < 80: cond = "Nhiều mây ⛅"
    else:            cond = "Có thể mưa 🌧️"

    return {
        "city":                 city,
        "target_date":          target_date.strftime("%Y-%m-%d"),
        "days_ahead":           days_ahead,
        "predicted_temp_c":     round(float(pred), 1),
        "confidence_low":       round(float(pred - margin), 1),
        "confidence_high":      round(float(pred + margin), 1),
        "estimated_condition":  cond,
        "current_temp_c":       round(avg_temp, 1),
        "temp_change":          round(float(pred) - round(avg_temp, 1), 1),
        "model_used":           best_name,
        "model_mae":            round(best_mae, 3),
        "predicted_at":         datetime.now().isoformat(),
    }

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. Demo dự đoán — Ngày mai và 7 ngày tới

# COMMAND ----------

print("=" * 68)
print("  DỰ ĐOÁN THỜI TIẾT  —  Demo")
print("=" * 68)
print(f"\n{'City':<22} {'Ngày':>12} {'Dự báo':>8} {'Khoảng':>16} {'Thay đổi':>10}  Điều kiện")
print("-" * 90)

for city in known_cities:
    pred = predict_city(city, days_ahead=1)
    if pred:
        change_str = f"+{pred['temp_change']}" if pred["temp_change"] >= 0 else str(pred["temp_change"])
        conf_str   = f"[{pred['confidence_low']:.1f} – {pred['confidence_high']:.1f}]"
        print(f"  {city:<20} {pred['target_date']} {pred['predicted_temp_c']:>7.1f}°C {conf_str:>16} {change_str:>9}°C  {pred['estimated_condition']}")

print(f"\n\n  7 NGÀY TỚI — {known_cities[0] if known_cities else '?'}:")
print("-" * 60)
if known_cities:
    for d in range(1, 8):
        pred = predict_city(known_cities[0], days_ahead=d)
        if pred:
            print(
                f"  +{d} ngày ({pred['target_date']})  "
                f"{pred['predicted_temp_c']:>5.1f}°C  "
                f"[{pred['confidence_low']:.1f} – {pred['confidence_high']:.1f}]  "
                f"{pred['estimated_condition']}"
            )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. Lưu toàn bộ predictions vào Delta + Export CSV

# COMMAND ----------

# Dự đoán tất cả city × 7 ngày
all_preds = []
for city in known_cities:
    for d in range(1, 8):
        p = predict_city(city, days_ahead=d)
        if p:
            all_preds.append(p)

print(f"Tổng predictions: {len(all_preds)}  ({len(known_cities)} cities × 7 ngày)")

if all_preds:
    from pyspark.sql.functions import current_timestamp as _now
    df_pred = spark.createDataFrame(pd.DataFrame(all_preds))
    (
        df_pred.write.format("delta").mode("overwrite")
        .option("overwriteSchema", "true").saveAsTable(PRED_TABLE)
    )
    print(f"✅ Predictions saved → {PRED_TABLE}")
    df_pred.orderBy("city", "days_ahead").show(14, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 10. Export CSV cho Streamlit

# COMMAND ----------

dbutils.fs.mkdirs(EXPORT_FS_PATH)

def export_df_csv(spark_table: str, filename: str):
    rows = spark.table(spark_table).take(1)
    if not rows:
        print(f"⏭  {filename} — bảng trống")
        return
    csv = spark.table(spark_table).toPandas().to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/{filename}", csv, overwrite=True)
    print(f"✓ Exported: {filename}")

export_df_csv(PRED_TABLE,    "ml_forecast_7d.csv")       # dự báo 7 ngày
export_df_csv(METRICS_TABLE, "ml_model_metrics.csv")     # hiệu suất từng model

# Export feature importance (RandomForest / GradientBoosting)
fi_data = []
for name in ["RandomForest", "GradientBoosting"]:
    if name in results:
        estimator = results[name]["model"].named_steps["model"]
        if hasattr(estimator, "feature_importances_"):
            for feat, imp in zip(FEATURE_COLS, estimator.feature_importances_):
                fi_data.append({"model": name, "feature": feat, "importance": round(float(imp), 6)})

if fi_data:
    fi_csv = pd.DataFrame(fi_data).sort_values(["model","importance"], ascending=[True,False]).to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/ml_feature_importance.csv", fi_csv, overwrite=True)
    print("✓ Exported: ml_feature_importance.csv")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 11. Tóm tắt

# COMMAND ----------

print("=" * 65)
print("  KẾT QUẢ TRAINING")
print("=" * 65)
print(f"  Training samples : {len(X_train)}")
print(f"  Test samples     : {len(X_test)}")
print(f"  Features used    : {len(FEATURE_COLS)}")
print(f"  Models trained   : {len(results)}")
print()
print(f"  {'Model':<22} {'MAE':>8} {'RMSE':>8} {'R²':>7}")
print("  " + "-" * 50)
for name, m in sorted(results.items(), key=lambda x: x[1]["mae"]):
    tag = " ← BEST" if name == best_name else ""
    print(f"  {name:<22} {m['mae']:>7.3f}°C {m['rmse']:>7.3f}°C {m['r2']:>6.3f}{tag}")
print()
print(f"  Best model       : {best_name}")
print(f"  Best MAE         : {best_mae:.3f}°C")
print(f"  Predictions      : {len(all_preds)} ({len(known_cities)} cities × 7 days)")
print()
print(f"  CSV exports:")
print(f"    ml_forecast_7d.csv       → dự báo 7 ngày × tất cả thành phố")
print(f"    ml_model_metrics.csv     → so sánh hiệu suất model")
print(f"    ml_feature_importance.csv→ tầm quan trọng features")
print("=" * 65)