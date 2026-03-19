import os
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse

# ---------- OCR pipeline imports ----------
from ocr import (
    extract_text_from_image,
    extract_text_from_pdf,
    clean_text,
    extract_all_fields,
    infer_document_type
)

# ---------- DataLake client ----------
from datalake import DataLakeClient

# ---------- Initialisation ----------
app = FastAPI(title="OCR Hackathon Backend")
_client = None


def get_datalake_client():
    global _client
    if _client is None:
        _client = DataLakeClient()
    return _client

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

AIRFLOW_API_URL = os.getenv("AIRFLOW_API_URL", "http://airflow-webserver:8080")
AIRFLOW_USER = "admin"
AIRFLOW_PASS = "admin"


# ---------- Fonction pipeline OCR → Datalake ----------
def process_and_store_document(file_path, object_name):
    """
    Prend un fichier local, exécute OCR + extraction + classification
    et stocke les résultats dans le datalake (RAW / CLEAN / CURATED).
    Retourne le JSON structuré.
    """
    import cv2

    dl = get_datalake_client()

    # 1. Upload RAW
    dl.upload_raw(object_name, file_path)

    # 2. OCR
    if file_path.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    else:
        image = cv2.imread(file_path)
        text = extract_text_from_image(image)

    cleaned = clean_text(text)

    # 3. Upload CLEAN
    clean_name = object_name.rsplit(".", 1)[0] + ".txt"
    dl.upload_clean(clean_name, cleaned)

    # 4. Extraction des champs
    data = extract_all_fields(cleaned)

    # 5. Classification du type de document
    doc_type, score = infer_document_type(data)

    # 6. Creation JSON CURATED
    curated_data = {
        "document": {
            "name": object_name,
            "type": doc_type
        },
        "extraction": data,
        "scores": score,
        "pipeline": ["raw", "clean", "curated"]
    }

    curated_name = object_name.rsplit(".", 1)[0] + ".json"
    dl.upload_curated(curated_name, curated_data)

    return curated_data


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Hello from Python backend"}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload un document PDF ou image, exécute OCR + extraction + classification,
    et le stocke dans le datalake.
    """
    file_path = os.path.join(TEMP_FOLDER, file.filename)
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        result = process_and_store_document(file_path, file.filename)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/trigger-pipeline")
def trigger_pipeline():
    """Declenche le DAG docuhack_document_pipeline via l'API REST Airflow."""
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
                "message": "Pipeline declenche",
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
        dl = get_datalake_client()
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
