# Validation Engine - Detection

Ce module valide des documents JSON depuis MinIO:

1. lecture depuis la zone clean (`clean-documents`)
2. analyse (SIRET + maths + modele ML)
3. ecriture en zone curated (`curated-documents`)

Le script principal est `document_validator.py`.

## Prerequis

Depuis la racine du repo:

```powershell
c:/Master2/Hackathon/.venv/Scripts/python.exe -m pip install -r validation_engine/backend/detection/requirements.txt
```

MinIO doit etre lance:

```powershell
cd validation_engine/backend/hackaton26-datalake_branche
docker compose up -d
```

Console MinIO: `http://localhost:9001`

- user: `admin`
- password: `admin1234`

## Utilisation rapide (mode modele fige .pkl)

### 1) Exporter le modele fige

```powershell
c:/Master2/Hackathon/.venv/Scripts/python.exe validation_engine/backend/detection/document_validator.py --export-frozen-model --model-path validation_engine/backend/detection/models/isolation_forest.pkl
```

Cela cree le fichier:

- `validation_engine/backend/detection/models/isolation_forest.pkl`

### 2) Lancer la validation clean -> curated avec modele obligatoire

```powershell
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
c:/Master2/Hackathon/.venv/Scripts/python.exe validation_engine/backend/detection/document_validator.py --mode minio --model-path validation_engine/backend/detection/models/isolation_forest.pkl --require-frozen-model --clean-prefix 2026/demo/ --curated-prefix 2026/demo_test_$stamp/
```

Exemple attendu en sortie console:

```json
{
  "processed": 8,
  "written": 8,
  "failed": 0
}
```

## Comment verifier que tout fonctionne

1. Dans MinIO, verifier que les entrees existent dans:
   - `clean-documents/2026/demo/`
2. Verifier que les sorties sont creees dans:
   - `curated-documents/2026/demo_test_<timestamp>/`
3. Ouvrir un JSON de sortie et verifier:
   - `validation.metadata.model.source = "frozen_pkl"`

Commande CLI de verification (exemple):

```powershell
docker run --rm --entrypoint /bin/sh --network container:minio-datalake minio/mc -c "mc alias set local http://127.0.0.1:9000 admin admin1234; mc cat local/curated-documents/2026/demo_test_YYYYMMDD_HHMMSS/dataset_SCN1_devis_011.json"
```

## Interpretation des statuts

- `VALID`: checks SIRET + maths + ML OK
- `SUSPECT`: SIRET/maths OK, mais ML detecte une anomalie
- `INVALID`: echec SIRET ou echec maths

Note: certains jeux de test contiennent des valeurs non numeriques (ex: `1963<unk>.8`) ou vides. Le pipeline reste fonctionnel, mais ces documents peuvent etre classes `INVALID` ou `SUSPECT`.

## Variables d environnement utiles

- `MINIO_ENDPOINT` (defaut: `localhost:9000`)
- `MINIO_ACCESS_KEY` (defaut: `admin`)
- `MINIO_SECRET_KEY` (defaut: `admin1234`)
- `MINIO_SECURE` (defaut: `false`)
- `MINIO_CLEAN_BUCKET` (defaut: `clean-documents`)
- `MINIO_CURATED_BUCKET` (defaut: `curated-documents`)
- `MINIO_CLEAN_PREFIX` (defaut: `2026/demo/`)
- `MINIO_CURATED_PREFIX` (defaut: `2026/demo/`)
- `VALIDATOR_MODEL_PATH` (defaut: `validation_engine/backend/detection/models/isolation_forest.pkl`)

## Pour Airflow (commande de task)

```powershell
c:/Master2/Hackathon/.venv/Scripts/python.exe validation_engine/backend/detection/document_validator.py --mode minio --model-path validation_engine/backend/detection/models/isolation_forest.pkl --require-frozen-model --clean-prefix 2026/demo/ --curated-prefix 2026/demo_airflow/
```
