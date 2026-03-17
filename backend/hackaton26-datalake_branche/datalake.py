"""
datalake.py
===========
Client Python pour interagir avec le Data Lake MinIO (3 zones).

Installation des dépendances :
    pip install minio python-dotenv

Usage rapide :
    from datalake import DataLakeClient

    client = DataLakeClient()
    client.upload_raw("facture_001.pdf", "/chemin/local/facture_001.pdf")
    client.upload_clean("facture_001.txt", b"Texte OCR extrait...")
    client.upload_curated("facture_001.json", {"siret": "12345678900012", "montant_ttc": 1200.0})
"""

import json
import io
import os
from datetime import datetime
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from dotenv import find_dotenv,load_dotenv

# ─────────────────────────────────────────────────────────────
#  Configuration de l'environnement
# ─────────────────────────────────────────────────────────────
dotenv_path=find_dotenv()
load_dotenv(dotenv_path)

MINIO_ENDPOINT  = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS    = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET    = os.getenv("MINIO_SECRET_KEY")
MINIO_SECURE    = os.getenv("MINIO_SECURE").lower() == "true"

# Noms des 3 buckets (zones du Data Lake)
BUCKET_RAW      = "raw-documents"
BUCKET_CLEAN    = "clean-documents"
BUCKET_CURATED  = "curated-documents"


# ─────────────────────────────────────────────────────────────
#  Client principal
# ─────────────────────────────────────────────────────────────

class DataLakeClient:
    """
    Interface unifiée pour les 3 zones du Data Lake.

    Zones :
        raw      → documents bruts (PDF, images)
        clean    → texte OCR nettoyé (.txt)
        curated  → données structurées JSON
    """

    def __init__(self):
        self.client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS,
            secret_key=MINIO_SECRET,
            secure=MINIO_SECURE,
        )
        self._ensure_buckets()

    # ── Initialisation ────────────────────────────────────────

    def _ensure_buckets(self):
        """Crée les buckets s'ils n'existent pas encore."""
        for bucket in [BUCKET_RAW, BUCKET_CLEAN, BUCKET_CURATED]:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                print(f"[✓] Bucket créé : {bucket}")
            else:
                print(f"[·] Bucket existant : {bucket}")

    # ── RAW ZONE ──────────────────────────────────────────────

    def upload_raw(self, object_name: str, file_path: str) -> str:
        """
        Dépose un document brut (PDF, image) dans la Raw zone.

        Args:
            object_name : nom de l'objet dans MinIO (ex: "2024/facture_001.pdf")
            file_path   : chemin local du fichier

        Returns:
            L'object_name déposé
        """
        path = Path(file_path)
        content_type = _guess_content_type(path.suffix)

        self.client.fput_object(
            BUCKET_RAW,
            object_name,
            file_path,
            content_type=content_type,
        )
        print(f"[RAW ✓] {object_name} → {BUCKET_RAW}")
        return object_name

    def download_raw(self, object_name: str, dest_path: str):
        """Télécharge un document brut depuis la Raw zone."""
        self.client.fget_object(BUCKET_RAW, object_name, dest_path)
        print(f"[RAW ↓] {object_name} → {dest_path}")

    # ── CLEAN ZONE ────────────────────────────────────────────

    def upload_clean(self, object_name: str, text_content: str | bytes) -> str:
        """
        Dépose le texte OCR nettoyé dans la Clean zone.

        Args:
            object_name  : nom de l'objet (ex: "2024/facture_001.txt")
            text_content : texte brut (str ou bytes)

        Returns:
            L'object_name déposé
        """
        if isinstance(text_content, str):
            text_content = text_content.encode("utf-8")

        data   = io.BytesIO(text_content)
        length = len(text_content)

        self.client.put_object(
            BUCKET_CLEAN,
            object_name,
            data,
            length,
            content_type="text/plain; charset=utf-8",
        )
        print(f"[CLEAN ✓] {object_name} → {BUCKET_CLEAN}")
        return object_name

    def download_clean(self, object_name: str) -> str:
        """
        Récupère le texte OCR depuis la Clean zone.

        Returns:
            Le texte sous forme de str
        """
        response = self.client.get_object(BUCKET_CLEAN, object_name)
        try:
            return response.read().decode("utf-8")
        finally:
            response.close()
            response.release_conn()

    # ── CURATED ZONE ──────────────────────────────────────────

    def upload_curated(self, object_name: str, data: dict) -> str:
        """
        Dépose des données structurées JSON dans la Curated zone.

        Args:
            object_name : nom de l'objet (ex: "2024/facture_001.json")
            data        : dictionnaire Python sérialisé en JSON

        Returns:
            L'object_name déposé
        """
        payload    = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        length     = len(payload)
        stream     = io.BytesIO(payload)

        self.client.put_object(
            BUCKET_CURATED,
            object_name,
            stream,
            length,
            content_type="application/json",
        )
        print(f"[CURATED ✓] {object_name} → {BUCKET_CURATED}")
        return object_name

    def download_curated(self, object_name: str) -> dict:
        """
        Récupère un document JSON depuis la Curated zone.

        Returns:
            Un dictionnaire Python
        """
        response = self.client.get_object(BUCKET_CURATED, object_name)
        try:
            return json.loads(response.read().decode("utf-8"))
        finally:
            response.close()
            response.release_conn()

    # ── UTILITAIRES ───────────────────────────────────────────

    def list_objects(self, zone: str = "raw", prefix: str = "") -> list[dict]:
        """
        Liste les objets dans une zone.

        Args:
            zone   : "raw" | "clean" | "curated"
            prefix : filtre par préfixe (ex: "2024/")

        Returns:
            Liste de dict {name, size, last_modified}
        """
        bucket = _zone_to_bucket(zone)
        objects = self.client.list_objects(bucket, prefix=prefix, recursive=True)
        result = []
        for obj in objects:
            result.append({
                "name":          obj.object_name,
                "size_kb":       round(obj.size / 1024, 2),
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else None,
            })
        return result

    def object_exists(self, zone: str, object_name: str) -> bool:
        """Vérifie si un objet existe dans une zone."""
        bucket = _zone_to_bucket(zone)
        try:
            self.client.stat_object(bucket, object_name)
            return True
        except S3Error:
            return False

    def get_stats(self) -> dict:
        """Retourne un résumé du contenu des 3 zones."""
        stats = {}
        for zone, bucket in [("raw", BUCKET_RAW), ("clean", BUCKET_CLEAN), ("curated", BUCKET_CURATED)]:
            objects = list(self.client.list_objects(bucket, recursive=True))
            total_kb = sum(o.size for o in objects) / 1024
            stats[zone] = {
                "bucket":       bucket,
                "nb_objects":   len(objects),
                "total_size_kb": round(total_kb, 2),
            }
        return stats


# ─────────────────────────────────────────────────────────────
#  Helpers internes
# ─────────────────────────────────────────────────────────────

def _zone_to_bucket(zone: str) -> str:
    mapping = {
        "raw":     BUCKET_RAW,
        "clean":   BUCKET_CLEAN,
        "curated": BUCKET_CURATED,
    }
    if zone not in mapping:
        raise ValueError(f"Zone inconnue : '{zone}'. Valeurs acceptées : raw, clean, curated")
    return mapping[zone]


def _guess_content_type(suffix: str) -> str:
    types = {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".tiff": "image/tiff",
        ".tif":  "image/tiff",
    }
    return types.get(suffix.lower(), "application/octet-stream")


