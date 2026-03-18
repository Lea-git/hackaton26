import os
import requests
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://airflow-webserver:8080")
AIRFLOW_USER = "admin"
AIRFLOW_PASS = "admin"


@app.get("/")
def read_root():
    return {"message": "Hello from Python backend 🚀"}


@app.post("/trigger-pipeline")
def trigger_pipeline():
    """Déclenche le DAG docuhack_document_pipeline via l'API REST Airflow."""
    try:
        resp = requests.post(
            f"{AIRFLOW_API_URL}/api/v1/dags/docuhack_document_pipeline/dagRuns",
            json={"conf": {}},
            auth=(AIRFLOW_USER, AIRFLOW_PASS),
            timeout=10,
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "success": True,
                "message": "Pipeline déclenché",
                "dag_run_id": data.get("dag_run_id"),
                "state": data.get("state"),
            }
        else:
            return JSONResponse(
                status_code=resp.status_code,
                content={"success": False, "message": f"Airflow error: {resp.text}"},
            )
    except requests.exceptions.ConnectionError:
        return JSONResponse(
            status_code=503,
            content={"success": False, "message": "Airflow non disponible"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": str(e)},
        )


@app.get("/health/pipeline")
def health_pipeline():
    """Endpoint monitoring : stats zones MinIO + dernier DAG run + documents pending."""
    result = {
        "status": "ok",
        "minio": {},
        "airflow": {},
    }

    # Stats MinIO
    try:
        from datalake import DataLakeClient
        dl = DataLakeClient()
        result["minio"] = dl.get_stats()
    except Exception as e:
        result["minio"] = {"error": str(e)}

    # Dernier DAG run Airflow
    try:
        resp = requests.get(
            f"{AIRFLOW_API_URL}/api/v1/dags/docuhack_document_pipeline/dagRuns",
            params={"limit": 1, "order_by": "-execution_date"},
            auth=(AIRFLOW_USER, AIRFLOW_PASS),
            timeout=10,
        )
        if resp.status_code == 200:
            runs = resp.json().get("dag_runs", [])
            if runs:
                last_run = runs[0]
                result["airflow"]["last_run"] = {
                    "dag_run_id": last_run.get("dag_run_id"),
                    "state": last_run.get("state"),
                    "execution_date": last_run.get("execution_date"),
                    "start_date": last_run.get("start_date"),
                    "end_date": last_run.get("end_date"),
                }
            else:
                result["airflow"]["last_run"] = None
        else:
            result["airflow"]["error"] = f"HTTP {resp.status_code}"
    except Exception as e:
        result["airflow"]["error"] = str(e)

    # Documents pending (raw - clean)
    try:
        raw_count = result["minio"].get("raw", {}).get("nb_objects", 0)
        clean_count = result["minio"].get("clean", {}).get("nb_objects", 0)
        curated_count = result["minio"].get("curated", {}).get("nb_objects", 0)
        result["documents"] = {
            "raw": raw_count,
            "clean": clean_count,
            "curated": curated_count,
            "pending": max(0, raw_count - clean_count),
        }
    except Exception:
        result["documents"] = {}

    return result
