"""
validate.py — Vérifie la cohérence des documents structurés.
Règles : SIREN consistency, TVA (HT × 1.20 = TTC), expiration attestations.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def validate_documents(**context):
    """Valide les documents structurés et enrichit avec les résultats de validation."""
    ti = context["ti"]
    structured = ti.xcom_pull(task_ids="ner_structuration")

    if not structured:
        logger.info("[validate] Aucun document à valider")
        return []

    validated = []
    for doc in structured:
        sd = doc["structured_data"]
        validation_results = []

        # Règle 1 : SIREN consistency
        siret_attendu = sd["entities"].get("siret_attendu", "")
        siret_affiche = sd["entities"].get("siret", "")
        if siret_attendu and siret_affiche:
            if siret_attendu[:9] != siret_affiche[:9]:
                validation_results.append({
                    "rule": "siren_consistency",
                    "passed": False,
                    "message": f"SIREN attendu {siret_attendu[:9]} ≠ affiché {siret_affiche[:9]}",
                })
            else:
                validation_results.append({
                    "rule": "siren_consistency",
                    "passed": True,
                    "message": "SIREN cohérent",
                })

        # Règle 2 : TVA (HT × 1.20 ≈ TTC)
        montant_ht = sd["financials"].get("montant_ht", 0)
        montant_ttc = sd["financials"].get("montant_ttc", 0)
        if montant_ht > 0:
            expected_ttc = round(montant_ht * 1.20, 2)
            diff = abs(expected_ttc - montant_ttc)
            passed = diff <= 1.0
            validation_results.append({
                "rule": "tva_consistency",
                "passed": passed,
                "message": f"TTC attendu {expected_ttc:.2f}, affiché {montant_ttc:.2f} (diff={diff:.2f})",
            })

        # Règle 3 : Expiration attestations (si c'est une attestation)
        if sd.get("document_type") == "attestation":
            validation_results.append({
                "rule": "attestation_expiry",
                "passed": sd["validation"].get("is_valid", False),
                "message": "Vérification expiration attestation",
            })

        all_passed = all(r["passed"] for r in validation_results) if validation_results else True

        doc["validation_results"] = validation_results
        doc["is_globally_valid"] = all_passed and sd["validation"].get("is_valid", False)
        validated.append(doc)

        status = "VALID" if doc["is_globally_valid"] else "INVALID"
        logger.info(f"[validate] {doc['filename']}: {status} ({len(validation_results)} règles)")

    valid_count = sum(1 for d in validated if d["is_globally_valid"])
    logger.info(f"[validate] Résultat: {valid_count}/{len(validated)} documents valides")

    return validated
