"""
ocr_real.py — Real OCR using Tesseract via backend/ocr.py → upload vers clean-documents.
"""

import io
import os
import tempfile
import logging
from minio import Minio

import sys
sys.path.insert(0, "/opt/airflow/backend")

from ocr import (
    extract_text_from_pdf,
    extract_text_from_image,
    clean_text,
    extract_all_fields,
    infer_document_type,
)
import cv2
import numpy as np

from docuhack_tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_RAW, BUCKET_CLEAN,
)

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")


def real_ocr(**context):
    """Pour chaque document ingéré, effectue le vrai OCR Tesseract et uploade dans clean-documents."""
    ti = context["ti"]
    ingested = ti.xcom_pull(task_ids="ingest_documents")

    if not ingested:
        logger.info("[ocr] Aucun document à traiter")
        return []

    minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                         secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)

    processed = []
    for doc in ingested:
        filename = doc["filename"]
        ext = os.path.splitext(filename)[1].lower()

        # Download raw file from MinIO to temp
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name

        try:
            minio_client.fget_object(BUCKET_RAW, filename, tmp_path)
            logger.info(f"[ocr] Fichier {filename} téléchargé depuis MinIO")

            # OCR
            if ext == ".pdf":
                raw_text = extract_text_from_pdf(tmp_path)
            elif ext in IMAGE_EXTENSIONS:
                image = cv2.imread(tmp_path)
                if image is None:
                    logger.error(f"[ocr] Impossible de lire l'image {filename}")
                    continue
                raw_text = extract_text_from_image(image)
            else:
                logger.warning(f"[ocr] Extension non supportée pour {filename}, skip")
                continue

            # Clean
            cleaned_text = clean_text(raw_text)
            logger.info(f"[ocr] Texte OCR extrait pour {filename} ({len(cleaned_text)} chars)")

            # Upload clean text to MinIO
            clean_name = filename.rsplit(".", 1)[0] + ".txt"
            data = cleaned_text.encode("utf-8")
            minio_client.put_object(
                BUCKET_CLEAN, clean_name,
                io.BytesIO(data), len(data),
                content_type="text/plain; charset=utf-8",
            )
            logger.info(f"[ocr] {filename} → {clean_name} uploadé dans clean-documents")

            # Extract fields
            ocr_fields = extract_all_fields(cleaned_text)

            # Classify
            doc_type, doc_scores = infer_document_type(ocr_fields)
            logger.info(f"[ocr] {filename} classifié comme '{doc_type}' (scores: {doc_scores})")

            processed.append({
                "filename": filename,
                "document_id": doc.get("document_id"),
                "clean_name": clean_name,
                "ocr_fields": ocr_fields,
                "doc_type": doc_type,
                "doc_scores": doc_scores,
            })

        except Exception as e:
            logger.error(f"[ocr] Erreur OCR pour {filename}: {e}")
            continue
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return processed
