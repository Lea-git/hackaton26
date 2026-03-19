import json
import tempfile
from pathlib import Path

from PIL import Image
from pdf2image import convert_from_path

from extraction.extract import DocumentExtractor
from datalake import DataLakeClient

MODEL_PATH = "./extraction/model"
POPPLER_PATH = "C:/poppler/poppler-25.12.0/Library/bin"
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}


def load_as_image(local_path: str) -> Image.Image:
    """Converts any supported file (PDF, JPG, PNG...) to a PIL Image."""
    path = Path(local_path)
    if path.suffix.lower() == ".pdf":
        pages = convert_from_path(str(path), dpi=300, poppler_path=POPPLER_PATH)
        return pages[0]
    else:
        return Image.open(path).convert("RGB")


def run_extraction_pipeline(raw_path: str, extractor=None, client=None) -> dict:
    """
    Télécharge un document depuis la zone brute, extrait les champs
    et uploade le résultat en zone clean.

    Args:
        raw_path  : chemin dans la raw zone, ex: "2024/factures/facture_001.pdf"
        extractor : instance de DocumentExtractor (optionnel, pour réutilisation)
        client    : instance de DataLakeClient (optionnel, pour réutilisation)

    Returns:
        Dictionnaire des champs extraits
    """
    if client is None:
        client = DataLakeClient()
    if extractor is None:
        extractor = DocumentExtractor(MODEL_PATH)

    clean_path = str(Path(raw_path).with_suffix(".json"))

    with tempfile.NamedTemporaryFile(suffix=Path(raw_path).suffix, delete=True) as tmp:
        client.download_raw(raw_path, tmp.name)
        image = load_as_image(tmp.name)
        fields = extractor.extract(image)

    client.upload_clean(clean_path, json.dumps(fields, ensure_ascii=False, indent=2))
    return fields


def run_batch_extraction_pipeline(prefix: str = "") -> None:
    """
    Parcourt tous les fichiers de la raw zone et lance le pipeline
    d'extraction sur chacun.

    Args:
        prefix: filtrer par chemin, ex: "2024/factures/"
                laisser vide pour tout traiter
    """
    client = DataLakeClient()
    extractor = DocumentExtractor(MODEL_PATH)

    objects = client.list_objects(zone="raw", prefix=prefix)

    if not objects:
        print("Aucun fichier trouvé dans la raw zone.")
        return

    print(f"{len(objects)} fichier(s) trouvé(s), démarrage du traitement...\n")

    success = 0
    errors = 0

    for obj in objects:
        raw_path = obj["name"]
        ext = Path(raw_path).suffix.lower()

        if ext not in SUPPORTED_EXTENSIONS:
            print(f"  [SKIP] Format non supporté : {raw_path}")
            continue

        print(f"  Traitement : {raw_path}")
        try:
            run_extraction_pipeline(raw_path, extractor=extractor, client=client)
            success += 1
        except Exception as e:
            print(f"  [ERREUR] {raw_path} : {e}")
            errors += 1
            continue

    print(f"\nBatch terminé — {success} succès, {errors} erreur(s).")
