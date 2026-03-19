from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import os
import cv2

# ---------- OCR pipeline imports ----------
from ocr_pipeline import (
    extract_text_from_image,
    extract_text_from_pdf,
    clean_text,
    extract_all_fields,
    infer_document_type
)

# ---------- DataLake client ----------
from datalake import DataLakeClient

# ---------- Initialisation ----------
app = FastAPI(title="OCR Hackathon Backend 🚀")
client = DataLakeClient()

TEMP_FOLDER = "temp"
os.makedirs(TEMP_FOLDER, exist_ok=True)

# ---------- Fonction pipeline OCR → Datalake ----------
def process_and_store_document(file_path, object_name):
    """
    Prend un fichier local, exécute OCR + extraction + classification
    et stocke les résultats dans le datalake (RAW / CLEAN / CURATED).
    Retourne le JSON structuré.
    """

    # 1️⃣ Upload RAW
    client.upload_raw(object_name, file_path)

    # 2️⃣ OCR
    if file_path.lower().endswith(".pdf"):
        text = extract_text_from_pdf(file_path)
    else:
        image = cv2.imread(file_path)
        text = extract_text_from_image(image)

    cleaned = clean_text(text)

    # 3️⃣ Upload CLEAN
    clean_name = object_name.rsplit(".", 1)[0] + ".txt"
    client.upload_clean(clean_name, cleaned)

    # 4️⃣ Extraction des champs
    data = extract_all_fields(cleaned)

    # 5️⃣ Classification du type de document
    doc_type, score = infer_document_type(data)

    # 6️⃣ Création JSON CURATED
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
    client.upload_curated(curated_name, curated_data)

    return curated_data

# ---------- Routes FastAPI ----------
@app.get("/")
def read_root():
    return {"message": "Hello from Python backend 🚀"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload un document PDF ou image, exécute OCR + extraction + classification,
    et le stocke dans le datalake.
    Retourne le JSON structuré.
    """
    file_path = os.path.join(TEMP_FOLDER, file.filename)
    os.makedirs(TEMP_FOLDER, exist_ok=True)

    # Sauvegarde locale temporaire
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        result = process_and_store_document(file_path, file.filename)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)