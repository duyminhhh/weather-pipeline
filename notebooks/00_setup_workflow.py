# Databricks notebook source
# MAGIC %md
# MAGIC # 00 — Setup: Tạo Workflow tự động chạy pipeline
# MAGIC
# MAGIC Notebook này dùng Databricks REST API để tạo **Workflow (Job)**
# MAGIC lên lịch chạy toàn bộ pipeline mỗi 6 giờ — không cần Airflow hay Docker.
# MAGIC
# MAGIC **Thứ tự chạy:**
# MAGIC ```
# MAGIC weather_crawler  →  bronze_ingest  →  silver_transform  →  gold_aggregate  →  ml_train
# MAGIC ```
# MAGIC
# MAGIC **Chạy 1 lần duy nhất để setup.**

# COMMAND ----------

import requests
import json

HOST  = "https://" + spark.conf.get("spark.databricks.workspaceUrl")
TOKEN = dbutils.notebook.entry_point.getDbutils().notebook().getContext().apiToken().get()

WORKSPACE_PATH = "/Shared/weather-pipeline"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

print(f"Host      : {HOST}")
print(f"Workspace : {WORKSPACE_PATH}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Build job_config — weather_crawler chạy đầu tiên

# COMMAND ----------

def make_task(task_key, notebook_name, depends_on=None, timeout=1800, retries=2):
    """Tạo task config cho Serverless compute."""
    task = {
        "task_key": task_key,
        "notebook_task": {
            "notebook_path": f"{WORKSPACE_PATH}/{notebook_name}",
            "source": "WORKSPACE",
        },
        "timeout_seconds": timeout,
        "max_retries": retries,
        "min_retry_interval_millis": 60000,
    }
    if depends_on:
        task["depends_on"] = [{"task_key": k} for k in depends_on]
    return task


job_config = {
    "name": "weather-pipeline",
    "tags": {"project": "weather", "env": "free-edition"},

    "tasks": [
        # ① Crawler chạy TRƯỚC TIÊN — fetch data, ghi weather_latest.json
        make_task(
            "weather_crawler",
            "weather_crawler",
            depends_on=None,   # không phụ thuộc ai — chạy đầu tiên
            timeout=600,       # 10 phút là đủ
            retries=3,         # retry nếu network lỗi
        ),

        # ② Bronze → ③ Silver → ④ Gold → ⑤ ML (mỗi bước phụ thuộc bước trước)
        make_task("bronze_ingest",    "01_bronze_ingest",    depends_on=["weather_crawler"]),
        make_task("silver_transform", "02_silver_transform", depends_on=["bronze_ingest"]),
        make_task("gold_aggregate",   "03_gold_aggregate",   depends_on=["silver_transform"]),
        make_task("ml_train",         "04_ml_train",         depends_on=["gold_aggregate"],
                  timeout=3600, retries=1),
    ],

    # Schedule: mỗi 6 giờ (0:00, 6:00, 12:00, 18:00 Asia/Ho_Chi_Minh)
    "schedule": {
        "quartz_cron_expression": "0 0 0/6 * * ?",
        "timezone_id": "Asia/Ho_Chi_Minh",
        "pause_status": "UNPAUSED",
    },

    # Uncomment để nhận email khi job thất bại:
    # "email_notifications": {
    #     "on_failure": ["your@email.com"],
    #     "no_alert_for_skipped_runs": True,
    # },
}

print("job_config đã build xong:")
print(json.dumps(job_config, indent=2, ensure_ascii=False))

# COMMAND ----------
# MAGIC %md
# MAGIC ## Tạo hoặc cập nhật Job

# COMMAND ----------

resp = requests.get(f"{HOST}/api/2.1/jobs/list", headers=HEADERS)
resp.raise_for_status()
existing_job = next(
    (j for j in resp.json().get("jobs", [])
     if j["settings"]["name"] == "weather-pipeline"),
    None
)

if existing_job:
    job_id = existing_job["job_id"]
    r = requests.post(
        f"{HOST}/api/2.1/jobs/reset",
        headers=HEADERS,
        json={"job_id": job_id, "new_settings": job_config},
    )
    if not r.ok:
        print(f"Lỗi update job: {r.status_code}")
        print(r.json())
        r.raise_for_status()
    print(f"✓ Job updated — job_id: {job_id}")
else:
    r = requests.post(f"{HOST}/api/2.1/jobs/create", headers=HEADERS, json=job_config)
    if not r.ok:
        print(f"Lỗi tạo job: {r.status_code}")
        print(r.json())
        r.raise_for_status()
    job_id = r.json()["job_id"]
    print(f"✓ Job created — job_id: {job_id}")

print(f"\n→ Xem tại: {HOST}/jobs/{job_id}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Trigger chạy ngay (lần đầu)

# COMMAND ----------

run = requests.post(
    f"{HOST}/api/2.1/jobs/run-now",
    headers=HEADERS,
    json={"job_id": job_id},
)
if not run.ok:
    print(f"Lỗi trigger run: {run.status_code}")
    print(run.json())
    run.raise_for_status()

run_id = run.json()["run_id"]
print(f"✓ Pipeline triggered — run_id: {run_id}")
print(f"→ Theo dõi tại: {HOST}/jobs/{job_id}/runs/{run_id}")
print(f"\nThứ tự chạy: weather_crawler → bronze_ingest → silver_transform → gold_aggregate → ml_train")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Xem runs gần đây

# COMMAND ----------

runs = requests.get(
    f"{HOST}/api/2.1/jobs/runs/list",
    headers=HEADERS,
    params={"job_id": job_id, "limit": 5},
).json()

for r in runs.get("runs", []):
    state = r.get("state", {})
    print(
        f"run_id={r['run_id']}  "
        f"state={state.get('life_cycle_state','?'):12}  "
        f"result={state.get('result_state','—'):10}  "
        f"url={r.get('run_page_url','')}"
    )
