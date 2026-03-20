import json
import os
import cv2
import numpy as np
import pytesseract
import re
from pdf2image import convert_from_path

# Path Tesseract : auto-detect (Linux Docker ou Windows)
if os.path.exists("/usr/bin/tesseract"):
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

RAW_FOLDER = "data/raw"
CLEAN_FOLDER = "data/clean"


# -------------------------
# Nettoyage texte OCR
# -------------------------
def clean_text(text):

    text = text.replace("€", " EUR ")
    text = text.replace("\n", " ")

    # corrections OCR fréquentes
    corrections = {
        "T7C": "TTC",
        "H.T": "HT",
        "T T C": "TTC",
        "H T": "HT"
    }

    for k, v in corrections.items():
        text = text.replace(k, v)

    text = re.sub(r'\s+', ' ', text)

    return text.strip()


# -------------------------
# Prétraitement image
# -------------------------
def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)[1]
    return thresh


# -------------------------
# OCR
# -------------------------
def extract_text_from_image(image):
    processed = preprocess_image(image)
    return pytesseract.image_to_string(processed, lang="fra")


def extract_text_from_pdf(pdf_path):
    """Extrait le texte d'un PDF.
    Utilise pdfplumber en priorité (PDFs textuels), avec fallback Tesseract (scans).
    """
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = [page.extract_text() or "" for page in pdf.pages]
        full_text = "\n".join(pages_text)
        if len(full_text.strip()) > 50:
            return full_text
    except Exception:
        pass

    # Fallback : conversion image + Tesseract (pour PDFs scannés)
    pages = convert_from_path(pdf_path)
    full_text = ""
    for page in pages:
        image = np.array(page)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        full_text += extract_text_from_image(image) + "\n"
    return full_text


# -------------------------
# Extraction MAXIMALE
# -------------------------
def _parse_amount(raw):
    """Convertit une chaîne montant en float.
    Gère le format français (1 234,56 / 1.234,56) ET anglais (1,234.56).
    """
    raw = raw.strip()
    # Format anglais : 1,234.56 (virgule=milliers, point=décimale)
    if re.match(r'^\d{1,3}(?:,\d{3})+\.\d{2}$', raw):
        return float(raw.replace(',', ''))
    # Format français : supprimer séparateurs de milliers (espaces ou points)
    raw = re.sub(r'[\s\.](?=\d{3}(?:[,\.]\d{2}|$))', '', raw)
    raw = raw.replace(",", ".")
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


def extract_amount_with_label(patterns, text):
    # Montant : gère format français (1 234,56) ET anglais (1,234.56)
    _amt = r'(\d[\d\s\.,]*[,\.]\d{2})'
    for pattern in patterns:
        match = re.search(pattern.replace(r'(\d+[.,]\d+)', _amt), text, re.IGNORECASE)
        if match:
            label = match.group(1).strip()
            value = _parse_amount(match.group(2))
            if value > 0:
                return {"label": label, "value": value}
    return None


def extract_all_fields(text):

    data = {}

    # SIRET : cherche d'abord près du mot-clé "SIRET" (accepte tout découpage OCR)
    data["siret"] = None
    siret_keyword = re.search(r'SIRET\s*:?\s*([\d\s]{14,20})', text, re.IGNORECASE)
    if siret_keyword:
        candidate = re.sub(r'\s', '', siret_keyword.group(1))
        if len(candidate) == 14:
            data["siret"] = candidate
    if not data["siret"]:
        # Fallback : groupes 3+3+3+5 avec espaces optionnels
        siret_match = re.search(r'\b(\d{3}[\s]?\d{3}[\s]?\d{3}[\s]?\d{5})\b', text)
        if siret_match:
            data["siret"] = re.sub(r'\s', '', siret_match.group(1))
    if not data["siret"]:
        # Dernier recours : 14 chiffres consécutifs
        siret_match = re.search(r'\b(\d{14})\b', text)
        if siret_match:
            data["siret"] = siret_match.group(1)

    # IBAN
    iban = re.search(r'\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b', text)
    data["iban"] = iban.group() if iban else None

    # BIC
    bic = re.search(r'\b[A-Z]{8,11}\b', text)
    data["bic"] = bic.group() if bic else None

    # Tous les montants (avec séparateurs de milliers)
    amounts = re.findall(r'\d[\d\s]*[.,]\d{2}', text)
    data["montants_detectes"] = list(set(amounts))

    # TTC
    data["montant_ttc"] = extract_amount_with_label([
        r'(Total TTC)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
        r'(TTC)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
        r'(Montant TTC)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
        r'(Net à payer)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
    ], text)

    # HT
    data["montant_ht"] = extract_amount_with_label([
        r'(Total HT)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
        r'(Montant HT)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
        r'(HT|Hors Taxe)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
    ], text)

    # TVA
    data["tva"] = extract_amount_with_label([
        r'(TVA \d+\s*%?)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
        r'(TVA)[^\d]*(\d[\d\s\.,]*[,\.]\d{2})',
    ], text)

    # Dates
    dates = re.findall(r'\d{2}/\d{2}/\d{4}', text)
    data["dates"] = dates

    # Nom entreprise : cherche SARL/SAS/EURL/SA/SNC suivi du nom
    company_match = re.search(
        r'\b((?:SARL|SAS|EURL|SA|SNC|SASU|SCOP)\s+[\w\s\-&\']+?)(?:\s*[-–—]|\s*\n|\s{2,}|,)',
        text, re.IGNORECASE
    )
    if company_match:
        data["nom_entreprise"] = company_match.group(1).strip()
    else:
        # fallback : premiers mots significatifs (clean_text a supprimé les \n)
        words = text.split()
        data["nom_entreprise"] = ' '.join(words[:6]) if words else None

    # Keywords
    keywords = [
        "facture", "devis", "iban", "bic", "kbis",
        "rcs", "tva", "total", "banque"
    ]

    data["keywords_found"] = [k for k in keywords if k in text.lower()]

    return data


# -------------------------
# Classification intelligente
# -------------------------
def infer_document_type(data):

    score = {
        "facture": 0,
        "devis": 0,
        "rib": 0,
        "extrait kbis": 0,
        "attestation siret": 0
    }

    text_keywords = data.get("keywords_found", [])

    # -------------------------
    # 🔥 RÈGLES FORTES (prioritaires)
    # -------------------------

    # RIB → IBAN = quasi certain
    if data.get("iban"):
        score["rib"] += 10

    # KBIS → RCS très discriminant
    if "rcs" in text_keywords or "kbis" in text_keywords:
        score["extrait kbis"] += 10

    # FACTURE → TTC + TVA ensemble
    if data.get("montant_ttc") and data.get("tva"):
        score["facture"] += 8

    # DEVIS → mot clé fort
    if "devis" in text_keywords:
        score["devis"] += 7

    # -------------------------
    # ⚖️ SCORES PONDÉRÉS
    # -------------------------
    if data.get("montant_ttc") and data["montant_ttc"]["value"]:
        score["facture"] += 3
    if data.get("montant_ht") and data["montant_ht"]["value"]:
        score["facture"] += 2
    if data.get("tva") and data["tva"]["value"]:
        score["facture"] += 2
        

    if data.get("montant_ht"):
        score["facture"] += 2
        score["devis"] += 2

    if data.get("siret"):
        score["facture"] += 1
        score["devis"] += 1
        score["attestation siret"] += 3

    if data.get("dates"):
        score["facture"] += 1
        score["devis"] += 1

    if "facture" in text_keywords:
        score["facture"] += 5

    if "iban" in text_keywords:
        score["rib"] += 3

    if "bic" in text_keywords:
        score["rib"] += 2

    # -------------------------
    # ❌ PÉNALITÉS (TRÈS IMPORTANT)
    # -------------------------

    # Si IBAN présent → peu probable facture pure
    if data.get("iban"):
        score["facture"] -= 3
        score["devis"] -= 2

    # Si aucun montant → pas une facture
    if not data.get("montant_ttc") and not data.get("montant_ht"):
        score["facture"] -= 4

    # Si aucun mot clé facture
    if "facture" not in text_keywords:
        score["facture"] -= 2

    # KBIS ne doit pas avoir de montants
    if score["extrait kbis"] > 0 and data.get("montant_ttc"):
        score["extrait kbis"] -= 5

    # -------------------------
    # 🧠 NORMALISATION
    # -------------------------

    # éviter scores négatifs extrêmes
    for k in score:
        score[k] = max(score[k], 0)

    # -------------------------
    # 🎯 CHOIX FINAL
    # -------------------------

    best_type = max(score, key=score.get)

    return best_type, score


# -------------------------
# Sauvegarde
# -------------------------
def save_output(text, filename):

    os.makedirs(CLEAN_FOLDER, exist_ok=True)

    cleaned = clean_text(text)

    # extraction globale
    data = extract_all_fields(cleaned)

    # classification basée sur données
    doc_type, score = infer_document_type(data)

    output = {
        "filename": filename,
        "type": doc_type,
        "scores": score,
        "detected_entities_count": len([v for v in data.values() if v]),
        "fields": data,
        "raw_text": cleaned
    }

    json_path = os.path.join(CLEAN_FOLDER, filename.replace(".txt", ".json"))

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)


# -------------------------
# Pipeline principal
# -------------------------
def process_documents():
    from datalake import DataLakeClient
    client = DataLakeClient()

    for file in os.listdir(RAW_FOLDER):

        path = os.path.join(RAW_FOLDER, file)

        print(f"Processing : {file}")

        try:
            # -------------------------
            # 1️⃣ UPLOAD RAW
            # -------------------------
            client.upload_raw(file, path)

            # -------------------------
            # 2️⃣ OCR
            # -------------------------
            if file.lower().endswith(".pdf"):
                text = extract_text_from_pdf(path)
            else:
                image = cv2.imread(path)
                text = extract_text_from_image(image)

            cleaned = clean_text(text)

            # -------------------------
            # 3️⃣ UPLOAD CLEAN
            # -------------------------
            clean_name = file.rsplit(".", 1)[0] + ".txt"
            client.upload_clean(clean_name, cleaned)

            # -------------------------
            # 4️⃣ EXTRACTION
            # -------------------------
            data = extract_all_fields(cleaned)

            # -------------------------
            # 5️⃣ CLASSIFICATION
            # -------------------------
            doc_type, score = infer_document_type(data)

            # -------------------------
            # 6️⃣ CURATED JSON
            # -------------------------
            curated_data = {
                "document": {
                    "name": file,
                    "type": doc_type
                },
                "extraction": data,
                "scores": score,
                "detected_entities_count": len([v for v in data.values() if v]),
                "pipeline": ["raw", "clean", "curated"]
            }

            curated_name = file.rsplit(".", 1)[0] + ".json"

            # -------------------------
            # 7️⃣ UPLOAD CURATED
            # -------------------------
            client.upload_curated(curated_name, curated_data)

            print("✅ Envoyé dans le DataLake\n")

        except Exception as e:
            print(f"❌ Erreur sur {file} : {e}\n")


if __name__ == "__main__":
    process_documents()