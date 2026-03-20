"""
ingest.py — Scan la raw zone MinIO et enregistre les nouveaux documents dans MySQL via l'API Laravel.
"""

import logging
import os
from minio import Minio

from docuhack_tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_RAW, BUCKET_CLEAN, CONTENT_TYPES,
)
from docuhack_tasks.laravel_client import LaravelAPIClient

logger = logging.getLogger(__name__)


def scan_raw_zone(**context):
    """Liste les fichiers dans raw-documents à traiter.

    Un fichier est à traiter si :
    - il n'est pas encore dans clean-documents (premier passage), OU
    - il a une entrée en_attente en DB (re-upload du même fichier).
    """
    client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                   secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)
    api = LaravelAPIClient()

    raw_objects = {obj.object_name for obj in client.list_objects(BUCKET_RAW, recursive=True)}
    clean_objects = set()
    for obj in client.list_objects(BUCKET_CLEAN, recursive=True):
        name = obj.object_name
        if name.endswith(".txt"):
            name = name[:-4]
        clean_objects.add(name)

    # Récupérer tous les fichiers avec statut en_attente depuis la DB
    pending_filenames = set()
    try:
        resp = api.get_documents()
        all_docs = resp.get("data", {})
        if isinstance(all_docs, dict):
            all_docs = all_docs.get("data", [])
        for doc in all_docs:
            if doc.get("statut_ocr") == "en_attente":
                pending_filenames.add(doc.get("nom_fichier_original", ""))
    except Exception as e:
        logger.warning(f"[scan] Impossible de récupérer les docs en_attente: {e}")

    new_files = []
    for raw_name in sorted(raw_objects):
        base_name = os.path.splitext(raw_name)[0]
        if base_name not in clean_objects:
            # Fichier jamais traité
            new_files.append(raw_name)
        elif raw_name in pending_filenames:
            # Fichier déjà dans clean mais re-uploadé (nouvelle entrée en_attente)
            logger.info(f"[scan] Re-upload détecté (en_attente en DB): {raw_name}")
            new_files.append(raw_name)

    logger.info(f"[scan] {len(new_files)} fichiers à traiter sur {len(raw_objects)} raw total")
    return new_files  # pushed to XCom automatically


def ingest_documents(**context):
    """Enregistre les nouveaux fichiers dans la base MySQL via POST /api/documents."""
    ti = context["ti"]
    new_files = ti.xcom_pull(task_ids="scan_raw_zone", key="new_files")

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
                # Chercher un document en_attente (upload récent pas encore traité)
                pending = [d for d in existing_docs if d.get("statut_ocr") == "en_attente"]
                if pending:
                    # Prendre le plus récent en_attente
                    doc_id = pending[-1]["id"]
                    logger.info(f"[ingest] Document en attente trouvé: {filename} → id={doc_id}")
                    ingested.append({"filename": filename, "document_id": doc_id})
                else:
                    # Tous déjà traités ou en erreur → on skip
                    logger.info(f"[ingest] Document déjà traité, skip: {filename}")
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
