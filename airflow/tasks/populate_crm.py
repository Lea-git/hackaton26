"""
populate_crm.py — Remplissage du CRM commercial via l'API Laravel.
Crée/update Fournisseur, crée Extraction, met à jour le type document.
"""

import json
import logging

from docuhack_tasks.laravel_client import LaravelAPIClient

logger = logging.getLogger(__name__)


def populate_crm(**context):
    """Peuple le CRM avec les données extraites des documents."""
    ti = context["ti"]
    validated = ti.xcom_pull(task_ids="validate_documents")

    if not validated:
        logger.info("[crm] Aucun document à peupler")
        return

    api = LaravelAPIClient()
    stats = {"fournisseurs_created": 0, "extractions_created": 0, "types_updated": 0}

    for doc in validated:
        sd = doc["structured_data"]
        document_id = doc.get("document_id")

        if not document_id:
            logger.warning(f"[crm] Pas de document_id pour {doc['filename']}, skip")
            continue

        try:
            _process_document(api, doc, sd, document_id, stats)
            api.update_document_status(document_id, "traite")
        except Exception as e:
            logger.error(f"[crm] Erreur globale doc {document_id}: {e}")
            try:
                api.update_document_status(document_id, "erreur")
            except Exception as e2:
                logger.error(f"[crm] Impossible de mettre à jour le statut doc {document_id}: {e2}")

    logger.info(f"[crm] Terminé: {stats}")
    return stats


def _process_document(api, doc, sd, document_id, stats):
    # 1. Créer/trouver le fournisseur
    siren = sd["entities"].get("siren", "")
    entreprise = sd["entities"].get("entreprise", "Inconnu")
    siret = sd["entities"].get("siret", "")

    if siren and len(siren) == 9:
        try:
            existing = api.get_fournisseur_by_siren(siren)
            if existing:
                logger.info(f"[crm] Fournisseur existant: {entreprise} (id={existing['id']})")
            else:
                resp = api.create_fournisseur(
                    nom=entreprise,
                    siren=siren,
                    siret=siret if len(siret) == 14 else None,
                    adresse=None,
                )
                stats["fournisseurs_created"] += 1
                logger.info(f"[crm] Fournisseur créé: {entreprise} (id={resp.get('data', {}).get('id')})")
        except Exception as e:
            logger.error(f"[crm] Erreur fournisseur {entreprise}: {e}")

    # 2. Créer l'extraction
    try:
        extraction_data = {
            "siren": siren if len(siren) == 9 else None,
            "siret": siret if len(siret) == 14 else None,
            "montant_ht": sd["financials"].get("montant_ht"),
            "montant_ttc": sd["financials"].get("montant_ttc"),
            "taux_tva": 20.0,
            "nom_fournisseur": entreprise,
            "donnees_completes": json.dumps(sd, ensure_ascii=False),
            "confiance_globale": 95.0 if sd["validation"].get("is_valid") else 60.0,
        }
        api.create_extraction(document_id, extraction_data)
        stats["extractions_created"] += 1
        logger.info(f"[crm] Extraction créée pour document {document_id}")
    except Exception as e:
        logger.error(f"[crm] Erreur extraction doc {document_id}: {e}")

    # 3. Mettre à jour le type de document
    doc_type = sd.get("document_type", "autre")
    if doc_type in ("facture", "devis", "attestation", "autre"):
        try:
            api.update_document_type(document_id, doc_type)
            stats["types_updated"] += 1
        except Exception as e:
            logger.error(f"[crm] Erreur update type doc {document_id}: {e}")
