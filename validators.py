import requests
import time
from thefuzz import fuzz

def check_siret(siret):
    """Vérifie le SIRET avec gestion du Rate Limit (Erreur 429)."""
    siret = str(siret).replace(" ", "").strip()
    url = f"https://recherche-entreprises.api.gouv.fr/search?q={siret}"
    
    # On fait semblant d'être un navigateur classique
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        # Petite pause pour éviter le blocage 429
        time.sleep(1) 
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 429:
            return False, "Erreur 429 (Trop de requêtes, attends 1 min)"
            
        data = response.json()
        results = data.get('results', [])
        
        if results:
            return True, results[0].get('nom_complet', 'NOM INCONNU')
            
        return False, "SIRET introuvable"
    except Exception as e:
        return False, f"Erreur: {str(e)}"

def check_arithmetic(ht, ttc):
    return abs((ht * 1.20) - ttc) < 1.0

def check_name_match(ocr_name, api_name):
    score = fuzz.token_sort_ratio(ocr_name.lower(), api_name.lower())
    return score >= 80, score