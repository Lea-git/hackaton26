"""
model_extract.py — Extraction structurée via modèle Donut fine-tuné.

Enrichit les résultats OCR avec les champs extraits directement depuis
les images de documents (emetteur, siret, iban, montants, dates, etc.).
"""

import io
import os
import re
import logging
import tempfile

from minio import Minio
from PIL import Image

from docuhack_tasks.config import (
    MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE,
    BUCKET_RAW, MODEL_PATH,
)

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif")

# Chargement unique du modèle au démarrage du worker
_processor = None
_model = None


def _load_model():
    global _processor, _model
    if _processor is None:
        from transformers import DonutProcessor, VisionEncoderDecoderModel
        logger.info(f"[model] Chargement Donut depuis {MODEL_PATH}")
        _processor = DonutProcessor.from_pretrained(MODEL_PATH)
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)
        _model.eval()
        logger.info("[model] Modèle prêt")
    return _processor, _model


def _run_donut(image_pil):
    """Lance l'inférence Donut sur une image PIL. Retourne un dict de champs."""
    import torch
    processor, model = _load_model()

    task_prompt = "<s_gt_parse>"
    decoder_input_ids = processor.tokenizer(
        task_prompt, add_special_tokens=False, return_tensors="pt"
    ).input_ids

    pixel_values = processor(image_pil, return_tensors="pt").pixel_values

    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = (
        sequence
        .replace(processor.tokenizer.eos_token, "")
        .replace(processor.tokenizer.pad_token, "")
    )
    # Supprimer le premier token de tâche
    sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()

    parsed = processor.token2json(sequence)
    if isinstance(parsed, dict):
        return parsed.get("gt_parse", parsed)
    return {}


def model_extract(**context):
    """Enrichit les résultats OCR avec les champs extraits par le modèle Donut."""
    ti = context["ti"]
    ocr_results = ti.xcom_pull(task_ids="ocr_extract")

    if not ocr_results:
        logger.info("[model] Aucun document à traiter")
        return []

    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )

    enriched = []
    for doc in ocr_results:
        filename = doc["filename"]
        ext = os.path.splitext(filename)[1].lower()

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name

        try:
            minio_client.fget_object(BUCKET_RAW, filename, tmp_path)

            if ext == ".pdf":
                from pdf2image import convert_from_path
                pages = convert_from_path(tmp_path)
                image_pil = pages[0].convert("RGB")
            elif ext in IMAGE_EXTENSIONS:
                image_pil = Image.open(tmp_path).convert("RGB")
            else:
                logger.warning(f"[model] Format non supporté: {filename}, passage sans inférence")
                enriched.append({**doc, "model_fields": {}})
                continue

            model_fields = _run_donut(image_pil)
            logger.info(f"[model] {filename} → champs extraits: {list(model_fields.keys())}")
            enriched.append({**doc, "model_fields": model_fields})

        except Exception as e:
            logger.error(f"[model] Erreur sur {filename}: {e}")
            enriched.append({**doc, "model_fields": {}})
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return enriched
