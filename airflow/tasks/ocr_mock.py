"""
ocr_mock.py — Mock OCR basé sur ground_truth.json → upload vers clean-documents.
"""

import io
import json
import logging
from minio import Minio

from airflow.tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_CLEAN, GROUND_TRUTH_PATH,
)

logger = logging.getLogger(__name__)


def _load_ground_truth():
    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        return {item["filename"]: item for item in json.load(f)}


def _generate_ocr_text(gt_entry):
    """Génère un texte OCR simulé à partir des données ground truth."""
    lines = [
        f"=== DOCUMENT OCR EXTRAIT ===",
        f"Type: {gt_entry.get('doc_type', 'inconnu').upper()}",
        f"Scénario: {gt_entry.get('scenario', 'N/A')}",
        f"",
        f"Émetteur: {gt_entry.get('emetteur', 'N/A')}",
        f"Entreprise: {gt_entry.get('entreprise', 'N/A')}",
        f"SIRET: {gt_entry.get('siret_affiche', 'N/A')}",
        f"Client: {gt_entry.get('client', 'N/A')}",
        f"",
        f"Montant HT: {gt_entry.get('total_ht', 0):.2f} EUR",
        f"TVA: {gt_entry.get('tva', 0):.2f} EUR",
        f"Montant TTC: {gt_entry.get('total_ttc', 0):.2f} EUR",
        f"",
        f"Valideur: {gt_entry.get('valideur', 'N/A')}",
        f"Valide: {'OUI' if gt_entry.get('is_valid') else 'NON'}",
    ]
    if gt_entry.get("error_type"):
        lines.append(f"Erreur détectée: {gt_entry['error_type']}")
    return "\n".join(lines)


def mock_ocr(**context):
    """Pour chaque document ingéré, génère le texte OCR et l'uploade dans clean-documents."""
    ti = context["ti"]
    ingested = ti.xcom_pull(task_ids="ingest_documents")

    if not ingested:
        logger.info("[ocr] Aucun document à traiter")
        return []

    gt = _load_ground_truth()
    minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                         secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)

    processed = []
    for doc in ingested:
        filename = doc["filename"]
        gt_entry = gt.get(filename)

        if not gt_entry:
            logger.warning(f"[ocr] Pas de ground truth pour {filename}, skip")
            continue

        ocr_text = _generate_ocr_text(gt_entry)
        clean_name = filename.rsplit(".", 1)[0] + ".txt"

        data = ocr_text.encode("utf-8")
        minio_client.put_object(
            BUCKET_CLEAN, clean_name,
            io.BytesIO(data), len(data),
            content_type="text/plain; charset=utf-8",
        )
        logger.info(f"[ocr] {filename} → {clean_name} uploadé dans clean-documents")

        processed.append({
            **doc,
            "clean_name": clean_name,
            "gt_entry": gt_entry,
        })

    return processed
