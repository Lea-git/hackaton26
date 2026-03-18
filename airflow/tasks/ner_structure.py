"""
ner_structure.py — Structuration NER → JSON, upload vers curated-documents.
"""

import io
import json
import logging
from minio import Minio

from airflow.tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_CURATED, SCENARIO_MAP,
)

logger = logging.getLogger(__name__)


def _build_structured_json(gt_entry):
    """Construit un document JSON structuré à partir des données ground truth."""
    siret = gt_entry.get("siret_affiche", "")
    siren = siret[:9] if len(siret) >= 9 else siret

    anomalies = []
    if not gt_entry.get("is_valid"):
        error_type = gt_entry.get("error_type")
        if error_type:
            anomalies.append(error_type)
        # Vérifier cohérence SIREN
        if gt_entry.get("siret_attendu") != gt_entry.get("siret_affiche"):
            anomalies.append("siret_mismatch")

    # Vérifier TVA (HT * 1.20 ≈ TTC)
    total_ht = gt_entry.get("total_ht", 0)
    total_ttc = gt_entry.get("total_ttc", 0)
    tva = gt_entry.get("tva", 0)
    if total_ht > 0:
        expected_ttc = round(total_ht * 1.20, 2)
        if abs(expected_ttc - total_ttc) > 1.0:
            anomalies.append("tva_inconsistency")

    return {
        "filename": gt_entry["filename"],
        "scenario": gt_entry.get("scenario", ""),
        "scenario_description": SCENARIO_MAP.get(gt_entry.get("scenario", ""), ""),
        "document_type": gt_entry.get("doc_type", "inconnu"),
        "category": gt_entry.get("category", ""),
        "entities": {
            "emetteur": gt_entry.get("emetteur"),
            "entreprise": gt_entry.get("entreprise"),
            "siren": siren,
            "siret": siret,
            "siret_attendu": gt_entry.get("siret_attendu"),
            "client": gt_entry.get("client"),
            "valideur": gt_entry.get("valideur"),
        },
        "financials": {
            "montant_ht": total_ht,
            "tva": tva,
            "montant_ttc": total_ttc,
        },
        "validation": {
            "is_valid": gt_entry.get("is_valid", False),
            "error_type": gt_entry.get("error_type"),
            "anomalies": anomalies,
        },
        "metadata": {
            "format": gt_entry.get("format", "pdf"),
            "difficulty": gt_entry.get("difficulty", ""),
            "split": gt_entry.get("split", ""),
            "linked_files": gt_entry.get("linked_files", []),
        },
    }


def ner_structuration(**context):
    """Transforme les données OCR en JSON structuré et uploade dans curated-documents."""
    ti = context["ti"]
    ocr_results = ti.xcom_pull(task_ids="mock_ocr")

    if not ocr_results:
        logger.info("[ner] Aucun document à structurer")
        return []

    minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                         secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)

    structured = []
    for doc in ocr_results:
        gt_entry = doc["gt_entry"]
        structured_data = _build_structured_json(gt_entry)

        curated_name = doc["filename"].rsplit(".", 1)[0] + ".json"
        payload = json.dumps(structured_data, ensure_ascii=False, indent=2).encode("utf-8")

        minio_client.put_object(
            BUCKET_CURATED, curated_name,
            io.BytesIO(payload), len(payload),
            content_type="application/json",
        )
        logger.info(f"[ner] {doc['filename']} → {curated_name} uploadé dans curated-documents")

        structured.append({
            "filename": doc["filename"],
            "document_id": doc.get("document_id"),
            "curated_name": curated_name,
            "structured_data": structured_data,
        })

    return structured
