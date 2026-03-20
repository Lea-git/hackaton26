"""
anomaly_detection.py — Détection d'anomalies sur les documents structurés.

Utilise DocumentValidator (IsolationForest + API SIRET gouvernementale + vérification math)
pour classifier chaque document : VALID, INVALID ou SUSPECT.
S'insère entre ner_structuration et validate_documents dans le pipeline.
"""

import io
import json
import logging

from minio import Minio

from docuhack_tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_CURATED,
)

logger = logging.getLogger(__name__)


def anomaly_detection(**context):
    """Analyse chaque document NER avec DocumentValidator et enrichit le curated JSON."""
    # Import lazy pour ne pas casser le parsing du DAG si sklearn/thefuzz absents
    try:
        from docuhack_tasks.document_validator import DocumentValidator
    except ImportError as e:
        logger.error(f"[anomaly] DocumentValidator non disponible: {e} — passage sans analyse")
        ti = context["ti"]
        return ti.xcom_pull(task_ids="ner_structuration") or []

    ti = context["ti"]
    structured_docs = ti.xcom_pull(task_ids="ner_structuration")

    if not structured_docs:
        logger.info("[anomaly] Aucun document à analyser")
        return []

    validator = DocumentValidator()
    minio_client = Minio(
        MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE,
    )

    enriched = []
    for doc in structured_docs:
        sd = doc["structured_data"]
        filename = doc["filename"]

        # Aplatir vers le format attendu par DocumentValidator
        flat = {
            "document_type": sd.get("document_type"),
            "siret": sd["entities"].get("siret"),
            "vendor_name": sd["entities"].get("entreprise"),
            "montant_ht": sd["financials"].get("montant_ht"),
            "montant_ttc": sd["financials"].get("montant_ttc"),
        }

        try:
            result = validator.analyze(flat)
            logger.info(
                f"[anomaly] {filename} → {result['status']} "
                f"(risk={result['risk_score']}, checks={result['checks']})"
            )
        except Exception as e:
            logger.error(f"[anomaly] Erreur analyse {filename}: {e}")
            result = {
                "status": "SUSPECT",
                "risk_score": 50,
                "checks": {"siret": False, "math": False, "ml": False},
                "metadata": {"errors": [str(e)], "analyzed_at": None},
            }

        # Injecter le résultat dans structured_data
        sd["anomaly_detection"] = result

        # Mettre à jour le curated JSON dans MinIO avec le résultat d'anomalie
        curated_name = doc.get("curated_name")
        if curated_name:
            try:
                # Construire le payload curated enrichi
                curated_payload = {
                    **sd,
                    "validation_status": result["status"],
                    "risk_score": result["risk_score"],
                    "anomaly_detection": result,
                }
                encoded = json.dumps(curated_payload, ensure_ascii=False, indent=2).encode("utf-8")
                minio_client.put_object(
                    BUCKET_CURATED, curated_name,
                    io.BytesIO(encoded), len(encoded),
                    content_type="application/json",
                )
                logger.info(f"[anomaly] {curated_name} mis à jour dans curated-documents")
            except Exception as e:
                logger.error(f"[anomaly] Erreur mise à jour curated {curated_name}: {e}")

        enriched.append(doc)

    valid_count = sum(1 for d in enriched if d["structured_data"]["anomaly_detection"]["status"] == "VALID")
    suspect_count = sum(1 for d in enriched if d["structured_data"]["anomaly_detection"]["status"] == "SUSPECT")
    invalid_count = sum(1 for d in enriched if d["structured_data"]["anomaly_detection"]["status"] == "INVALID")
    logger.info(f"[anomaly] Terminé: {valid_count} VALID, {suspect_count} SUSPECT, {invalid_count} INVALID")

    return enriched
