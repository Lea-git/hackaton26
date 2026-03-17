import json

def create_test_json(name, siret, vendor, ht, ttc):
    data = {
        "document_type": "facture",
        "siret": siret,
        "vendor_name": vendor,
        "montant_ht": ht,
        "montant_ttc": ttc
    }
    with open(name, 'w') as f:
        json.dump(data, f, indent=4)

# SIRET de Google France
create_test_json("facture_ok.json", "44306184100047", "GOOGLE FRANCE", 1000, 1200)
# SIRET Google + Erreur de calcul
create_test_json("facture_math_error.json", "44306184100047", "GOOGLE FRANCE", 1000, 5000)