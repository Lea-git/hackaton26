# Dataset Hackathon 2026 — Étudiant 1

Dataset synthétique de documents administratifs français destiné à entraîner et évaluer la pipeline OCR / classification / détection d'anomalies du projet hackathon.

---

## Structure du projet

```
dataset-hackaton/
├── Backend/
│ ├── app.py
│ ├── generate_dataset.py   # Script principal de génération
│ ├── datalake.py           # Script pour MinIO / datalake
│ ├── companies_pool.json   # Pool de 20 entreprises réelles (SIRET INSEE)
│ ├── requirements.txt
│ └── output/
│ ├── raw_zone/ # 170 documents générés (PDF + JPG) ← Raw Zone du Data Lake
│ ├── ground_truth.json        # Vérité terrain complète (170 entrées)
│ ├── ground_truth_train.json  # 80% — entraînement (136 docs)
│ └── ground_truth_test.json   # 20% — évaluation (34 docs)
├── Frontend/
│ ├── Dockerfile
│ └── ... # Projet Laravel/Vue minimal
└── docker-compose.yml
```

---

## Prérequis

```bash
pip install faker reportlab pillow
```

---
## Docker 

Installer Docker Desktop
Vérifier que Docker fonctionne
 docker --version
 docker composer version
 Lancer l’application avec Docker

Tout est conteneurisé : backend Python, frontend Laravel/Vue et MinIO pour le datalake.

1️⃣ Build et démarrage des conteneurs

Depuis la racine du projet :

docker compose up --build

Backend : exposé sur http://localhost:8000

Frontend : exposé sur http://localhost:8080

MinIO (datalake) : console web sur http://localhost:9001
, API S3 sur http://localhost:9000

Credentials :

User : admin

Password : password123

2️⃣ Accéder au conteneur backend pour générer le dataset
docker compose exec backend python generate_dataset.py

Les fichiers seront créés dans /app/output/ et persistés sur ton PC grâce au volume Docker.

3️⃣ Accéder au datalake MinIO
docker compose exec minio mc alias set local http://localhost:9000 admin password123
docker compose exec backend python datalake.py   # Pour uploader les fichiers dans MinIO

## Générer le dataset

```bash
python generate_dataset.py
```

Le script est **déterministe** (seed fixe à `42`) : il produit toujours exactement les mêmes fichiers.
Durée : ~1-2 minutes.

---

## Chiffres clés

| Métrique | Valeur |
|---|---|
| Total documents | **170** |
| Format PDF natif | 105 |
| Format image (JPG) | 65 |
| Split entraînement | 136 (80%) |
| Split test | 34 (20%) |
| Entreprises dans le pool | 20 |

### Répartition par type de document

| Type | Nombre |
|---|---|
| Facture | 88 |
| Devis | 25 |
| URSSAF | 31 |
| Kbis | 11 |
| Attestation SIRET | 10 |
| RIB | 5 |

---

## Les 10 scénarios

| Scénario | Nb docs | Format | Description | Anomalie injectée |
|---|---|---|---|---|
| **SCN-1** | 30 | PDF | Documents parfaits, lisibles | Aucune |
| **SCN-2** | 25 | JPG | Scans bruités (rotation, flou, grain) | `dirty_scan` |
| **SCN-3** | 15 | PDF | Factures avec SIRET falsifié | `siret_mismatch` |
| **SCN-4** | 15 | PDF | Attestations URSSAF expirées | `urssaf_expired` |
| **SCN-5** | 10 | PDF | Erreurs de calcul HT + TVA ≠ TTC | `vat_calculation_error` |
| **SCN-6** | 15 | JPG | Photos smartphone (perspective, ombre) | `smartphone_photo` |
| **SCN-7** | 15 | JPG | Combinés : dégradation + erreur métier | `combined_*` |
| **SCN-8** | 25 | PDF/JPG | Packs inter-documents (5 docs liés) | `siret_cross_mismatch` (cas B) |
| **SCN-9** | 10 | JPG | Très dégradés (pixelisé, taché) | `heavy_degradation` |
| **SCN-10** | 10 | PDF | Zones masquées / champs partiels | `partial_occlusion` |

---

## Format du ground truth

Chaque entrée de `ground_truth.json` contient :

```json
{
  "filename": "SCN3_siret_mismatch_001.pdf",
  "scenario": "SCN-3",
  "doc_type": "facture",
  "emetteur": "Moustapha ABDI ALI",
  "valideur": "Yannis Bouttier",
  "entreprise": "JLB LOGICIELS & SERVICES",
  "siret_attendu": "52935972100014",   ← SIRET officiel de l'entreprise (source INSEE)
  "siret_affiche": "96256706492763",   ← SIRET écrit sur le document (falsifié ici)
  "client": "C.RAPINE DATA & ANALYTICS",
  "total_ht": 51517.88,
  "tva": 10303.58,
  "total_ttc": 61821.46,
  "is_valid": false,                   ← false si une anomalie est présente
  "error_type": "siret_mismatch",      ← null si document valide
  "linked_files": [],                  ← liste des docs liés (SCN-8 uniquement)
  "category": "FACTURE",
  "format": "pdf",
  "difficulty": "easy",               ← easy / medium / hard
  "split": "train"                     ← train / test
}
```
### Notes Docker


Tous les fichiers Python et JSON sont dans Backend/.

Volumes Docker garantissent que les fichiers générés restent sur ton PC même après arrêt des conteneurs.

### Règle de vérification SIRET

> L'OCR extrait `siret_affiche` depuis le document. La validation croise ensuite ce SIRET avec `siret_attendu` (source SIRENE/companies_pool). Si `siret_affiche ≠ siret_attendu` → anomalie détectée.

---

## Rôle de chaque fichier pour la pipeline

| Fichier | Utilisé par | Pour quoi faire |
|---|---|---|
| `raw_zone/*.pdf` / `*.jpg` | **Étudiant 2 (OCR)** | Extraire le texte brut |
| `ground_truth_train.json` | **Étudiant 2 / Étudiant 5** | Entraîner les modèles |
| `ground_truth_test.json` | **Étudiant 2 / Étudiant 5** | Évaluer les modèles (données jamais vues) |
| `ground_truth.json` | **Étudiant 4 (Data Lake)** | Alimenter la Curated Zone |
| `companies_pool.json` | **Étudiant 5 (Validation)** | Référentiel SIRET pour détecter les fraudes |

### Flux de la pipeline

```
raw_zone/  (Étudiant 1 — ce dataset)
    ↓ OCR (Étudiant 2)
Clean Zone — texte extrait
    ↓ NER / structuration (Étudiant 2)
Curated Zone — JSON structuré (Étudiant 4)
    ↓ Validation (Étudiant 5)
Anomalies détectées → CRM / Outil conformité (Étudiant 3)
```

---

## Entreprises du pool

Les 20 entreprises de `companies_pool.json` sont des entreprises françaises réelles issues de l'API SIRENE (data.gouv.fr). Elles couvrent 4 secteurs :

- **Tech** : JLB Logiciels, ARC Informatique, BIG DATA & Analytics, etc.
- **BTP** : Eiffage, Provence Rénovation, NGE Routes, etc.
- **Service** : Domino Transports, Newrest Restauration, etc.
- **Personnalisé** : noms des binômes du groupe intégrés dans les champs émetteur/valideur

---

## Vérification SIRET via l'API gouvernementale

En production (et pour la démo live), la plateforme peut vérifier les SIRET extraits par l'OCR en temps réel via l'API gratuite de l'annuaire des entreprises :

```
GET https://recherche-entreprises.api.gouv.fr/search?q={siret_ou_nom}
```

> **Aucune clé API requise**, l'accès est public et gratuit.

### Exemple Python

```python
import requests

def verifier_siret(siret):
    url = f"https://recherche-entreprises.api.gouv.fr/search?q={siret}"
    response = requests.get(url)
    data = response.json()

    if data["total_results"] == 0:
        return {"valide": False, "raison": "SIRET introuvable"}

    entreprise = data["results"][0]
    return {
        "valide": True,
        "nom": entreprise["nom_complet"],
        "siret": siret,
        "adresse": entreprise.get("siege", {}).get("adresse", ""),
        "activite": entreprise.get("activite_principale", "")
    }

# SIRET réel → valide
verifier_siret("52935972100014")
# → {"valide": True, "nom": "JLB LOGICIELS & SERVICES", ...}

# SIRET falsifié (SCN-3) → introuvable
verifier_siret("96256706492763")
# → {"valide": False, "raison": "SIRET introuvable"}
```

### Flux de vérification dans la pipeline

```
Document uploadé
    ↓
OCR extrait :  SIRET "96256706492763"  +  Entreprise "JLB LOGICIELS"
    ↓
Requête API :  GET recherche-entreprises.api.gouv.fr/search?q=JLB+LOGICIELS
    ↓
API répond  :  le vrai SIRET est 52935972100014
    ↓
Comparaison :  96256706492763 ≠ 52935972100014
    ↓
→ ALERTE : "SIRET incohérent détecté !"
```

### Stratégie recommandée (offline + online)

| Mode | Source | Usage |
|---|---|---|
| **Offline** | `companies_pool.json` (20 entreprises) | Développement, tests unitaires, démo sans internet |
| **Online** | API `recherche-entreprises.api.gouv.fr` | Démo live, production, couvre toutes les entreprises françaises |

L'Étudiant 5 peut combiner les deux : vérifier d'abord dans `companies_pool.json` (instantané), puis appeler l'API en fallback si l'entreprise n'est pas dans le pool. Cela garantit que la démo fonctionne même sans connexion internet.

---

## Métriques d'évaluation attendues

### OCR (Étudiant 2)
- **CER** (Character Error Rate) par niveau de difficulté
- Objectif : CER < 5% sur SCN-1, tolérance plus haute sur SCN-9

### Classification (Étudiant 2)
- **Accuracy / F1-score** sur les 6 types de documents
- Évaluation sur `ground_truth_test.json` uniquement

### Détection d'anomalies (Étudiant 5)
- **Precision / Recall / F1** sur la détection des `is_valid = false`
- Détail par type d'erreur : `siret_mismatch`, `urssaf_expired`, `vat_calculation_error`

---
### Commandes Clés

# Build et lancer les conteneurs
docker compose up --build

# Générer dataset
docker compose exec backend python generate_dataset.py

# Uploader vers MinIO
docker compose exec backend python datalake.py

## Notes

- Le script est **entièrement reproductible** : `random.seed(42)` garantit les mêmes documents à chaque exécution.
- Pour augmenter le volume, modifier les paramètres `n=` dans la fonction `main()` de `generate_dataset.py`.
- Pour ajouter des entreprises, enrichir `companies_pool.json` via l'[API SIRENE officielle](https://api.insee.fr/catalogue/site/themes/wso2/subthemes/insee/pages/item-info.jag?name=Sirene&version=V3&provider=insee).
=======
# hackaton26
IPSSI hackaton 2026
>>>>>>> e3d5ccab6779955bf330bfc1bb8cc8c760aaa018
