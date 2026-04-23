# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — ML: Weather Forecast Model — Dự đoán thời tiết tương lai
# MAGIC
# MAGIC **Mô hình dự báo nhiệt độ (và điều kiện thời tiết) cho ngày mai hoặc N ngày tới**
# MAGIC bằng Machine Learning thuần (không dùng Deep Learning).
# MAGIC
# MAGIC ### Pipeline ML:
# MAGIC ```
# MAGIC Data (Gold/Silver) → Feature Engineering → Model Selection → Hyperparameter Tuning
# MAGIC     → MLflow Tracking → Best Model Registry → Prediction Function
# MAGIC ```
# MAGIC
# MAGIC ### Các mô hình so sánh:
# MAGIC | Model | Đặc điểm |
# MAGIC |-------|----------|
# MAGIC | Ridge Regression | Baseline, nhanh, giải thích được |
# MAGIC | Random Forest | Robust, xử lý non-linear tốt |
# MAGIC | Gradient Boosting | Thường tốt nhất cho tabular data |
# MAGIC | XGBoost | Mạnh, có built-in regularization |
# MAGIC | Extra Trees | Nhanh, ít overfit hơn RF |
# MAGIC | Voting Ensemble | Kết hợp các model tốt nhất |

# COMMAND ----------

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta

from sklearn.ensemble import (
    RandomForestRegressor, GradientBoostingRegressor,
    ExtraTreesRegressor, VotingRegressor
)
from sklearn.linear_model import Ridge
from sklearn.model_selection import (
    train_test_split, cross_val_score,
    GridSearchCV, KFold
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("⚠️  XGBoost không có sẵn, bỏ qua")

warnings.filterwarnings("ignore")

CATALOG = "workspace"
SCHEMA  = "weather_pipeline"

GOLD_DAILY_TABLE  = f"{CATALOG}.{SCHEMA}.gold_weather_daily"
SILVER_TABLE      = f"{CATALOG}.{SCHEMA}.silver_weather_clean"

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Load & kiểm tra data

# COMMAND ----------

df_gold = spark.table(GOLD_DAILY_TABLE).toPandas()
df_silver = spark.table(SILVER_TABLE).toPandas()

print(f"Gold daily rows  : {len(df_gold)}")
print(f"Silver rows      : {len(df_silver)}")
print(f"Thành phố (Gold) : {df_gold['city'].nunique() if len(df_gold) > 0 else 0}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Feature Engineering — xây dựng features dự đoán tương lai

# COMMAND ----------

def build_features(df_gold: pd.DataFrame, df_silver: pd.DataFrame) -> pd.DataFrame:
    """
    Xây dựng feature matrix có thể dùng để dự đoán temp_max/temp_min
    của ngày T+1 (ngày mai) hoặc T+N.

    Strategy:
    - Nếu Gold có đủ data (≥ 30 rows): dùng Gold với lag features + rolling stats
    - Nếu ít data: dùng Silver (per-reading) với temporal features
    - Luôn tạo đủ features để predict ngày tương lai
    """

    if len(df_gold) >= 15:
        print("→ Dùng Gold daily data với lag features")
        df = df_gold.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["city", "date"]).reset_index(drop=True)

        le = LabelEncoder()
        df["city_enc"] = le.fit_transform(df["city"])

        # Temporal features
        df["month"]        = df["date"].dt.month
        df["day_of_year"]  = df["date"].dt.dayofyear
        df["day_of_week"]  = df["date"].dt.dayofweek
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["quarter"]      = df["date"].dt.quarter
        df["is_weekend"]   = (df["day_of_week"] >= 5).astype(int)

        # Seasonal encoding (sin/cos để capture tính tuần hoàn)
        df["month_sin"]      = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"]      = np.cos(2 * np.pi * df["month"] / 12)
        df["doy_sin"]        = np.sin(2 * np.pi * df["day_of_year"] / 365)
        df["doy_cos"]        = np.cos(2 * np.pi * df["day_of_year"] / 365)

        # Lag features (giá trị của N ngày trước — per city)
        for lag in [1, 2, 3, 7]:
            df[f"temp_max_lag{lag}"] = df.groupby("city")["avg_temp_c"].shift(lag)
            df[f"humidity_lag{lag}"] = df.groupby("city")["avg_humidity"].shift(lag)

        # Rolling statistics (trung bình & độ lệch chuẩn 3, 7 ngày gần nhất)
        for window in [3, 7]:
            df[f"temp_roll_mean_{window}d"] = (
                df.groupby("city")["avg_temp_c"]
                  .transform(lambda x: x.shift(1).rolling(window, min_periods=1).mean())
            )
            df[f"temp_roll_std_{window}d"] = (
                df.groupby("city")["avg_temp_c"]
                  .transform(lambda x: x.shift(1).rolling(window, min_periods=1).std())
            )
            df[f"precip_roll_sum_{window}d"] = (
                df.groupby("city")["avg_precip_sum_mm" if "avg_precip_sum_mm" in df.columns else "avg_temp_c"]
                  .transform(lambda x: x.shift(1).rolling(window, min_periods=1).sum())
            )

        # Temp range hôm qua
        if "avg_temp_max_c" in df.columns and "avg_temp_min_c" in df.columns:
            df["temp_range"]       = df["avg_temp_max_c"] - df["avg_temp_min_c"]
            df["temp_range_lag1"]  = df.groupby("city")["temp_range"].shift(1)

        FEATURES = [
            "city_enc", "month", "day_of_year", "day_of_week", "week_of_year",
            "quarter", "is_weekend",
            "month_sin", "month_cos", "doy_sin", "doy_cos",
            "avg_humidity", "avg_pressure_hpa", "avg_wind_speed_kmh",
            "avg_cloud_pct", "avg_uv_index",
            "temp_max_lag1", "temp_max_lag2", "temp_max_lag3", "temp_max_lag7",
            "humidity_lag1", "humidity_lag2",
            "temp_roll_mean_3d", "temp_roll_mean_7d",
            "temp_roll_std_3d",
        ]

        # Chỉ giữ features tồn tại
        FEATURES = [f for f in FEATURES if f in df.columns]
        TARGET   = "avg_temp_c"
        source   = "gold"

    else:
        print(f"→ Gold chỉ có {len(df_gold)} rows — dùng Silver data")
        df = df_silver.copy()
        df["crawled_at"] = pd.to_datetime(df["crawled_at"])
        df = df.sort_values(["city", "crawled_at"]).reset_index(drop=True)

        le = LabelEncoder()
        df["city_enc"] = le.fit_transform(df["city"])

        df["month"]       = df["crawled_at"].dt.month
        df["day_of_year"] = df["crawled_at"].dt.dayofyear
        df["day_of_week"] = df["crawled_at"].dt.dayofweek
        df["hour"]        = df["crawled_at"].dt.hour
        df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)

        df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)
        df["doy_sin"]     = np.sin(2 * np.pi * df["day_of_year"] / 365)
        df["doy_cos"]     = np.cos(2 * np.pi * df["day_of_year"] / 365)
        df["hour_sin"]    = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"]    = np.cos(2 * np.pi * df["hour"] / 24)

        # Lag features (per-reading)
        for lag in [1, 2, 3]:
            df[f"temp_lag{lag}"]     = df.groupby("city")["temperature_c"].shift(lag)
            df[f"humidity_lag{lag}"] = df.groupby("city")["humidity"].shift(lag)

        FEATURES = [
            "city_enc", "month", "day_of_year", "day_of_week", "hour",
            "is_weekend", "month_sin", "month_cos", "doy_sin", "doy_cos",
            "hour_sin", "hour_cos",
            "humidity", "pressure_hpa", "wind_speed_kmh",
            "cloud_cover_pct", "uv_index",
            "temp_lag1", "temp_lag2",
            "humidity_lag1",
        ]

        FEATURES = [f for f in FEATURES if f in df.columns]
        TARGET   = "temperature_c"
        source   = "silver"

    df_clean = df.dropna(subset=FEATURES + [TARGET])
    print(f"→ {len(df_clean)} rows sạch / {len(df)} rows tổng (source={source})")

    return df_clean, FEATURES, TARGET, le, source


df_model, FEATURES, TARGET, label_encoder, data_source = build_features(df_gold, df_silver)

print(f"\nFeatures ({len(FEATURES)}):")
for f in FEATURES:
    print(f"  - {f}")
print(f"\nTarget: {TARGET}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Train/Test Split

# COMMAND ----------

X = df_model[FEATURES]
y = df_model[TARGET]

n = len(df_model)

if n < 4:
    # Quá ít data — không thể CV, chỉ fit & predict trên toàn bộ
    print(f"⚠️  Chỉ có {n} records — bỏ qua CV, train trên toàn bộ data")
    print("→ Crawl thêm nhiều ngày để model có ý nghĩa hơn")
    X_train, X_test = X, X
    y_train, y_test = y, y
    use_cv = False
    CV_FOLDS = 2   # placeholder, sẽ không dùng khi use_cv=False
elif n < 10:
    print(f"⚠️  Chỉ có {n} records — pipeline chạy nhưng metrics chưa đại diện")
    print("→ Crawl thêm nhiều ngày để model có ý nghĩa hơn")
    X_train, X_test = X, X
    y_train, y_test = y, y
    use_cv = True
    CV_FOLDS = max(2, min(3, n))   # đảm bảo CV_FOLDS ≥ 2
elif n < 30:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    use_cv = True
    CV_FOLDS = 3
    print(f"→ {n} rows — dùng 3-fold CV để đánh giá ổn định hơn")
else:
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    use_cv = True
    CV_FOLDS = 5
    print(f"→ {n} rows — 5-fold cross-validation")

print(f"Train: {len(X_train)}  |  Test: {len(X_test)}  |  CV folds: {CV_FOLDS}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Định nghĩa Models với Hyperparameter Tuning

# COMMAND ----------

# Imputer để xử lý NaN còn sót
imputer = SimpleImputer(strategy="median")

def make_pipeline(model):
    """Wrap model trong Pipeline với imputer."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", model),
    ])


# Định nghĩa model + grid search params
MODELS = {
    "Ridge": {
        "pipeline": make_pipeline(Ridge()),
        "param_grid": {
            "model__alpha": [0.1, 1.0, 10.0, 100.0],
        },
    },
    "RandomForest": {
        "pipeline": make_pipeline(
            RandomForestRegressor(random_state=42, n_jobs=-1)
        ),
        "param_grid": {
            "model__n_estimators": [100, 200],
            "model__max_depth": [None, 10, 20],
            "model__min_samples_split": [2, 5],
            "model__max_features": ["sqrt", "log2"],
        },
    },
    "GradientBoosting": {
        "pipeline": make_pipeline(
            GradientBoostingRegressor(random_state=42)
        ),
        "param_grid": {
            "model__n_estimators": [100, 200],
            "model__learning_rate": [0.05, 0.1, 0.2],
            "model__max_depth": [3, 5, 7],
            "model__subsample": [0.8, 1.0],
        },
    },
    "ExtraTrees": {
        "pipeline": make_pipeline(
            ExtraTreesRegressor(random_state=42, n_jobs=-1)
        ),
        "param_grid": {
            "model__n_estimators": [100, 200],
            "model__max_depth": [None, 15],
            "model__min_samples_split": [2, 5],
        },
    },
}

if HAS_XGBOOST:
    MODELS["XGBoost"] = {
        "pipeline": make_pipeline(
            XGBRegressor(
                random_state=42, n_jobs=-1,
                eval_metric="rmse", verbosity=0,
                tree_method="hist",
            )
        ),
        "param_grid": {
            "model__n_estimators": [100, 200],
            "model__learning_rate": [0.05, 0.1],
            "model__max_depth": [3, 5, 7],
            "model__subsample": [0.8, 1.0],
            "model__colsample_bytree": [0.8, 1.0],
            "model__reg_alpha": [0, 0.1],
        },
    }

print(f"Sẽ train & tune {len(MODELS)} models: {list(MODELS.keys())}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 5. Train với GridSearchCV + MLflow tracking

# COMMAND ----------

mlflow.set_experiment("/Shared/weather_forecast")

# CV_FOLDS phải ≥ 2 — guard cuối cùng trước khi tạo KFold
CV_FOLDS = max(2, CV_FOLDS)
kfold = KFold(n_splits=CV_FOLDS, shuffle=True, random_state=42) if use_cv else None

results = {}  # lưu kết quả để so sánh
best_estimators = {}  # lưu fitted model tốt nhất của mỗi loại

for name, cfg in MODELS.items():
    print(f"\n{'='*55}")
    print(f"  Training: {name}")
    print(f"{'='*55}")

    with mlflow.start_run(run_name=name):
        param_grid = cfg["param_grid"]
        # Khi data ít → rút gọn grid để tránh timeout
        if len(X_train) < 20:
            param_grid = {k: v[:1] for k, v in param_grid.items()}

        if use_cv and kfold is not None:
            # Có đủ data → dùng GridSearchCV
            gs = GridSearchCV(
                cfg["pipeline"],
                param_grid,
                cv=kfold,
                scoring="neg_mean_absolute_error",
                n_jobs=-1,
                refit=True,
                verbose=0,
            )
            gs.fit(X_train, y_train)
            best_model  = gs.best_estimator_
            best_params = gs.best_params_
        else:
            # Quá ít data → fit trực tiếp với params mặc định
            print(f"  ⚠️  Data quá ít ({len(X_train)} rows) — bỏ qua GridSearch, fit trực tiếp")
            best_model  = cfg["pipeline"]
            best_params = {}
            best_model.fit(X_train, y_train)

        # Đánh giá trên test set
        preds      = best_model.predict(X_test)
        mae        = mean_absolute_error(y_test, preds)
        rmse       = np.sqrt(mean_squared_error(y_test, preds))
        r2         = r2_score(y_test, preds)

        # Cross-validation score (stability measure) — chỉ khi use_cv
        if use_cv and kfold is not None:
            cv_scores   = cross_val_score(best_model, X, y, cv=kfold,
                                          scoring="neg_mean_absolute_error")
            cv_mae_mean = -cv_scores.mean()
            cv_mae_std  = cv_scores.std()
        else:
            cv_mae_mean = mae
            cv_mae_std  = 0.0

        # Feature importance (nếu model hỗ trợ)
        inner_model = best_model.named_steps["model"]
        fi_dict = {}
        if hasattr(inner_model, "feature_importances_"):
            fi = inner_model.feature_importances_
            fi_dict = dict(zip(FEATURES, fi.tolist()))
            top5 = sorted(fi_dict.items(), key=lambda x: -x[1])[:5]
            print(f"  Top-5 features: {top5}")
        elif hasattr(inner_model, "coef_"):
            coef = np.abs(inner_model.coef_)
            fi_dict = dict(zip(FEATURES, coef.tolist()))

        # MLflow logging
        mlflow.log_params(best_params)
        mlflow.log_param("model_type",  name)
        mlflow.log_param("features",    FEATURES)
        mlflow.log_param("n_train",     len(X_train))
        mlflow.log_param("n_test",      len(X_test))
        mlflow.log_param("cv_folds",    CV_FOLDS if use_cv else "N/A")
        mlflow.log_param("data_source", data_source)

        mlflow.log_metric("mae",         mae)
        mlflow.log_metric("rmse",        rmse)
        mlflow.log_metric("r2",          r2)
        mlflow.log_metric("cv_mae_mean", cv_mae_mean)
        mlflow.log_metric("cv_mae_std",  cv_mae_std)

        if fi_dict:
            mlflow.log_dict(fi_dict, "feature_importance.json")

        mlflow.sklearn.log_model(
            best_model,
            artifact_path="model",
            registered_model_name=f"weather_forecast_{name.lower()}",
        )

        results[name] = {
            "model": best_model,
            "mae": mae, "rmse": rmse, "r2": r2,
            "cv_mae_mean": cv_mae_mean, "cv_mae_std": cv_mae_std,
            "best_params": best_params,
        }
        best_estimators[name] = best_model

        print(f"  MAE={mae:.2f}°C  RMSE={rmse:.2f}°C  R²={r2:.3f}")
        print(f"  CV MAE={cv_mae_mean:.2f}°C ± {cv_mae_std:.2f}  (best params: {best_params})")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 6. Tạo Voting Ensemble từ top-3 models

# COMMAND ----------

# Chọn top-3 model theo MAE thấp nhất
sorted_models = sorted(results.items(), key=lambda x: x[1]["mae"])
top3 = sorted_models[:3]
print(f"Top-3 models: {[m[0] for m in top3]}")

ensemble = VotingRegressor(
    estimators=[(name, best_estimators[name]) for name, _ in top3]
)
ensemble_pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("ensemble", ensemble),
])

# Fit ensemble (các base models đã được fit, nhưng VotingRegressor cần fit lại)
ensemble_pipeline.fit(X_train, y_train)

with mlflow.start_run(run_name="VotingEnsemble"):
    preds_ens = ensemble_pipeline.predict(X_test)
    mae_ens   = mean_absolute_error(y_test, preds_ens)
    rmse_ens  = np.sqrt(mean_squared_error(y_test, preds_ens))
    r2_ens    = r2_score(y_test, preds_ens)

    if use_cv and kfold is not None:
        cv_ens      = cross_val_score(ensemble_pipeline, X, y, cv=kfold,
                                      scoring="neg_mean_absolute_error")
        cv_ens_mean = -cv_ens.mean()
        cv_ens_std  = cv_ens.std()
    else:
        cv_ens_mean = mae_ens
        cv_ens_std  = 0.0

    mlflow.log_param("model_type",    "VotingEnsemble")
    mlflow.log_param("base_models",   [m[0] for m in top3])
    mlflow.log_param("data_source",   data_source)
    mlflow.log_metric("mae",          mae_ens)
    mlflow.log_metric("rmse",         rmse_ens)
    mlflow.log_metric("r2",           r2_ens)
    mlflow.log_metric("cv_mae_mean",  cv_ens_mean)
    mlflow.log_metric("cv_mae_std",   cv_ens_std)
    mlflow.sklearn.log_model(
        ensemble_pipeline,
        artifact_path="model",
        registered_model_name="weather_forecast_ensemble",
    )
    print(f"\nVotingEnsemble: MAE={mae_ens:.2f}°C  RMSE={rmse_ens:.2f}°C  R²={r2_ens:.3f}")

results["VotingEnsemble"] = {
    "model": ensemble_pipeline, "mae": mae_ens, "rmse": rmse_ens, "r2": r2_ens,
    "cv_mae_mean": cv_ens_mean, "cv_mae_std": cv_ens_std,
    "best_params": {"base_models": [m[0] for m in top3]},
}
best_estimators["VotingEnsemble"] = ensemble_pipeline

# COMMAND ----------
# MAGIC %md
# MAGIC ## 7. So sánh tất cả models

# COMMAND ----------

print("\n" + "="*70)
print(f"{'Model':<20} {'MAE':>8} {'RMSE':>8} {'R²':>7} {'CV MAE':>10} {'CV±':>8}")
print("="*70)

sorted_all = sorted(results.items(), key=lambda x: x[1]["mae"])
for name, m in sorted_all:
    marker = " ← BEST" if name == sorted_all[0][0] else ""
    print(
        f"{name:<20} {m['mae']:>7.2f}°C {m['rmse']:>7.2f}°C "
        f"{m['r2']:>6.3f}  {m['cv_mae_mean']:>8.2f}°C {m['cv_mae_std']:>7.2f}{marker}"
    )

best_name  = sorted_all[0][0]
best_model = results[best_name]["model"]
print(f"\n✓ Model tốt nhất: {best_name} (MAE={results[best_name]['mae']:.2f}°C)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 8. Dự đoán thời tiết tương lai cho bất kỳ thành phố nào
# MAGIC
# MAGIC ### Cách dùng:
# MAGIC ```python
# MAGIC predict_future_weather("Ho Chi Minh City", days_ahead=1)   # ngày mai
# MAGIC predict_future_weather("Tokyo", days_ahead=3)              # 3 ngày tới
# MAGIC predict_future_weather("London", days_ahead=7)             # 1 tuần tới
# MAGIC ```

# COMMAND ----------

# Lấy thống kê lịch sử của từng thành phố để làm input dự đoán
def get_city_baseline(city_name: str, df_gold: pd.DataFrame, df_silver: pd.DataFrame) -> dict:
    """
    Lấy các giá trị hiện tại/gần nhất của thành phố làm baseline features.
    """
    # Thử Gold trước
    if len(df_gold) > 0:
        city_data = df_gold[df_gold["city"] == city_name].sort_values("date", ascending=False)
        if len(city_data) > 0:
            latest = city_data.iloc[0]
            return {
                "avg_humidity":       latest.get("avg_humidity", 70),
                "avg_pressure_hpa":   latest.get("avg_pressure_hpa", 1013),
                "avg_wind_speed_kmh": latest.get("avg_wind_speed_kmh", 15),
                "avg_cloud_pct":      latest.get("avg_cloud_pct", 50),
                "avg_uv_index":       latest.get("avg_uv_index", 5),
                "avg_temp_c":         latest.get("avg_temp_c", 25),
                "recent_temps":       city_data["avg_temp_c"].head(7).tolist(),
            }

    # Fallback Silver
    if len(df_silver) > 0:
        city_data = df_silver[df_silver["city"] == city_name].sort_values("crawled_at", ascending=False)
        if len(city_data) > 0:
            latest = city_data.iloc[0]
            return {
                "avg_humidity":       latest.get("humidity", 70),
                "avg_pressure_hpa":   latest.get("pressure_hpa", 1013),
                "avg_wind_speed_kmh": latest.get("wind_speed_kmh", 15),
                "avg_cloud_pct":      latest.get("cloud_cover_pct", 50),
                "avg_uv_index":       latest.get("uv_index", 5),
                "avg_temp_c":         latest.get("temperature_c", 25),
                "recent_temps":       city_data["temperature_c"].head(7).tolist(),
            }

    print(f"⚠️  Không tìm thấy data cho {city_name}, dùng giá trị mặc định")
    return {
        "avg_humidity": 70, "avg_pressure_hpa": 1013,
        "avg_wind_speed_kmh": 15, "avg_cloud_pct": 50,
        "avg_uv_index": 5, "avg_temp_c": 25, "recent_temps": [25],
    }


def predict_future_weather(
    city_name: str,
    days_ahead: int = 1,
    model=None,
    features: list = None,
    le: LabelEncoder = None,
) -> dict:
    """
    Dự đoán nhiệt độ (và ước tính điều kiện thời tiết) cho thành phố
    vào N ngày tới.

    Parameters
    ----------
    city_name  : Tên thành phố (phải có trong training data)
    days_ahead : Số ngày tới cần dự đoán (1 = ngày mai, 7 = 1 tuần tới)

    Returns
    -------
    dict: {city, target_date, days_ahead, predicted_temp_c, confidence_range, ...}
    """
    if model is None:
        model = best_model
    if features is None:
        features = FEATURES
    if le is None:
        le = label_encoder

    # Kiểm tra thành phố có trong encoder không
    known_cities = list(le.classes_)
    if city_name not in known_cities:
        print(f"⚠️  '{city_name}' chưa có trong training data.")
        print(f"   Các thành phố đã biết: {known_cities}")
        return None

    baseline = get_city_baseline(city_name, df_gold, df_silver)
    target_date = datetime.now() + timedelta(days=days_ahead)

    # Build feature row cho ngày target
    row = {
        "city_enc":           le.transform([city_name])[0],
        "month":              target_date.month,
        "day_of_year":        target_date.timetuple().tm_yday,
        "day_of_week":        target_date.weekday(),
        "week_of_year":       target_date.isocalendar()[1],
        "quarter":            (target_date.month - 1) // 3 + 1,
        "is_weekend":         int(target_date.weekday() >= 5),
        "month_sin":          np.sin(2 * np.pi * target_date.month / 12),
        "month_cos":          np.cos(2 * np.pi * target_date.month / 12),
        "doy_sin":            np.sin(2 * np.pi * target_date.timetuple().tm_yday / 365),
        "doy_cos":            np.cos(2 * np.pi * target_date.timetuple().tm_yday / 365),
        "hour_sin":           0.0,
        "hour_cos":           1.0,
        "hour":               12,

        # Weather condition features (dùng latest)
        "avg_humidity":       baseline["avg_humidity"],
        "humidity":           baseline["avg_humidity"],
        "avg_pressure_hpa":   baseline["avg_pressure_hpa"],
        "pressure_hpa":       baseline["avg_pressure_hpa"],
        "avg_wind_speed_kmh": baseline["avg_wind_speed_kmh"],
        "wind_speed_kmh":     baseline["avg_wind_speed_kmh"],
        "avg_cloud_pct":      baseline["avg_cloud_pct"],
        "cloud_cover_pct":    baseline["avg_cloud_pct"],
        "avg_uv_index":       baseline["avg_uv_index"],
        "uv_index":           baseline["avg_uv_index"],

        # Lag features (dùng recent temps)
        "temp_max_lag1":      baseline["recent_temps"][0] if len(baseline["recent_temps"]) > 0 else baseline["avg_temp_c"],
        "temp_max_lag2":      baseline["recent_temps"][1] if len(baseline["recent_temps"]) > 1 else baseline["avg_temp_c"],
        "temp_max_lag3":      baseline["recent_temps"][2] if len(baseline["recent_temps"]) > 2 else baseline["avg_temp_c"],
        "temp_max_lag7":      baseline["recent_temps"][-1] if len(baseline["recent_temps"]) > 0 else baseline["avg_temp_c"],
        "temp_lag1":          baseline["recent_temps"][0] if len(baseline["recent_temps"]) > 0 else baseline["avg_temp_c"],
        "temp_lag2":          baseline["recent_temps"][1] if len(baseline["recent_temps"]) > 1 else baseline["avg_temp_c"],
        "temp_lag3":          baseline["recent_temps"][2] if len(baseline["recent_temps"]) > 2 else baseline["avg_temp_c"],
        "humidity_lag1":      baseline["avg_humidity"],
        "humidity_lag2":      baseline["avg_humidity"],

        # Rolling features (ước tính từ recent)
        "temp_roll_mean_3d":  np.mean(baseline["recent_temps"][:3]) if len(baseline["recent_temps"]) >= 3 else baseline["avg_temp_c"],
        "temp_roll_mean_7d":  np.mean(baseline["recent_temps"]) if baseline["recent_temps"] else baseline["avg_temp_c"],
        "temp_roll_std_3d":   np.std(baseline["recent_temps"][:3]) if len(baseline["recent_temps"]) >= 3 else 1.0,
        "precip_roll_sum_3d": 0.0,
        "precip_roll_sum_7d": 0.0,
        "temp_range":         5.0,
        "temp_range_lag1":    5.0,
    }

    X_pred = pd.DataFrame([{f: row.get(f, 0) for f in features}])
    pred_temp = model.predict(X_pred)[0]

    # Ước tính khoảng tin cậy dựa trên MAE của model
    model_mae = results[best_name]["mae"]
    # Uncertainty tăng theo số ngày dự đoán (±10% mỗi ngày thêm)
    uncertainty_factor = 1 + (days_ahead - 1) * 0.1
    confidence_margin  = model_mae * uncertainty_factor

    # Ước tính điều kiện thời tiết đơn giản từ nhiệt độ & cloud cover
    cloud = baseline["avg_cloud_pct"]
    if cloud < 20:
        weather_cond = "Nắng đẹp ☀️"
    elif cloud < 50:
        weather_cond = "Ít mây 🌤️"
    elif cloud < 80:
        weather_cond = "Nhiều mây ⛅"
    else:
        weather_cond = "Có thể mưa 🌧️"

    result = {
        "city":            city_name,
        "target_date":     target_date.strftime("%Y-%m-%d"),
        "days_ahead":      days_ahead,
        "predicted_temp_c":     round(pred_temp, 1),
        "confidence_low":       round(pred_temp - confidence_margin, 1),
        "confidence_high":      round(pred_temp + confidence_margin, 1),
        "estimated_condition":  weather_cond,
        "model_used":           best_name,
        "model_mae_train":      round(model_mae, 2),
        "current_temp_c":       baseline["avg_temp_c"],
        "temp_change_vs_today": round(pred_temp - baseline["avg_temp_c"], 1),
    }

    return result


# COMMAND ----------
# MAGIC %md
# MAGIC ## 9. Demo dự đoán — Ngày mai và các ngày tới

# COMMAND ----------

print("=" * 65)
print("  DỰ ĐOÁN THỜI TIẾT — DEMO")
print("=" * 65)

# Danh sách thành phố muốn dự đoán
demo_cities = ["Ho Chi Minh City", "Hanoi", "Tokyo", "London", "Singapore"]

# Dự đoán ngày mai cho các thành phố
print("\n📅 DỰ ĐOÁN NGÀY MAI:")
print("-" * 65)
for city in demo_cities:
    pred = predict_future_weather(city, days_ahead=1)
    if pred:
        change_str = f"+{pred['temp_change_vs_today']}" if pred['temp_change_vs_today'] >= 0 else str(pred['temp_change_vs_today'])
        print(
            f"  {pred['city']:20} {pred['target_date']}  "
            f"{pred['predicted_temp_c']:5.1f}°C  "
            f"[{pred['confidence_low']:.1f}–{pred['confidence_high']:.1f}]  "
            f"({change_str}°C)  {pred['estimated_condition']}"
        )

# Dự đoán 1 tuần tới cho HCM City
print("\n📅 DỰ ĐOÁN 7 NGÀY TỚI — Ho Chi Minh City:")
print("-" * 65)
for d in range(1, 8):
    pred = predict_future_weather("Ho Chi Minh City", days_ahead=d)
    if pred:
        change_str = f"+{pred['temp_change_vs_today']}" if pred['temp_change_vs_today'] >= 0 else str(pred['temp_change_vs_today'])
        print(
            f"  +{d} ngày ({pred['target_date']})  "
            f"{pred['predicted_temp_c']:5.1f}°C  "
            f"[{pred['confidence_low']:.1f}–{pred['confidence_high']:.1f}]  "
            f"{pred['estimated_condition']}"
        )

# COMMAND ----------
# MAGIC %md
# MAGIC ## 10. Lưu kết quả dự đoán vào Delta Table

# COMMAND ----------

from pyspark.sql.types import StructType, StructField, StringType, DoubleType, IntegerType

# Tạo predictions cho tất cả thành phố × 7 ngày tới
all_predictions = []
all_cities = list(label_encoder.classes_)

for city in all_cities:
    for d in range(1, 8):
        pred = predict_future_weather(city, days_ahead=d)
        if pred:
            all_predictions.append(pred)

print(f"Tổng số dự đoán: {len(all_predictions)} ({len(all_cities)} cities × 7 days)")

# Chuyển sang Spark DataFrame
if all_predictions:
    df_pred = spark.createDataFrame(
        pd.DataFrame(all_predictions)
    ).withColumn("predicted_at", F.current_timestamp() if "F" in dir() else __import__("pyspark.sql.functions", fromlist=["current_timestamp"]).current_timestamp())

    PRED_TABLE = f"{CATALOG}.{SCHEMA}.ml_weather_predictions"
    (
        df_pred.write
        .format("delta")
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(PRED_TABLE)
    )

    print(f"✅ Đã lưu {len(all_predictions)} dự đoán → {PRED_TABLE}")
    df_pred.orderBy("city", "days_ahead").show(20, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 11. Tóm tắt kết quả

# COMMAND ----------

print("=" * 65)
print("  KẾT QUẢ TRAINING")
print("=" * 65)
print(f"  Data source       : {data_source}")
print(f"  Training samples  : {len(X_train)}")
print(f"  Test samples      : {len(X_test)}")
print(f"  Features used     : {len(FEATURES)}")
print(f"  Models trained    : {len(results)}")
print()
print(f"{'Model':<20} {'MAE':>8} {'R²':>7}")
print("-" * 40)
for name, m in sorted(results.items(), key=lambda x: x[1]["mae"]):
    marker = " ← BEST" if name == best_name else ""
    print(f"  {name:<18} {m['mae']:>7.2f}°C {m['r2']:>6.3f}{marker}")
print()
print(f"  Best model        : {best_name}")
print(f"  Best MAE          : {results[best_name]['mae']:.2f}°C")
print(f"  Best R²           : {results[best_name]['r2']:.3f}")
print()
print("  → Xem MLflow: sidebar Experiments → weather_forecast")
print("  → Dự đoán:    workspace.weather_pipeline.ml_weather_predictions")
print("=" * 65)