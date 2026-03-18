"""
laravel_client.py — Client HTTP pour l'API Laravel DocuHack.
"""

import requests
import logging

from airflow.tasks.config import LARAVEL_API_URL

logger = logging.getLogger(__name__)


class LaravelAPIClient:
    def __init__(self, base_url=None):
        self.base_url = (base_url or LARAVEL_API_URL).rstrip("/")

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, json_data=None):
        url = f"{self.base_url}{path}"
        resp = requests.post(url, json=json_data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _patch(self, path, json_data=None):
        url = f"{self.base_url}{path}"
        resp = requests.patch(url, json=json_data, timeout=30)
        resp.raise_for_status()
        return resp.json()

    # ── Documents ──────────────────────────────────────────

    def get_documents(self, nom_fichier=None):
        params = {}
        if nom_fichier:
            params["nom_fichier"] = nom_fichier
        return self._get("/documents", params=params)

    def create_document(self, nom, chemin, type_doc, mime, taille):
        return self._post("/documents", {
            "nom_fichier_original": nom,
            "chemin_stockage": chemin,
            "type_document": type_doc,
            "mime_type": mime,
            "taille_fichier": taille,
        })

    def update_document_type(self, document_id, type_doc):
        return self._patch(f"/documents/{document_id}/type", {
            "type_document": type_doc,
        })

    # ── Fournisseurs ───────────────────────────────────────

    def get_fournisseurs(self):
        return self._get("/fournisseurs")

    def get_fournisseur_by_siren(self, siren):
        resp = self.get_fournisseurs()
        fournisseurs = resp.get("data", [])
        for f in fournisseurs:
            if f.get("siren") == siren:
                return f
        return None

    def create_fournisseur(self, nom, siren, siret=None, adresse=None):
        return self._post("/fournisseurs", {
            "nom": nom,
            "siren": siren,
            "siret": siret,
            "adresse": adresse,
        })

    # ── Extractions ────────────────────────────────────────

    def create_extraction(self, document_id, data):
        return self._post(f"/documents/{document_id}/extractions", data)

    # ── Alertes ────────────────────────────────────────────

    def create_alerte(self, type_alerte, niveau, message, documents_concernes, fournisseur_id=None, details=None):
        import json
        payload = {
            "type": type_alerte,
            "niveau": niveau,
            "message": message,
            "documents_concerenes": documents_concernes,
            "fournisseur_id": fournisseur_id,
            "details": json.dumps(details) if details else None,
        }
        return self._post("/alertes", payload)
