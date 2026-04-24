# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — ML Train: Dự báo nhiệt độ ngày hôm sau
# MAGIC
# MAGIC **Pipeline:**
# MAGIC 1. Load `gold_ml_features` từ Gold layer
# MAGIC 2. Feature selection + preprocessing
# MAGIC 3. Train 3 models: RandomForest · GradientBoosting · Ridge (baseline)
# MAGIC 4. Evaluate → chọn model tốt nhất theo RMSE
# MAGIC 5. Log vào MLflow (nếu có)
# MAGIC 6. Predict toàn bộ dataset + tạo forecast 7 ngày tới
# MAGIC 7. Lưu kết quả vào Delta + export CSV cho Streamlit

# COMMAND ----------

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

GOLD_ML_TABLE      = f"{CATALOG}.{SCHEMA}.gold_ml_features"
GOLD_DAILY_TABLE   = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
GOLD_LATEST_TABLE  = f"{CATALOG}.{SCHEMA}.gold_weather_latest"
ML_PRED_TABLE      = f"{CATALOG}.{SCHEMA}.gold_ml_predictions"
ML_METRICS_TABLE   = f"{CATALOG}.{SCHEMA}.gold_ml_metrics"
ML_FEATIMP_TABLE   = f"{CATALOG}.{SCHEMA}.gold_ml_feature_importance"

NOTEBOOK_DIR   = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR   = "/".join(NOTEBOOK_DIR.split("/")[:-1])
EXPORT_WS_PATH = f"/Workspace{NOTEBOOK_DIR}/exports"
EXPORT_FS_PATH = f"file:{EXPORT_WS_PATH}"

dbutils.fs.mkdirs(EXPORT_FS_PATH)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Load data

# COMMAND ----------

pdf = spark.table(GOLD_ML_TABLE).toPandas()
print(f"gold_ml_features shape: {pdf.shape}")
print(f"Columns: {list(pdf.columns)}")
print(f"Cities: {sorted(pdf['city'].unique())}")
print(f"Date range: {pdf['date'].min()} → {pdf['date'].max()}")

# Drop rows không có target
pdf_clean = pdf.dropna(subset=["target_next_temp"]).copy()
pdf_clean["date"] = pd.to_datetime(pdf_clean["date"])
pdf_clean = pdf_clean.sort_values(["city", "date"]).reset_index(drop=True)
print(f"\nRows có target: {len(pdf_clean)} / {len(pdf)}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Feature Engineering & Selection

# COMMAND ----------

FEATURE_COLS = [
    # Điều kiện thời tiết hiện tại
    "avg_temp_c", "avg_feels_like_c", "avg_humidity",
    "avg_pressure_hpa", "avg_wind_speed_kmh", "max_wind_speed_kmh",
    "avg_cloud_pct", "avg_precipitation_mm", "avg_uv_index",

    # Derived features
    "temp_range", "heat_index", "comfort_score", "weather_severity",

    # Temporal features
    "month_sin", "month_cos", "doy_sin", "doy_cos",
    "day_of_week", "is_weekend", "quarter",

    # Lag features
    "temp_lag1", "temp_lag2", "temp_lag3", "temp_lag7",
    "humidity_lag1", "humidity_lag3",

    # Rolling stats
    "temp_roll_mean_3d", "temp_roll_mean_7d",
    "temp_roll_std_3d",  "temp_roll_std_7d",
    "precip_roll_sum_3d", "precip_roll_sum_7d",
]

# Chỉ giữ các cột thực sự có trong data
FEATURE_COLS = [c for c in FEATURE_COLS if c in pdf_clean.columns]
print(f"Features được dùng: {len(FEATURE_COLS)}")
print(FEATURE_COLS)

# Label encode city
le = LabelEncoder()
pdf_clean["city_encoded"] = le.fit_transform(pdf_clean["city"])
ALL_FEATURES = FEATURE_COLS + ["city_encoded"]

# Train/test split: 20% cuối theo date (không random để giữ tính thời gian)
# Dùng sort + iloc thay vì quantile() vì quantile trên datetime trả về timestamp int, không đáng tin
sorted_dates = pdf_clean["date"].drop_duplicates().sort_values().reset_index(drop=True)
split_idx    = int(len(sorted_dates) * 0.80)
split_date   = sorted_dates.iloc[split_idx]

train_mask = pdf_clean["date"] <= split_date
test_mask  = pdf_clean["date"] >  split_date

train = pdf_clean[train_mask]
test  = pdf_clean[test_mask]

# Guard: đảm bảo cả 2 tập đều có dữ liệu
assert len(train) > 0, "❌ Train set rỗng — kiểm tra lại cột 'date'"
assert len(test)  > 0, (
    f"❌ Test set rỗng — split_date={split_date.date()}, "
    f"data kết thúc tại {pdf_clean['date'].max().date()}. "
    "Hãy kiểm tra gold_ml_features có đủ dữ liệu không."
)

# Fill NaN với mean của train set
feature_means = train[ALL_FEATURES].mean()

X_train = train[ALL_FEATURES].fillna(feature_means)
y_train = train["target_next_temp"]
X_test  = test[ALL_FEATURES].fillna(feature_means)
y_test  = test["target_next_temp"]

print(f"\nSplit date : {split_date.date()}")
print(f"Train: {len(train)} rows ({train['date'].min().date()} → {train['date'].max().date()})")
print(f"Test : {len(test)}  rows ({test['date'].min().date()} → {test['date'].max().date()})")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Train Models

# COMMAND ----------

MODELS = {
    "RandomForest": RandomForestRegressor(
        n_estimators=200, max_depth=10, min_samples_leaf=2,
        n_jobs=-1, random_state=42,
    ),
    "GradientBoosting": GradientBoostingRegressor(
        n_estimators=150, max_depth=5, learning_rate=0.1,
        subsample=0.8, random_state=42,
    ),
    "Ridge": Pipeline([
        ("scaler", StandardScaler()),
        ("ridge",  Ridge(alpha=1.0)),
    ]),
}

results   = {}
all_preds = {}

experiment_name = "/Shared/weather-pipeline/ml_experiments"
try:
    mlflow.set_experiment(experiment_name)
except Exception:
    pass   # bỏ qua nếu mlflow không khả dụng

with mlflow.start_run(run_name="weather_forecast_training") as run:
    mlflow.log_param("n_features",   len(ALL_FEATURES))
    mlflow.log_param("train_rows",   len(train))
    mlflow.log_param("test_rows",    len(test))
    mlflow.log_param("split_date",   str(split_date.date()))
    mlflow.log_param("n_cities",     len(pdf_clean["city"].unique()))

    for name, model in MODELS.items():
        print(f"\n── Đang train: {name} ──")
        model.fit(X_train, y_train)

        preds_train = model.predict(X_train)
        preds_test  = model.predict(X_test)

        # Metrics
        metrics = {
            "rmse_train": float(np.sqrt(mean_squared_error(y_train, preds_train))),
            "rmse_test":  float(np.sqrt(mean_squared_error(y_test,  preds_test))),
            "mae_test":   float(mean_absolute_error(y_test,  preds_test)),
            "r2_test":    float(r2_score(y_test,  preds_test)),
        }

        print(f"  RMSE train: {metrics['rmse_train']:.3f}°C")
        print(f"  RMSE test : {metrics['rmse_test']:.3f}°C")
        print(f"  MAE  test : {metrics['mae_test']:.3f}°C")
        print(f"  R²   test : {metrics['r2_test']:.3f}")

        mlflow.log_metrics({f"{name}_{k}": v for k, v in metrics.items()})
        results[name] = {"model": model, **metrics, "preds_test": preds_test}
        all_preds[name] = preds_test

    # Chọn model tốt nhất theo RMSE test
    best_name  = min(results, key=lambda n: results[n]["rmse_test"])
    best_model = results[best_name]["model"]
    best_rmse  = results[best_name]["rmse_test"]

    print(f"\n★ Model tốt nhất: {best_name}  (RMSE = {best_rmse:.3f}°C)")
    mlflow.set_tag("best_model", best_name)

    try:
        mlflow.sklearn.log_model(best_model, "best_model")
    except Exception:
        pass

print(f"\nMLflow run_id: {run.info.run_id if run else 'N/A'}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Lưu Predictions + Metrics + Feature Importance

# COMMAND ----------

# ── Predictions (test set) ───────────────────────────────────────────────────
pred_df = test[["city", "country", "date", "avg_temp_c", "target_next_temp"]].copy()
for name in MODELS:
    pred_df[f"pred_{name.lower().replace(' ', '_')}"] = results[name]["preds_test"]

# Thêm cột best model prediction riêng
best_col = f"pred_{best_name.lower().replace(' ', '_')}"
pred_df["pred_best"]   = pred_df[best_col]
pred_df["model_name"]  = best_name
pred_df["error"]       = (pred_df["pred_best"] - pred_df["target_next_temp"]).round(2)
pred_df["abs_error"]   = pred_df["error"].abs()
pred_df["within_1deg"] = (pred_df["abs_error"] <= 1.0).astype(int)
pred_df["within_2deg"] = (pred_df["abs_error"] <= 2.0).astype(int)

# ── Metrics table ────────────────────────────────────────────────────────────
metrics_rows = []
for name, res in results.items():
    metrics_rows.append({
        "model":       name,
        "rmse_train":  round(res["rmse_train"], 4),
        "rmse_test":   round(res["rmse_test"],  4),
        "mae_test":    round(res["mae_test"],   4),
        "r2_test":     round(res["r2_test"],    4),
        "is_best":     (name == best_name),
    })
metrics_df = pd.DataFrame(metrics_rows).sort_values("rmse_test")

# ── Feature Importance ───────────────────────────────────────────────────────
# Lấy estimator thực từ Pipeline (nếu có) để truy cập feature_importances_/coef_
best_raw = best_model.steps[-1][1] if hasattr(best_model, "steps") else best_model
if hasattr(best_raw, "feature_importances_"):
    importances = best_raw.feature_importances_
elif hasattr(best_raw, "coef_"):
    importances = np.abs(best_raw.coef_)
else:
    importances = np.zeros(len(ALL_FEATURES))

feat_imp_df = pd.DataFrame({
    "feature":    ALL_FEATURES,
    "importance": importances,
}).sort_values("importance", ascending=False).reset_index(drop=True)
feat_imp_df["rank"] = range(1, len(feat_imp_df) + 1)
feat_imp_df["importance_pct"] = (feat_imp_df["importance"] / feat_imp_df["importance"].sum() * 100).round(2)

print("Top 15 features:")
print(feat_imp_df.head(15).to_string(index=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Predict toàn bộ dataset + Forecast ngày hôm sau

# COMMAND ----------

# Predict trên toàn bộ dữ liệu (train + test) để vẽ biểu đồ
all_X = pdf_clean[ALL_FEATURES].fillna(feature_means)
pdf_clean["predicted_temp"] = best_model.predict(all_X).round(2)
pdf_clean["split"]          = "train"
pdf_clean.loc[test_mask, "split"] = "test"
pdf_clean["prediction_error"] = (pdf_clean["predicted_temp"] - pdf_clean["target_next_temp"]).round(2)

# ── Forecast ngày tiếp theo cho mỗi thành phố ────────────────────────────────
# Dùng hàng mới nhất của mỗi city để predict nhiệt độ ngày hôm sau
latest_per_city = pdf.sort_values("date").groupby("city").tail(1).copy()
latest_per_city["city_encoded"] = le.transform(latest_per_city["city"])
X_forecast = latest_per_city[ALL_FEATURES].fillna(feature_means)
latest_per_city["forecast_temp_next_day"] = best_model.predict(X_forecast).round(2)

forecast_df = latest_per_city[[
    "city", "country", "date",
    "avg_temp_c", "avg_humidity", "avg_wind_speed_kmh",
    "comfort_score", "weather_severity",
    "forecast_temp_next_day",
]].copy()
forecast_df["forecast_date"] = pd.to_datetime(forecast_df["date"]) + pd.Timedelta(days=1)
forecast_df["model_name"]    = best_name

print("\nForecast nhiệt độ ngày mai:")
print(forecast_df[["city", "avg_temp_c", "forecast_temp_next_day", "forecast_date"]].to_string(index=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Lưu vào Delta Tables

# COMMAND ----------

def save_to_delta(df_pd, table_name, mode="overwrite"):
    df_spark = spark.createDataFrame(df_pd)
    (
        df_spark.write.format("delta").mode(mode)
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )
    print(f"✓ Saved → {table_name}  ({len(df_pd)} rows)")

save_to_delta(pred_df,                                          ML_PRED_TABLE)
save_to_delta(metrics_df,                                       ML_METRICS_TABLE)
save_to_delta(feat_imp_df,                                      ML_FEATIMP_TABLE)
save_to_delta(pdf_clean[["city", "country", "date", "avg_temp_c",
                          "target_next_temp", "predicted_temp",
                          "split", "prediction_error"]],
              f"{CATALOG}.{SCHEMA}.gold_ml_full_predictions")
save_to_delta(forecast_df,                                      f"{CATALOG}.{SCHEMA}.gold_ml_forecast")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Export CSV cho Streamlit

# COMMAND ----------

def export_csv(df_pd: pd.DataFrame, filename: str):
    csv_content = df_pd.to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/{filename}", csv_content, overwrite=True)
    print(f"✓ Exported: {filename}  ({len(df_pd)} rows)")

# Predictions (test set)
export_csv(pred_df, "ml_predictions.csv")

# Model metrics
export_csv(metrics_df, "ml_metrics.csv")

# Feature importance
export_csv(feat_imp_df, "ml_feature_importance.csv")

# Full predictions (train + test) — cho chart actual vs predicted
export_csv(
    pdf_clean[["city", "country", "date", "avg_temp_c",
               "target_next_temp", "predicted_temp", "split", "prediction_error"]],
    "ml_full_predictions.csv"
)

# Forecast ngày mai
export_csv(forecast_df, "ml_forecast.csv")

# Summary report
summary = {
    "best_model":         [best_name],
    "rmse_test":          [round(best_rmse, 4)],
    "mae_test":           [round(results[best_name]["mae_test"], 4)],
    "r2_test":            [round(results[best_name]["r2_test"],  4)],
    "n_features":         [len(ALL_FEATURES)],
    "train_rows":         [len(train)],
    "test_rows":          [len(test)],
    "n_cities":           [len(pdf_clean["city"].unique())],
    "within_1deg_pct":    [round(pred_df["within_1deg"].mean() * 100, 1)],
    "within_2deg_pct":    [round(pred_df["within_2deg"].mean() * 100, 1)],
}
export_csv(pd.DataFrame(summary), "ml_summary.csv")

print(f"\n✓ Tất cả CSV tại: {EXPORT_WS_PATH}")
print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"  Best Model : {best_name}")
print(f"  RMSE Test  : {best_rmse:.3f} °C")
print(f"  MAE  Test  : {results[best_name]['mae_test']:.3f} °C")
print(f"  R²   Test  : {results[best_name]['r2_test']:.3f}")
print(f"  Within 1°C : {pred_df['within_1deg'].mean()*100:.1f}%")
print(f"  Within 2°C : {pred_df['within_2deg'].mean()*100:.1f}%")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")