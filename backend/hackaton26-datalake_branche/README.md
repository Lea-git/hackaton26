# Documentation — Data Lake MinIO (Hackathon 2026)

## Rôle dans le projet

Etant responsable du stockage distribué.Ma mission est la fondation sur laquelle tous les autres services s'appuient :

- L'étudiant 2 (OCR) lit depuis la Raw zone et écrit dans la Clean zone
- L'étudiant 5 (validation) lit depuis la Clean zone et écrit dans la Curated zone
- L'étudiant 3 (front-end) consomme la Curated zone via l'API
- L'étudiant 6 (Airflow) orchestre tous ces flux

---

## Architecture des 3 zones

```
Upload document
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│                    MinIO Data Lake                       │
│                                                         │
│  ┌─────────────┐   OCR    ┌─────────────┐  NER  ┌──────────────┐
│  │  Raw zone   │ ───────► │ Clean zone  │ ─────► │Curated zone  │
│  │             │          │             │        │              │
│  │ Fichiers    │          │ Texte OCR   │        │ JSON         │
│  │ bruts       │          │ nettoyé     │        │ structuré    │
│  │ .pdf .jpg   │          │ .txt        │        │ .json        │
│  └─────────────┘          └─────────────┘        └──────────────┘
│   bucket:                  bucket:                bucket:
│   raw-documents            clean-documents        curated-documents
└─────────────────────────────────────────────────────────┘
                                                          │
                                                          ▼
                                              CRM · Outil conformité
```

### Raw zone — `raw-documents`

- Contient les fichiers originaux tels qu'uploadés (PDF, JPEG, PNG, TIFF)
- **Immutables** : on n'y touche jamais après dépôt
- Structure recommandée : `{année}/{type_document}/{nom_fichier}`
- Exemple : `2024/factures/facture_acme_001.pdf`

### Clean zone — `clean-documents`

- Contient le texte extrait par OCR, nettoyé (encodage UTF-8 unifié, espaces normalisés)
- Même arborescence que la Raw zone, extension `.txt`
- Exemple : `2024/factures/facture_acme_001.txt`

### Curated zone — `curated-documents`

- Contient les données structurées extraites par le module NER (étudiant 5)
- Format JSON avec schéma standardisé
- Exemple : `2024/factures/facture_acme_001.json`

---

## Structure JSON — Curated zone

```json
{
  "document_id": "facture_acme_001",
  "document_type": "facture",
  "fournisseur": "ACME SAS",
  "siret": "12345678900012",
  "date_emission": "2024-03-15",
  "date_expiration": null,
  "montant_ht": 1000.0,
  "tva": 200.0,
  "montant_ttc": 1200.0,
  "devise": "EUR",
  "coherence_ok": true,
  "anomalies": [],
  "ingested_at": "2024-03-15T10:30:00"
}
```

---

## Démarrage rapide

### 1. Lancer MinIO

```bash
docker-compose up -d
```

MinIO démarre sur :

- API S3 : http://localhost:9000
- Console Web : http://localhost:9001 avec les identifiants pour y accéder

Le service `minio-init` crée automatiquement les 3 buckets au premier démarrage.

### 2. Installer les dépendances Python

```bash
pip install minio python-dotenv
```

---

---

## Arborescence recommandée des objets

```
{bucket}/
└── {année}/
    └── {type_document}/
        └── {nom_fichier}.{ext}

Exemples :
  raw-documents/2024/factures/facture_acme_001.pdf
  clean-documents/2024/factures/facture_acme_001.txt
  curated-documents/2024/factures/facture_acme_001.json
```

---

## Intégration avec les autres modules

### Depuis le module OCR (étudiant 2)

```python
from datalake import DataLakeClient

client = DataLakeClient()

# 1. Télécharger le PDF brut
client.download_raw("2024/factures/facture_001.pdf", "/tmp/facture_001.pdf")

# 2. Appliquer l'OCR (Tesseract / EasyOCR)
texte_ocr = run_ocr("/tmp/facture_001.pdf")

# 3. Stocker le résultat en Clean zone
client.upload_clean("2024/factures/facture_001.txt", texte_ocr)
```

### Depuis le module NER/Validation (étudiant 5)

```python
# 1. Lire le texte OCR
texte = client.download_clean("2024/factures/facture_001.txt")

# 2. Extraire les entités
entites = run_ner(texte)

# 3. Valider la cohérence inter-documents
entites["coherence_ok"] = check_coherence(entites)

# 4. Stocker en Curated zone
client.upload_curated("2024/factures/facture_001.json", entites)
```

### Depuis Airflow (étudiant 6)

```python
from airflow.operators.python import PythonOperator
from datalake import DataLakeClient

def task_upload_raw(**context):
    client = DataLakeClient()
    filepath = context["dag_run"].conf["filepath"]
    client.upload_raw(f"2024/factures/{Path(filepath).name}", filepath)
```

---

## Commandes utiles — Console MinIO

Accéder à http://localhost:9001 avec les identifiants pour :

- Visualiser les fichiers dans chaque bucket
- Télécharger manuellement un document
- Surveiller l'espace disque utilisé

---

## Checklist de livraison (étudiant 4)

- [ ] `docker-compose.yml` fonctionnel et testé
- [ ] 3 buckets créés automatiquement au démarrage
- [ ] `datalake.py` : upload/download dans les 3 zones
- [ ] Test complet `python datalake.py` sans erreur
- [ ] Variables d'environnement documentées (`.env`)
- [ ] Intégration validée avec étudiant 2 (OCR) et étudiant 5 (NER)
- [ ] Console MinIO accessible sur http://localhost:9001
