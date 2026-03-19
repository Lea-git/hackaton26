# DocuHack - Plateforme de traitement automatique de documents administratifs

## Présentation du projet

DocuHack est une plateforme développée lors de notre hackathon permettant l'upload, la classification, 
l'extraction et la validation de documents administratifs (factures, devis, attestations). 
Le projet suit une architecture Medallion (Bronze, Silver, Gold) et intègre plusieurs services interconnectés.

## Rôle : Frontend & API

Développement de l'interface utilisateur et des points d'entrée API pour :
- L'upload de documents multi-formats
- L'affichage des données issues du Data Lake (MinIO)
- La visualisation des résultats OCR et des alertes de conformité
- L'authentification multi-profils (user / admin)

## Stack technique

- **Framework frontend et backend** : Laravel 12
- **Base de données** : SQLite
- **Stockage objet** : MinIO (compatible S3)
- **Client S3** : AWS SDK PHP + league/flysystem-aws-s3-v3
- **Authentification** : Guard Laravel avec rôles

## Architecture du projet

```
frontend/
├── app/
│   ├── Http/
│   │   └── Controllers/
│   │       └── Api/          # Contrôleurs API (Document, Extraction, Fournisseur, Alerte)
│   ├── Models/                # Modèles (Document, Extraction, Fournisseur, Alerte)
│   └── Services/
│       └── DataLakeClient.php # Client de communication avec MinIO
├── database/
│   ├── migrations/             # Tables (documents, extractions, fournisseurs, alertes)
│   └── seeders/                # Données de test
├── resources/
│   └── views/
│       ├── user/         # Vues espace utilisateur
│       │   ├── login.blade.php
│       │   └── dashboard.blade.php
│       └── admin/         # Vues espace administrateur
│           ├── login.blade.php
│           └── dashboard.blade.php
├── routes/
│   ├── web.php                 # Routes principales
│   └── api.php                 # Routes API
└── .env                        # Configuration
```

## Installation

### Prérequis

- PHP 8.3 ou supérieur
- Composer
- Node.js 18 ou supérieur
- Docker (pour le Data Lake MinIO)
- Git

### Étapes d'installation

1. **Cloner le dépôt**
```bash
git clone https://github.com/Lea-git/hackaton26.git
cd hackaton26/backend```

2. **Installer les dépendances PHP**
```bash
composer install
```

3. **Installer les dépendances JavaScript**
```bash
npm install
```

4. **Installer le package spécifique pour MinIO**
```bash
composer require league/flysystem-aws-s3-v3:^3.0
```

4. **Configurer l'environnement**
```bash
cp .env.example .env
php artisan key:generate
```

5. **Configurer la base de données**
```bash
# Créer le fichier SQLite
touch database/database.sqlite

# Lancer les migrations
php artisan migrate

# Ajouter des données de test
php artisan db:seed --class=DocumentSeeder
```

6. **Configurer le stockage**
```bash
php artisan storage:link
```

7. **Lancer le serveur de développement**
```bash
# Terminal 1 : serveur Laravel
php artisan serve

# Terminal 2 : compilation des assets
npm run dev
```

## Configuration du Data Lake (MinIO)

Le projet utilise MinIO comme Data Lake. Pour le lancer :

```bash
# Cloner le dépôt de l'étudiant 4
cd ..
git clone --branch datalake_branche https://github.com/Lea-git/hackaton26.git datalake
cd datalake

# Lancer MinIO avec Docker
docker-compose up -d
```

Accès à la console MinIO : http://localhost:9003  
Identifiants par défaut : admin / admin1234

Buckets créés automatiquement :
- raw-documents
- clean-documents
- curated-documents

### Configuration dans le .env

```
# Configuration MinIO
FILESYSTEM_DISK=s3
AWS_BUCKET=curated-documents
AWS_ACCESS_KEY_ID=admin
AWS_SECRET_ACCESS_KEY=admin1234
AWS_DEFAULT_REGION=us-east-1
AWS_ENDPOINT=http://localhost:9000
AWS_USE_PATH_STYLE_ENDPOINT=true

MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=admin1234
```

## Identifications de test

Deux profils sont disponibles après migration :

**utilisateur(user)**
- Email : user@docuhack.com
- Mot de passe : password123

**administrateur(admin)**
- Email : admin@docuhack.com
- Mot de passe : password123

## Points d'accès

### Interface utilisateur

- Accueil : http://localhost:8000
- Login user : http://localhost:8000/user/login
- Dashboard user : http://localhost:8000/user/dashboard
- Login admin : http://localhost:8000/admin/login
- Dashboard admin : http://localhost:8000/admin/dashboard

### API principales

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | /api/upload | Upload de documents |
| GET | /api/documents | Liste des documents |
| GET | /api/documents/{id} | Détail d'un document |
| GET | /api/fournisseurs | Liste des fournisseurs |
| GET | /api/alertes | Liste des alertes |
| POST | /api/alertes | Création d'une alerte |
| POST | /api/verifier/documents | Vérification de cohérence |

## Structure des données

### Format des documents OCR (étudiant 2)

```json
{
  "document_type": "facture",
  "siret": "55208131700019",
  "tva": "FR45552081317",
  "date": "2024-02-14",
  "montant_ht": 1000,
  "montant_ttc": 1200
}
```

### Format des documents analysés (étudiant 5)

```json
{
  "status": "VALID",
  "risk_score": 0,
  "checks": {
    "siret": true,
    "math": true,
    "ml": true
  },
  "metadata": {
    "analyzed_at": "2026-03-17T11:07:28.072751+00:00",
    "errors": [],
    "document_type": "facture",
    "input_vendor_name": "GOOGLE FRANCE",
    "api_company_name": "GOOGLE FRANCE"
  }
}
```

## Fonctionnalités implémentées

- **Authentification** multi-profils (user / admin) avec rôles
- **Upload** de documents (PDF, JPG, PNG) avec stockage local et envoi vers MinIO
- **Dashboards dynamiques** avec statistiques en temps réel
- **Affichage des données OCR** à partir de fichiers JSON
- **Connexion au Data Lake** (MinIO) pour les documents analysés
- **Détection automatique** des anomalies et incohérences
- **Design responsive** et professionnel

## Tests

Pour tester le bon fonctionnement :

1. **Tester l'authentification**
   - Se connecter avec les deux profils
   - Vérifier les redirections

2. **Tester l'upload**
   - Uploader un fichier PDF ou image
   - Vérifier son apparition dans "Documents récents"
   - Vérifier sa présence dans MinIO (bucket raw-documents)

3. **Tester l'affichage des données**
   - Vérifier les trois sections du dashboard user
   - Vérifier les alertes dans le dashboard admin

## Déploiement avec Docker

Un Dockerfile est fourni pour conteneuriser l'application :

```dockerfile
FROM php:8.3-apache
RUN apt-get update && apt-get install -y libpng-dev libjpeg-dev libfreetype6-dev zip unzip git
RUN docker-php-ext-configure gd --with-freetype --with-jpeg
RUN docker-php-ext-install -j$(nproc) gd pdo pdo_mysql
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
COPY . /var/www/html
RUN chown -R www-data:www-data /var/www/html
RUN chmod -R 755 /var/www/html/storage
RUN chmod -R 755 /var/www/html/bootstrap/cache
WORKDIR /var/www/html
RUN composer install --no-interaction --optimize-autoloader --no-dev
EXPOSE 80
CMD ["apache2-foreground"]
```

Pour lancer l'application avec Docker Compose :

```bash
cp .env.docker .env
docker-compose up -d --build
docker-compose exec app php artisan migrate
docker-compose exec app php artisan storage:link
```
