# Extraction de documents avec Donut

Modèle [Donut](https://github.com/clovaai/donut) fine-tuné pour extraire des champs structurés depuis des documents professionnels français.

---

## Prérequis système

**Poppler** — requis pour la conversion PDF vers image.
- Windows : télécharger depuis [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), extraire l'archive, et renseigner `POPPLER_PATH` dans `extraction/prepare_train_data.py` en pointant vers le dossier `bin`.
- Linux : `sudo apt install poppler-utils`
- Mac : `brew install poppler`

**GPU NVIDIA + CUDA** — requis pour l'entraînement. Vérifier la version CUDA avec `nvidia-smi`.

---

## Installation

```bash
pip install -r requirements.txt
```

> PyTorch est installé avec le support CUDA 12.4. Si votre version CUDA est différente, mettez à jour le `--extra-index-url` et les versions de torch dans `requirements.txt`. Voir [pytorch.org](https://pytorch.org/get-started/locally/).

---

## Structure du projet

```
extraction/
├── prepare_train_data.py   # Convertit les PDFs/images bruts → donut_dataset/
├── train.py                # Fine-tune le modèle Donut
├── extractor.py            # Module d'extraction réutilisable
├── inference.py            # Script d'inférence pour des tests rapide
├── model/                  # Modèle sauvegardé après entraînement
output/
├── raw_zone/               # PDFs et images sources bruts
└── ground_truth.json       # Labels de vérité terrain
donut_dataset/
├── train/                  # Images d'entraînement + metadata.jsonl
└── test/                   # Images de test + metadata.jsonl
```

---

## Utilisation

### 1. Préparer les données
```bash
python ./extraction/prepare_train_data.py
```

### 2. Entraîner le modèle
```bash
python ./extraction/train.py
```

### 3. Extraire les champs d'un document
```python
from extractor import DocumentExtractor
from PIL import Image

MODEL_PATH = "./extraction/model"
extractor = DocumentExtractor(MODEL_PATH)

image = Image.open(image_path).convert("RGB")

# Accepte une Image PIL
fields = extractor.extract(image)
print(fields)
# {"emetteur": "...", "siret": "...", "total_ttc": "...", ...}
```