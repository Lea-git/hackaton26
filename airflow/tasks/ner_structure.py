"""
ner_structure.py — Structuration NER → JSON, upload vers curated-documents.
Supporte le mode mock (gt_entry) et le mode réel (ocr_fields).
"""

import io
import json
import logging
import os
from minio import Minio

from docuhack_tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_CURATED, SCENARIO_MAP,
)

logger = logging.getLogger(__name__)

OCR_MODE = os.getenv("OCR_MODE", "real")


def _build_structured_json(gt_entry):
    """Construit un document JSON structuré à partir des données ground truth (mode mock)."""
    siret = gt_entry.get("siret_affiche", "")
    siren = siret[:9] if len(siret) >= 9 else siret

    anomalies = []
    if not gt_entry.get("is_valid"):
        error_type = gt_entry.get("error_type")
        if error_type:
            anomalies.append(error_type)
        if gt_entry.get("siret_attendu") != gt_entry.get("siret_affiche"):
            anomalies.append("siret_mismatch")

    total_ht = gt_entry.get("total_ht") or 0
    total_ttc = gt_entry.get("total_ttc") or 0
    tva = gt_entry.get("tva") or 0
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


def _to_float(v):
    """Convertit une valeur (str ou None) en float, retourne 0 si impossible."""
    if v is None:
        return 0
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return 0


def _build_structured_json_from_ocr(ocr_fields, doc_type, filename, model_fields=None):
    """Construit un document JSON structuré.

    Utilise en priorité les champs extraits par le modèle Donut (model_fields),
    avec fallback sur les champs OCR/regex (ocr_fields).
    """
    mf = model_fields or {}

    siret = mf.get("siret") or ocr_fields.get("siret") or ""
    siren = siret[:9] if len(siret) >= 9 else siret

    # Montants : modèle en priorité, sinon OCR regex
    montant_ht_data = ocr_fields.get("montant_ht")
    montant_ttc_data = ocr_fields.get("montant_ttc")
    tva_data = ocr_fields.get("tva")

    montant_ht = _to_float(mf.get("total_ht")) or (montant_ht_data["value"] if montant_ht_data else 0)
    montant_ttc = _to_float(mf.get("total_ttc")) or (montant_ttc_data["value"] if montant_ttc_data else 0)
    tva = _to_float(mf.get("tva")) or (tva_data["value"] if tva_data else 0)

    anomalies = []
    is_valid = True
    if montant_ht > 0:
        expected_ttc = round(montant_ht * 1.20, 2)
        if abs(expected_ttc - montant_ttc) > 1.0:
            anomalies.append("tva_inconsistency")
            is_valid = False

    return {
        "filename": filename,
        "scenario": None,
        "scenario_description": None,
        "document_type": doc_type,
        "category": "",
        "entities": {
            "emetteur": mf.get("emetteur"),
            "entreprise": mf.get("entreprise") or ocr_fields.get("nom_entreprise"),
            "siren": siren,
            "siret": siret,
            "siret_attendu": None,
            "client": mf.get("client"),
            "valideur": mf.get("valideur"),
        },
        "financials": {
            "montant_ht": montant_ht,
            "tva": tva,
            "montant_ttc": montant_ttc,
        },
        "validation": {
            "is_valid": is_valid,
            "error_type": None,
            "anomalies": anomalies,
        },
        "metadata": {
            "format": filename.rsplit(".", 1)[-1] if "." in filename else "pdf",
            "difficulty": "",
            "split": "",
            "linked_files": [],
        },
    }


def ner_structuration(**context):
    """Transforme les données OCR en JSON structuré et uploade dans curated-documents."""
    ti = context["ti"]
    # Tire depuis model_extract qui enrichit les résultats de ocr_extract
    ocr_results = ti.xcom_pull(task_ids="model_extract")

    if not ocr_results:
        logger.info("[ner] Aucun document à structurer")
        return []

    minio_client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
                         secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE)

    structured = []
    for doc in ocr_results:
        filename = doc["filename"]

        if OCR_MODE == "mock" and "gt_entry" in doc:
            structured_data = _build_structured_json(doc["gt_entry"])
        else:
            ocr_fields = doc.get("ocr_fields", {})
            model_fields = doc.get("model_fields", {})
            doc_type = doc.get("doc_type", "inconnu")
            structured_data = _build_structured_json_from_ocr(ocr_fields, doc_type, filename, model_fields)

        curated_name = filename.rsplit(".", 1)[0] + ".json"
        payload = json.dumps(structured_data, ensure_ascii=False, indent=2).encode("utf-8")

        minio_client.put_object(
            BUCKET_CURATED, curated_name,
            io.BytesIO(payload), len(payload),
            content_type="application/json",
        )
        logger.info(f"[ner] {filename} → {curated_name} uploadé dans curated-documents")

        structured.append({
            "filename": filename,
            "document_id": doc.get("document_id"),
            "curated_name": curated_name,
            "structured_data": structured_data,
        })

    return structured
