"""
populate_conformite.py — Remplissage de l'outil conformité via l'API Laravel.
Crée des alertes rouge/orange selon les résultats de validation.
"""

import logging

from docuhack_tasks.laravel_client import LaravelAPIClient

logger = logging.getLogger(__name__)


def populate_conformite(**context):
    """Crée des alertes conformité pour les documents invalides ou suspects."""
    ti = context["ti"]
    validated = ti.xcom_pull(task_ids="validate_documents")

    if not validated:
        logger.info("[conformite] Aucun document à traiter")
        return

    api = LaravelAPIClient()
    stats = {"alertes_rouges": 0, "alertes_oranges": 0, "skipped": 0}

    for doc in validated:
        sd = doc["structured_data"]
        document_id = doc.get("document_id")

        if doc.get("is_globally_valid"):
            stats["skipped"] += 1
            continue

        # Déterminer le niveau d'alerte
        anomalies = sd["validation"].get("anomalies", [])
        failed_rules = [r for r in doc.get("validation_results", []) if not r["passed"]]

        is_invalid = not sd["validation"].get("is_valid", False)
        has_multiple_anomalies = len(anomalies) > 1 or len(failed_rules) > 1

        if is_invalid or has_multiple_anomalies:
            niveau = "rouge"
            stats["alertes_rouges"] += 1
        else:
            niveau = "orange"
            stats["alertes_oranges"] += 1

        # Construire le message
        entreprise = sd["entities"].get("entreprise", "Inconnu")
        doc_type = sd.get("document_type", "document")
        messages = []
        if anomalies:
            messages.append(f"Anomalies: {', '.join(anomalies)}")
        for rule in failed_rules:
            messages.append(rule["message"])
        message = f"{doc_type.upper()} - {entreprise}: {'; '.join(messages) if messages else 'Document invalide'}"

        # Trouver le fournisseur_id
        siren = sd["entities"].get("siren", "")
        fournisseur_id = None
        if siren and len(siren) == 9:
            try:
                f = api.get_fournisseur_by_siren(siren)
                if f:
                    fournisseur_id = f["id"]
            except Exception:
                pass

        # Créer l'alerte
        try:
            api.create_alerte(
                type_alerte=f"validation_{doc_type}",
                niveau=niveau,
                message=message,
                documents_concernes=[document_id] if document_id else [],
                fournisseur_id=fournisseur_id,
                details={
                    "filename": doc["filename"],
                    "anomalies": anomalies,
                    "validation_results": doc.get("validation_results", []),
                    "scenario": sd.get("scenario", ""),
                },
            )
            logger.info(f"[conformite] Alerte {niveau} créée: {doc['filename']}")
        except Exception as e:
            logger.error(f"[conformite] Erreur alerte {doc['filename']}: {e}")

    logger.info(f"[conformite] Terminé: {stats}")
    return stats
