# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — ML Train: Dự báo nhiệt độ ngày hôm sau
# MAGIC
# MAGIC **Pipeline:**
# MAGIC 1. Load `gold_ml_features` từ Gold layer
# MAGIC 2. Kiểm tra data đủ để train không (guard sớm, lỗi rõ ràng)
# MAGIC 3. Feature selection + fillna(mean) cho lag/rolling NaN
# MAGIC 4. Train/test split theo thời gian (80/20) — có fallback khi data ít
# MAGIC 5. Train 3 models: LinearRegression · KMeans (cluster-mean) · RandomForest
# MAGIC 6. Evaluate + chọn model tốt nhất theo RMSE
# MAGIC 7. Log vào MLflow
# MAGIC 8. Predict toàn bộ dataset + forecast ngày mai mỗi city
# MAGIC 9. Lưu Delta + export CSV cho Streamlit

# COMMAND ----------

import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
import warnings
warnings.filterwarnings("ignore")

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

GOLD_ML_TABLE    = f"{CATALOG}.{SCHEMA}.gold_ml_features"
ML_PRED_TABLE    = f"{CATALOG}.{SCHEMA}.gold_ml_predictions"
ML_METRICS_TABLE = f"{CATALOG}.{SCHEMA}.gold_ml_metrics"
ML_FEATIMP_TABLE = f"{CATALOG}.{SCHEMA}.gold_ml_feature_importance"
ML_FULLPRED_TABLE= f"{CATALOG}.{SCHEMA}.gold_ml_full_predictions"
ML_FORECAST_TABLE= f"{CATALOG}.{SCHEMA}.gold_ml_forecast"

NOTEBOOK_DIR   = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
NOTEBOOK_DIR   = "/".join(NOTEBOOK_DIR.split("/")[:-1])
EXPORT_WS_PATH = f"/Workspace{NOTEBOOK_DIR}/exports"
EXPORT_FS_PATH = f"file:{EXPORT_WS_PATH}"

dbutils.fs.mkdirs(EXPORT_FS_PATH)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Load data + Guard checks

# COMMAND ----------

# ── Load toàn bộ gold_ml_features ────────────────────────────────────────────
try:
    pdf_raw = spark.table(GOLD_ML_TABLE).toPandas()
except Exception as e:
    raise RuntimeError(
        f"Khong doc duoc {GOLD_ML_TABLE}. Hay chay 03_gold_aggregate truoc.\n{e}"
    )

print(f"gold_ml_features: {pdf_raw.shape}")
print(f"Cities: {sorted(pdf_raw['city'].unique())}")

if len(pdf_raw) == 0:
    raise ValueError(
        "gold_ml_features trong! "
        "Pipeline can chay it nhat 2 ngay lien tiep de co du lieu train."
    )

# ── Chỉ dùng hàng có target ──────────────────────────────────────────────────
pdf_raw["date"] = pd.to_datetime(pdf_raw["date"])
pdf_trainable = pdf_raw.dropna(subset=["target_next_temp"]).copy()
pdf_trainable = pdf_trainable.sort_values(["city", "date"]).reset_index(drop=True)

print(f"Rows co target_next_temp: {len(pdf_trainable)} / {len(pdf_raw)}")
print(f"Date range: {pdf_trainable['date'].min().date()} -> {pdf_trainable['date'].max().date()}")

if len(pdf_trainable) == 0:
    raise ValueError(
        "Khong co row nao co target_next_temp! "
        "Can it nhat 2 ngay du lieu lien tiep moi city. "
        "Hay chay lai pipeline sau khi co them du lieu."
    )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Feature Selection + Preprocessing

# COMMAND ----------

# Tất cả features có thể dùng (03 đã tính sẵn)
CANDIDATE_FEATURES = [
    # Thời tiết hiện tại
    "avg_temp_c", "avg_feels_like_c", "avg_humidity",
    "avg_pressure_hpa", "avg_wind_speed_kmh", "max_wind_speed_kmh",
    "avg_cloud_pct", "avg_precipitation_mm", "avg_uv_index",
    # Derived
    "temp_range", "heat_index", "comfort_score", "weather_severity",
    # Temporal
    "month_sin", "month_cos", "doy_sin", "doy_cos",
    "day_of_week", "is_weekend", "quarter",
    # Lag
    "temp_lag1", "temp_lag2", "temp_lag3", "temp_lag7",
    "humidity_lag1", "humidity_lag3",
    # Rolling
    "temp_roll_mean_3d", "temp_roll_mean_7d",
    "temp_roll_std_3d",  "temp_roll_std_7d",
    "precip_roll_sum_3d", "precip_roll_sum_7d",
]

# Chỉ dùng cột thực sự tồn tại trong data
FEATURE_COLS = [c for c in CANDIDATE_FEATURES if c in pdf_trainable.columns]
print(f"Features su dung: {len(FEATURE_COLS)}")
print(FEATURE_COLS)

# Label encode city (categorical → numeric)
le = LabelEncoder()
pdf_trainable["city_encoded"] = le.fit_transform(pdf_trainable["city"])
ALL_FEATURES = FEATURE_COLS + ["city_encoded"]

# ── Train/test split theo thời gian (80/20) ──────────────────────────────────
# Không dùng random split để giữ tính thời gian — luôn test trên data mới nhất
split_date = pd.to_datetime(pdf_trainable["date"].quantile(0.80, interpolation="nearest"))
train_mask = pdf_trainable["date"] <= split_date
test_mask  = ~train_mask

train = pdf_trainable[train_mask].copy()
test  = pdf_trainable[test_mask].copy()

# Fallback: nếu test rỗng (data quá ít), dùng 20% cuối của train làm test
if len(test) == 0:
    n_test = max(1, int(len(pdf_trainable) * 0.20))
    train  = pdf_trainable.iloc[:-n_test].copy()
    test   = pdf_trainable.iloc[-n_test:].copy()
    print(f"FALLBACK split: toan bo data <= split_date, dung {n_test} rows cuoi lam test.")

# Guard cuối: đảm bảo cả 2 set đều có data
assert len(train) > 0, "Train set rong sau split! Can them du lieu."
assert len(test)  > 0, "Test set rong sau split! Can them du lieu."

# ── Impute NaN ────────────────────────────────────────────────────────────────
# Dùng SimpleImputer thay vì fillna(mean) thủ công:
# fillna(mean) thất bại khi cột toàn NaN trong train → mean = NaN → vẫn còn NaN
# SimpleImputer xử lý cả trường hợp đó bằng cách fallback về 0
imputer = SimpleImputer(strategy="mean")
X_train_imp = imputer.fit_transform(train[ALL_FEATURES])
X_test_imp  = imputer.transform(test[ALL_FEATURES])

# Kiểm tra không còn NaN sau impute
assert not np.isnan(X_train_imp).any(), "Van con NaN trong X_train sau impute!"
assert not np.isnan(X_test_imp).any(),  "Van con NaN trong X_test sau impute!"

# ── KMeans cluster feature ────────────────────────────────────────────────────
# Thêm cluster label của KMeans (k=5) làm feature phụ cho các model
# Ý nghĩa: nhóm các thành phố/ngày có pattern thời tiết tương tự
N_CLUSTERS = min(5, len(train))   # không vượt quá số sample train
kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
kmeans.fit(X_train_imp)

cluster_train = kmeans.predict(X_train_imp).reshape(-1, 1)
cluster_test  = kmeans.predict(X_test_imp).reshape(-1, 1)

X_train = np.hstack([X_train_imp, cluster_train])
X_test  = np.hstack([X_test_imp,  cluster_test])
y_train = train["target_next_temp"].values
y_test  = test["target_next_temp"].values

print(f"\nTrain: {len(train)} rows  ({train['date'].min().date()} -> {train['date'].max().date()})")
print(f"Test : {len(test)}  rows  ({test['date'].min().date()}  -> {test['date'].max().date()})")
print(f"X_train shape: {X_train.shape} | X_test shape: {X_test.shape}")
print(f"KMeans clusters: {N_CLUSTERS}  |  cluster distribution train: {np.bincount(cluster_train.ravel())}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Train Models

# COMMAND ----------

# ── KMeans Regressor wrapper ──────────────────────────────────────────────────
# KMeans không phải regressor, nên wrap lại: fit cluster → lưu centroid target mean
# predict = mean(target) của cluster gần nhất trên train set
class KMeansRegressor:
    """Cluster-mean regressor: assign cluster, predict mean target of that cluster."""
    def __init__(self, n_clusters=8, random_state=42):
        self.n_clusters   = n_clusters
        self.random_state = random_state
        self.km           = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
        self.cluster_means_ = None

    def fit(self, X, y):
        self.km.fit(X)
        labels = self.km.labels_
        self.cluster_means_ = np.array([
            y[labels == k].mean() if (labels == k).any() else y.mean()
            for k in range(self.n_clusters)
        ])
        return self

    def predict(self, X):
        labels = self.km.predict(X)
        return self.cluster_means_[labels]

    # sklearn-compatible properties
    @property
    def feature_importances_(self):
        return None   # không có, dùng uniform fallback

MODELS = {
    # 1. Linear Regression (baseline tuyến tính)
    "LinearRegression": Pipeline([
        ("scaler", StandardScaler()),
        ("lr",     LinearRegression()),
    ]),
    # 2. KMeans Regressor (cluster-mean, non-parametric)
    "KMeans": Pipeline([
        ("scaler", StandardScaler()),
        ("km",     KMeansRegressor(n_clusters=min(8, max(2, len(train) // 10)), random_state=42)),
    ]),
    # 3. Random Forest (non-linear, bắt được tương tác phức tạp giữa features)
    "RandomForest": RandomForestRegressor(
        n_estimators=200, max_depth=10, min_samples_leaf=2,
        n_jobs=-1, random_state=42,
    ),
}

results = {}

experiment_name = "/Shared/weather-pipeline/ml_experiments"
try:
    mlflow.set_experiment(experiment_name)
except Exception:
    pass

with mlflow.start_run(run_name="weather_forecast_training") as run:
    mlflow.log_param("n_features",  len(ALL_FEATURES))
    mlflow.log_param("train_rows",  len(train))
    mlflow.log_param("test_rows",   len(test))
    mlflow.log_param("split_date",  str(split_date.date()))
    mlflow.log_param("n_cities",    len(pdf_trainable["city"].unique()))

    for name, model in MODELS.items():
        print(f"\n-- Train: {name} --")
        model.fit(X_train, y_train)

        preds_train = model.predict(X_train)
        preds_test  = model.predict(X_test)

        rmse_train = float(np.sqrt(mean_squared_error(y_train, preds_train)))
        rmse_test  = float(np.sqrt(mean_squared_error(y_test,  preds_test)))
        mae_test   = float(mean_absolute_error(y_test, preds_test))
        # r2 không xác định khi test chỉ có 1 mẫu
        r2_test    = float(r2_score(y_test, preds_test)) if len(y_test) > 1 else float("nan")

        print(f"  RMSE train : {rmse_train:.3f}C")
        print(f"  RMSE test  : {rmse_test:.3f}C")
        print(f"  MAE  test  : {mae_test:.3f}C")
        print(f"  R2   test  : {r2_test:.3f}" if not np.isnan(r2_test) else "  R2   test  : N/A (1 sample)")

        mlflow.log_metrics({
            f"{name}_rmse_train": rmse_train,
            f"{name}_rmse_test":  rmse_test,
            f"{name}_mae_test":   mae_test,
            f"{name}_r2_test":    r2_test if not np.isnan(r2_test) else -999,
        })

        results[name] = {
            "model":      model,
            "rmse_train": rmse_train,
            "rmse_test":  rmse_test,
            "mae_test":   mae_test,
            "r2_test":    r2_test,
            "preds_test": preds_test,
        }

    # Chọn best model theo RMSE test
    best_name  = min(results, key=lambda n: results[n]["rmse_test"])
    best_model = results[best_name]["model"]
    best_rmse  = results[best_name]["rmse_test"]

    print(f"\n*** Best model: {best_name}  (RMSE = {best_rmse:.3f}C) ***")
    mlflow.set_tag("best_model", best_name)
    try:
        mlflow.sklearn.log_model(best_model, "best_model")
    except Exception:
        pass

print(f"\nMLflow run_id: {run.info.run_id}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Feature Importance + Metrics tables

# COMMAND ----------

# ── Metrics ──────────────────────────────────────────────────────────────────
metrics_rows = []
for name, res in results.items():
    metrics_rows.append({
        "model":      name,
        "rmse_train": round(res["rmse_train"], 4),
        "rmse_test":  round(res["rmse_test"],  4),
        "mae_test":   round(res["mae_test"],   4),
        "r2_test":    round(res["r2_test"],    4) if not np.isnan(res["r2_test"]) else None,
        "is_best":    (name == best_name),
    })
metrics_df = pd.DataFrame(metrics_rows).sort_values("rmse_test").reset_index(drop=True)
print("Model metrics:")
print(metrics_df.to_string(index=False))

# ── Feature importance ────────────────────────────────────────────────────────
# ALL_FEATURES + "kmeans_cluster" là toàn bộ features thực sự đưa vào model
FINAL_FEATURE_NAMES = ALL_FEATURES + ["kmeans_cluster"]

best_raw = best_model
# Nếu là Pipeline, lấy step cuối
if hasattr(best_model, "steps"):
    best_raw = best_model.steps[-1][1]

if hasattr(best_raw, "feature_importances_") and best_raw.feature_importances_ is not None:
    importances = best_raw.feature_importances_
elif hasattr(best_raw, "coef_"):
    importances = np.abs(best_raw.coef_).flatten()  # flatten để đảm bảo 1D
else:
    importances = np.ones(len(FINAL_FEATURE_NAMES)) / len(FINAL_FEATURE_NAMES)

# Guard: đảm bảo độ dài khớp với FINAL_FEATURE_NAMES
if len(importances) != len(FINAL_FEATURE_NAMES):
    print(f"[WARN] importance length {len(importances)} != feature count {len(FINAL_FEATURE_NAMES)}, dùng uniform fallback")
    importances = np.ones(len(FINAL_FEATURE_NAMES)) / len(FINAL_FEATURE_NAMES)

feat_imp_df = (
    pd.DataFrame({"feature": FINAL_FEATURE_NAMES, "importance": importances})
    .sort_values("importance", ascending=False)
    .reset_index(drop=True)
)
feat_imp_df["rank"] = range(1, len(feat_imp_df) + 1)
total_imp = feat_imp_df["importance"].sum()
feat_imp_df["importance_pct"] = (feat_imp_df["importance"] / total_imp * 100).round(2) if total_imp > 0 else 0.0

print("\nTop 15 features:")
print(feat_imp_df.head(15).to_string(index=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Predict toàn bộ dataset + Forecast ngày mai

# COMMAND ----------

# ── Full predictions (train + test) — dùng cho chart Actual vs Predicted ─────
all_X_imp = imputer.transform(pdf_trainable[ALL_FEATURES])
all_cluster = kmeans.predict(all_X_imp).reshape(-1, 1)
all_X_final = np.hstack([all_X_imp, all_cluster])

pdf_trainable["predicted_temp"]   = best_model.predict(all_X_final).round(2)
pdf_trainable["split"]            = "train"
# Gán split label đúng theo vị trí index
test_indices = test.index
pdf_trainable.loc[pdf_trainable.index.isin(test_indices), "split"] = "test"
pdf_trainable["prediction_error"] = (
    pdf_trainable["predicted_temp"] - pdf_trainable["target_next_temp"]
).round(2)

# ── Test set predictions — dùng cho metrics chi tiết ─────────────────────────
pred_df = test[["city", "country", "date", "avg_temp_c", "target_next_temp"]].copy()
for name in MODELS:
    col = f"pred_{name.lower().replace(' ', '_')}"
    pred_df[col] = results[name]["preds_test"]

best_col = f"pred_{best_name.lower().replace(' ', '_')}"
pred_df["pred_best"]   = pred_df[best_col]
pred_df["model_name"]  = best_name
pred_df["error"]       = (pred_df["pred_best"] - pred_df["target_next_temp"]).round(2)
pred_df["abs_error"]   = pred_df["error"].abs()
pred_df["within_1deg"] = (pred_df["abs_error"] <= 1.0).astype(int)
pred_df["within_2deg"] = (pred_df["abs_error"] <= 2.0).astype(int)

# ── Forecast ngày mai cho mỗi city ───────────────────────────────────────────
# Dùng hàng mới nhất (kể cả hàng không có target) của mỗi city
latest_rows = pdf_raw.sort_values("date").groupby("city").tail(1).copy()
latest_rows["city_encoded"] = le.transform(latest_rows["city"])

X_fc_imp     = imputer.transform(latest_rows[ALL_FEATURES])
X_fc_cluster = kmeans.predict(X_fc_imp).reshape(-1, 1)
X_fc_final   = np.hstack([X_fc_imp, X_fc_cluster])

latest_rows["forecast_temp_next_day"] = best_model.predict(X_fc_final).round(2)

forecast_df = latest_rows[[
    "city", "country", "date",
    "avg_temp_c", "avg_humidity", "avg_wind_speed_kmh",
    "comfort_score", "weather_severity",
    "forecast_temp_next_day",
]].copy()
forecast_df["forecast_date"] = pd.to_datetime(forecast_df["date"]) + pd.Timedelta(days=1)
forecast_df["model_name"]    = best_name

print("Forecast nhiet do ngay mai:")
print(forecast_df[["city", "avg_temp_c", "forecast_temp_next_day", "forecast_date"]].to_string(index=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Lưu vào Delta Tables

# COMMAND ----------

def save_to_delta(df_pd: pd.DataFrame, table_name: str):
    (
        spark.createDataFrame(df_pd)
        .write.format("delta").mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name)
    )
    print(f"  Saved -> {table_name}  ({len(df_pd)} rows)")

print("=== Saving Delta tables ===")
save_to_delta(pred_df,    ML_PRED_TABLE)
save_to_delta(metrics_df, ML_METRICS_TABLE)
save_to_delta(feat_imp_df,ML_FEATIMP_TABLE)
save_to_delta(
    pdf_trainable[[
        "city", "country", "date", "avg_temp_c",
        "target_next_temp", "predicted_temp",
        "split", "prediction_error",
    ]],
    ML_FULLPRED_TABLE,
)
save_to_delta(forecast_df, ML_FORECAST_TABLE)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. Export CSV cho Streamlit

# COMMAND ----------

def export_csv(df_pd: pd.DataFrame, filename: str):
    csv_str = df_pd.to_csv(index=False)
    dbutils.fs.put(f"{EXPORT_FS_PATH}/{filename}", csv_str, overwrite=True)
    print(f"  OK   {filename}  ({len(df_pd)} rows)")

# Summary — Streamlit ML Insights KPI cards
within_1 = pred_df["within_1deg"].mean() * 100
within_2 = pred_df["within_2deg"].mean() * 100
summary_df = pd.DataFrame([{
    "best_model":      best_name,
    "rmse_test":       round(best_rmse, 4),
    "mae_test":        round(results[best_name]["mae_test"],  4),
    "r2_test":         round(results[best_name]["r2_test"],   4) if not np.isnan(results[best_name]["r2_test"]) else None,
    "n_features":      len(ALL_FEATURES),
    "train_rows":      len(train),
    "test_rows":       len(test),
    "n_cities":        len(pdf_trainable["city"].unique()),
    "within_1deg_pct": round(within_1, 1),
    "within_2deg_pct": round(within_2, 1),
}])

print("=== Exporting CSVs ===")
export_csv(summary_df,  "ml_summary.csv")
export_csv(metrics_df,  "ml_metrics.csv")
export_csv(feat_imp_df, "ml_feature_importance.csv")
export_csv(pred_df,     "ml_predictions.csv")
export_csv(
    pdf_trainable[[
        "city", "country", "date", "avg_temp_c",
        "target_next_temp", "predicted_temp",
        "split", "prediction_error",
    ]],
    "ml_full_predictions.csv",
)
export_csv(forecast_df, "ml_forecast.csv")

# COMMAND ----------

print(f"\nTat ca CSV tai: {EXPORT_WS_PATH}")
print("\n" + "=" * 50)
print(f"  Best Model  : {best_name}")
print(f"  RMSE Test   : {best_rmse:.3f} C")
print(f"  MAE  Test   : {results[best_name]['mae_test']:.3f} C")
r2_disp = f"{results[best_name]['r2_test']:.3f}" if not np.isnan(results[best_name]["r2_test"]) else "N/A"
print(f"  R2   Test   : {r2_disp}")
print(f"  Within 1C   : {within_1:.1f}%")
print(f"  Within 2C   : {within_2:.1f}%")
print(f"  Train rows  : {len(train)}")
print(f"  Test  rows  : {len(test)}")
print("=" * 50)