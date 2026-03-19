"""
config.py — Constantes partagées pour le pipeline Airflow DocuHack.
"""

import os

# ── MinIO ──────────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "admin1234")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

BUCKET_RAW = "raw-documents"
BUCKET_CLEAN = "clean-documents"
BUCKET_CURATED = "curated-documents"

# ── Laravel API ────────────────────────────────────────────
LARAVEL_API_URL = os.getenv("LARAVEL_API_URL", "http://frontend:80/api")

# ── Ground Truth ───────────────────────────────────────────
GROUND_TRUTH_PATH = os.getenv("GROUND_TRUTH_PATH", "/opt/airflow/backend/output/ground_truth.json")

# ── Modèle Donut ───────────────────────────────────────────
MODEL_PATH = os.getenv("MODEL_PATH", "/opt/airflow/model")

# ── Mapping scénario → description ─────────────────────────
SCENARIO_MAP = {
    "SCN-1": "Fournisseur légitime – documents valides",
    "SCN-2": "Fournisseur légitime – erreurs OCR mineures",
    "SCN-3": "Fournisseur suspect – incohérences SIRET",
    "SCN-4": "Fournisseur frauduleux – documents falsifiés",
    "SCN-5": "Multi-fournisseurs – chaîne de sous-traitance",
}

# ── Mapping extensions → content types ─────────────────────
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}
