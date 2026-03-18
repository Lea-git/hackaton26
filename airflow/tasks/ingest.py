"""
ingest.py — Scan la raw zone MinIO et enregistre les nouveaux documents dans MySQL via l'API Laravel.
"""

import logging
import os
from minio import Minio

from airflow.tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_RAW, BUCKET_CLEAN, CONTENT_TYPES,
)
from airflow.tasks.laravel_client import LaravelAPIClient

logger = logging.getLogger(__name__)


def scan_raw_zone(**context):
    """Liste les fichiers dans raw-documents qui ne sont pas encore dans clean-documents."""
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                   secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)

    raw_objects = {obj.object_name for obj in client.list_objects(BUCKET_RAW, recursive=True)}
    clean_objects = set()
    for obj in client.list_objects(BUCKET_CLEAN, recursive=True):
        # clean files have .txt extension, map back to original name
        name = obj.object_name
        for ext in [".txt"]:
            if name.endswith(ext):
                name = name[: -len(ext)]
                break
        clean_objects.add(name)

    new_files = []
    for raw_name in sorted(raw_objects):
        base_name = os.path.splitext(raw_name)[0]
        if base_name not in clean_objects:
            new_files.append(raw_name)

    logger.info(f"[scan] {len(new_files)} nouveaux fichiers détectés sur {len(raw_objects)} raw total")
    return new_files  # pushed to XCom automatically


def ingest_documents(**context):
    """Enregistre les nouveaux fichiers dans la base MySQL via POST /api/documents."""
    ti = context["ti"]
    new_files = ti.xcom_pull(task_ids="scan_raw_zone")

    if not new_files:
        logger.info("[ingest] Aucun nouveau fichier à ingérer")
        return []

    api = LaravelAPIClient()
    minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                         secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)

    ingested = []
    for filename in new_files:
        # Vérifier si le document existe déjà
        try:
            resp = api.get_documents(nom_fichier=filename)
            existing = resp.get("data", {})
            if isinstance(existing, dict):
                existing_docs = existing.get("data", [])
            else:
                existing_docs = existing
            if existing_docs:
                logger.info(f"[ingest] Document déjà existant: {filename}")
                ingested.append({
                    "filename": filename,
                    "document_id": existing_docs[0]["id"],
                })
                continue
        except Exception:
            pass

        # Récupérer la taille
        try:
            stat = minio_client.stat_object(BUCKET_RAW, filename)
            taille = stat.size
        except Exception:
            taille = 0

        ext = os.path.splitext(filename)[1].lower()
        mime = CONTENT_TYPES.get(ext, "application/octet-stream")

        try:
            resp = api.create_document(
                nom=filename,
                chemin=f"raw-documents/{filename}",
                type_doc="non_classe",
                mime=mime,
                taille=taille,
            )
            doc_id = resp.get("data", {}).get("id")
            logger.info(f"[ingest] Document créé: {filename} → id={doc_id}")
            ingested.append({"filename": filename, "document_id": doc_id})
        except Exception as e:
            logger.error(f"[ingest] Erreur création {filename}: {e}")

    return ingested
