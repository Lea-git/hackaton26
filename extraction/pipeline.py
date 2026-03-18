import tempfile
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from extraction.extract import DocumentExtractor
from extraction.prepare_train_data import POPPLER_PATH
from datalake import DataLakeClient


MODEL_PATH = "./donut_invoice_model"


def load_as_image(local_path: str) -> Image.Image:
    """Converts any supported file (PDF, JPG, PNG...) to a PIL Image."""
    path = Path(local_path)
    if path.suffix.lower() == ".pdf":
        pages = convert_from_path(str(path), dpi=300, poppler_path=POPPLER_PATH)
        return pages[0]  # first page
    else:
        return Image.open(path).convert("RGB")

def run_extraction_pipeline(raw_path: str) -> dict:
    client = DataLakeClient()
    extractor = DocumentExtractor(MODEL_PATH)
    clean_path = str(Path(raw_path).with_suffix(".json"))

    with tempfile.NamedTemporaryFile(suffix=Path(raw_path).suffix, delete=True) as tmp:
        client.download_raw(raw_path, tmp.name)
        image = load_as_image(tmp.name)
        fields = extractor.extract(image)

    client.upload_clean(clean_path, fields)
    return fields
