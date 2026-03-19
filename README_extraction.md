# Extraction de documents avec Donut

Modèle [Donut](https://github.com/clovaai/donut) fine-tuné pour extraire des champs structurés depuis des documents professionnels français.

---

## Prérequis système

**Poppler** — requis pour la conversion PDF vers image.
- Windows : télécharger depuis [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases), extraire l'archive, et renseigner `POPPLER_PATH` dans `extraction/pipeline.py` et `extraction/prepare_train_data.py` en pointant vers le dossier `bin`.
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
├── evaluate.py             # Métriques d'évaluation sur le jeu de test
├── extract.py              # Module d'extraction réutilisable
├── pipeline.py             # Orchestre téléchargement, extraction et upload
├── inference.py            # Script d'inférence pour des tests rapides
└── model/                  # Modèle sauvegardé après entraînement
run_pipeline.py             # Point d'entrée pour lancer le batch
output/
├── raw_zone/               # PDFs et images sources bruts
└── ground_truth.json       # Labels de vérité terrain
donut_dataset/              # Généré par prepare_train_data.py
├── train/                  # Images d'entraînement + metadata.jsonl
└── test/                   # Images de test + metadata.jsonl
```

---

## Utilisation

### 1. Préparer les données
```bash
python -m extraction.prepare_train_data
```

### 2. Entraîner le modèle
```bash
python -m extraction.train
```

### 3. Pipeline batch (datalake raw → extraction → datalake clean)
Traite tous les documents présents dans la raw zone et pousse les résultats en zone clean :
```bash
python run_pipeline.py
```

### 4. Pipeline sur un seul document
```python
from extraction.pipeline import run_extraction_pipeline

fields = run_extraction_pipeline("dataset/facture_001.pdf")
# résultat aussi uploadé dans "dataset/facture_001.json"
```

### 5. Extraction standalone (sans datalake)
```python
from extraction.extract import DocumentExtractor
from PIL import Image

MODEL_PATH = "./extraction/model"
extractor = DocumentExtractor(MODEL_PATH)

image = Image.open("./document.jpg").convert("RGB")
fields = extractor.extract(image)
print(fields)
# {"emetteur": "...", "siret": "...", "total_ttc": "...", ...}
```