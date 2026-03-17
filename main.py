import json
from validators import check_siret, check_arithmetic, check_name_match
from anomaly_model import detect_outlier

def run_pipeline(json_file):
    print(f"\n>>> ANALYSE DU FICHIER : {json_file}")
    
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Extraction des données
    siret = data.get('siret')
    ht = data.get('montant_ht')
    ttc = data.get('montant_ttc')
    ocr_name = data.get('vendor_name', 'Inconnu')

    # 1. Validation Légale (API)
    is_siret_valid, api_name = check_siret(siret)
    
    # 2. Validation Sémantique (Fuzzy)
    is_name_match, score = check_name_match(ocr_name, api_name) if is_siret_valid else (False, 0)

    # 3. Validation Arithmétique
    is_math_ok = check_arithmetic(ht, ttc)

    # 4. Détection d'Anomalie (ML)
    is_suspicious = detect_outlier(ttc)

    # --- RAPPORT FINAL ---
    print(f"Statut SIRET : {'✅ OK' if is_siret_valid else '❌ ERREUR'} ({api_name})")
    print(f"Match Nom : {'✅ OK' if is_name_match else '❌ DISCORDANCE'} ({score}%)")
    print(f"Calcul TVA : {'✅ OK' if is_math_ok else '❌ CALCUL FAUX'}")
    print(f"Alerte Fraude (ML) : {'⚠️ SUSPECT' if is_suspicious else '✅ NORMAL'}")

if __name__ == "__main__":
    # lancé mock_generator.py avant
    try:
        run_pipeline("facture_ok.json")
        run_pipeline("facture_math_error.json")
    except FileNotFoundError:
        print("Erreur : Fichiers JSON introuvables. Lance mock_generator.py d'abord.")