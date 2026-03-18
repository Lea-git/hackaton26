#!/usr/bin/env python3
"""
generate_dataset.py — Génération d'un dataset synthétique de documents administratifs.
Hackathon 2026 — Plateforme de traitement de documents.
"""

import json
import os
import random
import string
import math
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from faker import Faker
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle

fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)
np.random.seed(42)

# 🔥 AJOUT
from datalake import DataLakeClient
from datetime import datetime

# 🔥 AJOUT
datalake = DataLakeClient()

# 🔥 AJOUT
def upload_raw_only(local_path, filename, scenario):
    import os

    if not os.path.exists(local_path):
        print(f"[ERREUR] Fichier introuvable : {local_path}")
        return

    try:
        date_path = datetime.now().strftime("%Y/%m/%d")
        object_name = f"{scenario}/{date_path}/{filename}"

        datalake.upload_raw(object_name, str(local_path))
    except Exception as e:
        print(f"[ERREUR UPLOAD RAW] {filename} : {e}")
# --- Config ---
BASE_DIR = Path(__file__).parent
#OUTPUT_DIR = BASE_DIR / "output" / "raw_zone"
#OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# 🔥 AJOUT
OUTPUT_DIR = Path("output/raw_zone")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEAM_MEMBERS = [
    "Amine Belhaimeur",
    "Lea Druffin",
    "Moustapha ABDI ALI",
    "Ameto Cornelia Adanto",
    "Younes Elfraihi",
    "Yannis Bouttier",
]

with open(BASE_DIR / "companies_pool.json", "r", encoding="utf-8") as f:
    COMPANIES = json.load(f)

ground_truth = []
counters = {
    "SCN-1": 0, "SCN-2": 0, "SCN-3": 0, "SCN-4": 0,
    "SCN-5": 0, "SCN-6": 0, "SCN-7": 0, "SCN-8": 0,
    "SCN-9": 0, "SCN-10": 0,
}


# --- Helpers ---
def pick_team():
    return random.choice(TEAM_MEMBERS)


def pick_company():
    return random.choice(COMPANIES)


def random_siret():
    """Génère un SIRET aléatoire (14 chiffres) garanti différent du pool."""
    while True:
        s = "".join(random.choices(string.digits, k=14))
        if not any(c["siret"] == s for c in COMPANIES):
            return s


def gen_invoice_number():
    return f"FA-{random.randint(2024, 2026)}-{random.randint(1000, 9999)}"


def gen_devis_number():
    return f"DV-{random.randint(2024, 2026)}-{random.randint(1000, 9999)}"


def gen_kbis_number():
    return f"KBIS-{random.randint(2020, 2026)}-{random.randint(100000, 999999)}"


def gen_iban():
    """Génère un IBAN français crédible (format FR76 + 23 chiffres)."""
    digits = "".join(random.choices(string.digits, k=23))
    return f"FR76 {digits[:4]} {digits[4:8]} {digits[8:12]} {digits[12:16]} {digits[16:20]} {digits[20:]}"


def gen_bic():
    """Génère un code BIC crédible."""
    banks = ["BNPAFRPP", "SOGEFRPP", "CRLYFRPP", "AGRIFRPP", "CEPAFRPP",
             "CMCIFRPP", "CCBPFRPP", "BFCOFRPP", "NATXFRPP", "BOUSFRPP"]
    return random.choice(banks)


def random_date(start_year=2025, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def format_date(dt):
    return dt.strftime("%d/%m/%Y")


def generate_line_items(count=None):
    """Génère des lignes de facture réalistes."""
    if count is None:
        count = random.randint(2, 6)
    items = []
    descriptions = [
        "Prestation de conseil en informatique",
        "Développement application web",
        "Maintenance serveurs (forfait mensuel)",
        "Audit de sécurité SI",
        "Formation équipe technique",
        "Licence logicielle annuelle",
        "Hébergement cloud (trimestre)",
        "Support technique niveau 2",
        "Installation réseau fibre optique",
        "Fourniture matériel informatique",
        "Travaux de maçonnerie",
        "Pose de cloisons sèches",
        "Nettoyage industriel (forfait)",
        "Gardiennage site (mois)",
        "Transport marchandises",
        "Consultation RH",
        "Rénovation bureaux",
        "Câblage électrique bâtiment",
        "Étude de faisabilité technique",
        "Intégration API partenaires",
    ]
    for _ in range(count):
        desc = random.choice(descriptions)
        qty = random.randint(1, 10)
        unit_price = round(random.uniform(150, 3500), 2)
        total_ht = round(qty * unit_price, 2)
        items.append(
            {"description": desc, "qty": qty, "unit_price": unit_price, "total_ht": total_ht}
        )
    return items


# ============================================================
# PDF DRAWING FUNCTIONS
# ============================================================

def draw_invoice_pdf(filepath, company, client, items, invoice_num, date_str,
                     emetteur, valideur, siret_display, tva_rate=0.20,
                     force_vat_error=False):
    """Dessine une facture PDF complète."""
    c = canvas.Canvas(str(filepath), pagesize=A4)
    w, h = A4

    color_primary = HexColor("#1a5276")
    color_accent = HexColor("#2980b9")
    c.setFillColor(color_primary)
    c.rect(0, h - 90, w, 90, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(30, h - 45, "FACTURE")
    c.setFont("Helvetica", 10)
    c.drawString(30, h - 65, f"N° {invoice_num}")
    c.drawString(30, h - 80, f"Date : {date_str}")

    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(w - 30, h - 45, company["nom"])
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 30, h - 60, f"SIRET : {siret_display}")
    c.drawRightString(w - 30, h - 73, company["adresse"])

    y = h - 115
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawString(30, y, f"Émis par : {emetteur}")
    c.drawString(30, y - 14, f"Validé par : {valideur}")

    c.setFillColor(color_accent)
    c.rect(w - 250, y - 10, 220, 60, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 240, y + 30, "CLIENT")
    c.setFont("Helvetica", 9)
    c.drawString(w - 240, y + 16, client["nom"])
    c.drawString(w - 240, y + 3, f"SIRET : {client['siret']}")
    c.drawString(w - 240, y - 10, client["adresse"][:40])

    y_table = y - 50
    header = ["Description", "Qté", "PU HT (€)", "Total HT (€)"]
    data = [header]
    for item in items:
        data.append([
            item["description"][:40],
            str(item["qty"]),
            f"{item['unit_price']:.2f}",
            f"{item['total_ht']:.2f}",
        ])

    total_ht = sum(i["total_ht"] for i in items)
    tva_amount = round(total_ht * tva_rate, 2)
    total_ttc = round(total_ht + tva_amount, 2)

    if force_vat_error:
        error_delta = round(random.uniform(5, 80), 2) * random.choice([1, -1])
        total_ttc_display = round(total_ttc + error_delta, 2)
    else:
        total_ttc_display = total_ttc

    data.append(["", "", "Total HT", f"{total_ht:.2f}"])
    data.append(["", "", f"TVA ({int(tva_rate*100)}%)", f"{tva_amount:.2f}"])
    data.append(["", "", "Total TTC", f"{total_ttc_display:.2f}"])

    col_widths = [220, 40, 80, 90]
    t = Table(data, colWidths=col_widths)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -4), 0.5, HexColor("#cccccc")),
        ("BACKGROUND", (2, -3), (-1, -1), HexColor("#ecf0f1")),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (2, -3), (-1, -3), 1, color_primary),
    ])
    t.setStyle(style)
    t_w, t_h = t.wrap(0, 0)
    t.drawOn(c, 30, y_table - t_h)

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawString(30, 40, f"{company['nom']} — SIRET {siret_display} — {company['adresse']}")
    c.drawString(30, 28, "TVA intracommunautaire : FR" + siret_display[:11])
    c.drawCentredString(w / 2, 15, "Document généré automatiquement — Hackathon 2026")

    c.save()
    return total_ht, tva_amount, total_ttc, total_ttc_display


def draw_devis_pdf(filepath, company, client, items, devis_num, date_str,
                   emetteur, siret_display, tva_rate=0.20):
    """Dessine un devis PDF."""
    c = canvas.Canvas(str(filepath), pagesize=A4)
    w, h = A4

    color_primary = HexColor("#1b4332")
    color_accent = HexColor("#2d6a4f")
    c.setFillColor(color_primary)
    c.rect(0, h - 90, w, 90, fill=1, stroke=0)

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(30, h - 45, "DEVIS")
    c.setFont("Helvetica", 10)
    c.drawString(30, h - 65, f"N° {devis_num}")
    c.drawString(30, h - 80, f"Date : {date_str}")
    validity = format_date(datetime.strptime(date_str, "%d/%m/%Y") + timedelta(days=30))
    c.drawString(200, h - 80, f"Valide jusqu'au : {validity}")

    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(w - 30, h - 45, company["nom"])
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 30, h - 60, f"SIRET : {siret_display}")
    c.drawRightString(w - 30, h - 73, company["adresse"])

    y = h - 115
    c.setFillColor(black)
    c.setFont("Helvetica", 9)
    c.drawString(30, y, f"Établi par : {emetteur}")

    c.setFillColor(color_accent)
    c.rect(w - 250, y - 10, 220, 50, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 240, y + 22, "CLIENT")
    c.setFont("Helvetica", 9)
    c.drawString(w - 240, y + 8, client["nom"])
    c.drawString(w - 240, y - 5, f"SIRET : {client['siret']}")

    y_table = y - 50
    header = ["Description", "Qté", "PU HT (€)", "Total HT (€)"]
    data = [header]
    for item in items:
        data.append([
            item["description"][:40],
            str(item["qty"]),
            f"{item['unit_price']:.2f}",
            f"{item['total_ht']:.2f}",
        ])

    total_ht = sum(i["total_ht"] for i in items)
    tva_amount = round(total_ht * tva_rate, 2)
    total_ttc = round(total_ht + tva_amount, 2)
    data.append(["", "", "Total HT", f"{total_ht:.2f}"])
    data.append(["", "", f"TVA ({int(tva_rate*100)}%)", f"{tva_amount:.2f}"])
    data.append(["", "", "Total TTC", f"{total_ttc:.2f}"])

    col_widths = [220, 40, 80, 90]
    t = Table(data, colWidths=col_widths)
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_primary),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -4), 0.5, HexColor("#cccccc")),
        ("BACKGROUND", (2, -3), (-1, -1), HexColor("#ecf0f1")),
        ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (2, -3), (-1, -3), 1, color_primary),
    ])
    t.setStyle(style)
    t_w, t_h = t.wrap(0, 0)
    t.drawOn(c, 30, y_table - t_h)

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawString(30, 40, f"{company['nom']} — SIRET {siret_display} — {company['adresse']}")
    c.drawCentredString(w / 2, 15, "Document généré automatiquement — Hackathon 2026")
    c.save()
    return total_ht, tva_amount, total_ttc


def draw_urssaf_pdf(filepath, company, date_emission, date_expiration,
                    emetteur, siret_display):
    """Dessine une attestation de vigilance URSSAF."""
    c = canvas.Canvas(str(filepath), pagesize=A4)
    w, h = A4

    color_urssaf = HexColor("#003DA5")
    c.setFillColor(color_urssaf)
    c.rect(0, h - 100, w, 100, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 45, "ATTESTATION DE VIGILANCE")
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, h - 68, "URSSAF — Sécurité Sociale")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 85, f"Réf : ATT-{random.randint(100000, 999999)}")

    y = h - 140
    c.setFillColor(black)
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Je soussigné(e), l'URSSAF, atteste que l'entreprise ci-dessous")
    c.drawString(50, y - 18, "est à jour de ses obligations déclaratives et de paiement.")

    y -= 55
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Entreprise :")
    c.setFont("Helvetica", 11)
    c.drawString(160, y, company["nom"])
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "SIRET :")
    c.setFont("Helvetica", 11)
    c.drawString(160, y, siret_display)
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Adresse :")
    c.setFont("Helvetica", 11)
    c.drawString(160, y, company["adresse"])
    y -= 22
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Activité :")
    c.setFont("Helvetica", 11)
    c.drawString(160, y, company["activite"])

    y -= 45
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Date d'émission :  {format_date(date_emission)}")
    y -= 25
    # Toujours en noir — aucun indice visuel, l'IA doit calculer
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, f"Date d'expiration :  {format_date(date_expiration)}")

    y -= 60
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Délivré par : {emetteur}")
    c.drawString(50, y - 18, "Pour le Directeur de l'URSSAF")

    # Bandeau toujours vert "ATTESTATION VALIDE" — piège visuel
    y -= 60
    c.setStrokeColor(HexColor("#27ae60"))
    c.setFillColor(HexColor("#eafaf1"))
    c.roundRect(50, y - 30, w - 100, 40, 5, fill=1, stroke=1)
    c.setFillColor(HexColor("#27ae60"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, y - 17, "ATTESTATION VALIDE")

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, "Ce document est une attestation officielle de l'URSSAF.")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()


def draw_kbis_pdf(filepath, company, dirigeant, siret_display, date_immat, capital):
    """Dessine un extrait Kbis."""
    c = canvas.Canvas(str(filepath), pagesize=A4)
    w, h = A4

    # Bandeau Greffe du Tribunal de Commerce
    color_greffe = HexColor("#2c3e50")
    color_gold = HexColor("#c9a84c")
    c.setFillColor(color_greffe)
    c.rect(0, h - 110, w, 110, fill=1, stroke=0)

    # Filet doré décoratif
    c.setStrokeColor(color_gold)
    c.setLineWidth(2)
    c.line(30, h - 108, w - 30, h - 108)

    c.setFillColor(color_gold)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 25, "RÉPUBLIQUE FRANÇAISE")
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 52, "EXTRAIT KBIS")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 72, "Greffe du Tribunal de Commerce")
    kbis_num = gen_kbis_number()
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 90, f"Réf : {kbis_num}")
    date_str = format_date(random_date(2025, 2026))
    c.drawCentredString(w / 2, h - 102, f"Délivré le : {date_str}")

    # Corps du document
    y = h - 145
    c.setFillColor(black)

    siren = siret_display[:9]
    nic = siret_display[9:]

    fields = [
        ("Dénomination sociale", company["nom"]),
        ("SIREN", siren),
        ("NIC (Siège)", nic),
        ("SIRET (Siège)", siret_display),
        ("Forme juridique", random.choice(["SAS", "SARL", "SA", "EURL", "SCI"])),
        ("Adresse du siège", company["adresse"]),
        ("Activité (NAF)", company["activite"]),
        ("Date d'immatriculation", format_date(date_immat)),
        ("Capital social", f"{capital:,.0f} EUR".replace(",", " ")),
        ("Dirigeant", dirigeant),
        ("Qualité", random.choice(["Président", "Gérant", "Directeur Général"])),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"{label} :")
        c.setFont("Helvetica", 11)
        c.drawString(230, y, str(value))
        y -= 28

    # Cadre "INSCRIPTION ACTIVE"
    y -= 30
    c.setStrokeColor(HexColor("#27ae60"))
    c.setFillColor(HexColor("#eafaf1"))
    c.roundRect(50, y - 25, w - 100, 40, 5, fill=1, stroke=1)
    c.setFillColor(HexColor("#27ae60"))
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, y - 12, "INSCRIPTION ACTIVE AU RCS")

    # Mentions légales
    y -= 70
    c.setFillColor(HexColor("#555555"))
    c.setFont("Helvetica", 8)
    c.drawString(50, y, "Le présent extrait est délivré en application des articles R.123-150 et suivants")
    c.drawString(50, y - 12, "du Code de Commerce. Il certifie l'inscription au Registre du Commerce et des Sociétés.")

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, f"Greffe du Tribunal de Commerce — {kbis_num}")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()


def draw_rib_pdf(filepath, company, siret_display, iban, bic):
    """Dessine un RIB (Relevé d'Identité Bancaire)."""
    c = canvas.Canvas(str(filepath), pagesize=A4)
    w, h = A4

    color_bank = HexColor("#1a237e")
    color_light = HexColor("#e8eaf6")

    # En-tête banque
    c.setFillColor(color_bank)
    c.rect(0, h - 80, w, 80, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 40, "RELEVÉ D'IDENTITÉ BANCAIRE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 60, "RIB — Coordonnées Bancaires")

    y = h - 120
    c.setFillColor(black)

    # Bloc titulaire
    c.setFillColor(color_light)
    c.roundRect(40, y - 80, w - 80, 90, 5, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y - 10, "Titulaire du compte")
    c.setFont("Helvetica", 11)
    c.drawString(60, y - 30, company["nom"])
    c.drawString(60, y - 48, company["adresse"])
    c.drawString(60, y - 66, f"SIRET : {siret_display}")

    y -= 110

    # Bloc coordonnées bancaires
    code_banque = iban.replace(" ", "")[4:9]
    code_guichet = iban.replace(" ", "")[9:14]
    num_compte = iban.replace(" ", "")[14:25]
    cle_rib = iban.replace(" ", "")[25:27]

    bank_fields = [
        ("Code Banque", code_banque),
        ("Code Guichet", code_guichet),
        ("N° de Compte", num_compte),
        ("Clé RIB", cle_rib),
    ]

    # Tableau RIB
    header = [f[0] for f in bank_fields]
    values = [f[1] for f in bank_fields]
    data = [header, values]
    col_widths = [120, 120, 140, 80]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_bank),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, 1), "Courier-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 1, HexColor("#cccccc")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    t_w, t_h = t.wrap(0, 0)
    t.drawOn(c, (w - sum(col_widths)) / 2, y - t_h)

    y -= t_h + 40

    # IBAN et BIC
    c.setFillColor(color_light)
    c.roundRect(40, y - 70, w - 80, 80, 5, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y - 10, "IBAN :")
    c.setFont("Courier-Bold", 13)
    c.drawString(130, y - 10, iban)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y - 40, "BIC / SWIFT :")
    c.setFont("Courier-Bold", 13)
    c.drawString(180, y - 40, bic)

    # Domiciliation
    y -= 100
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, y, "Domiciliation :")
    c.setFont("Helvetica", 11)
    banques = ["BNP Paribas", "Société Générale", "Crédit Lyonnais", "Crédit Agricole",
               "Caisse d'Épargne", "Crédit Mutuel", "Banque Populaire", "Banque de France"]
    c.drawString(180, y, f"{random.choice(banques)} — Agence Centrale")

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, f"{company['nom']} — SIRET {siret_display}")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()


def draw_siret_pdf(filepath, company, siret_display, date_delivrance):
    """Dessine une attestation d'inscription au répertoire SIRENE (attestation SIRET)."""
    c = canvas.Canvas(str(filepath), pagesize=A4)
    w, h = A4

    # Bandeau INSEE
    color_insee = HexColor("#0055A4")
    c.setFillColor(color_insee)
    c.rect(0, h - 110, w, 110, fill=1, stroke=0)

    c.setFillColor(HexColor("#FFD700"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 20, "RÉPUBLIQUE FRANÇAISE")

    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 48, "ATTESTATION DE SITUATION SIRENE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 68, "INSEE — Institut National de la Statistique et des Études Économiques")
    c.setFont("Helvetica", 9)
    ref = f"SIRENE-{random.randint(100000, 999999)}"
    c.drawCentredString(w / 2, h - 85, f"Réf : {ref}")
    c.drawCentredString(w / 2, h - 98, f"Délivré le : {format_date(date_delivrance)}")

    # Corps
    y = h - 145
    c.setFillColor(black)
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "L'INSEE certifie que l'établissement ci-dessous est inscrit")
    c.drawString(50, y - 18, "au répertoire national des entreprises et des établissements (SIRENE).")

    siren = siret_display[:9]
    nic = siret_display[9:]

    y -= 55
    fields = [
        ("Dénomination", company["nom"]),
        ("SIREN", siren),
        ("NIC", nic),
        ("SIRET", siret_display),
        ("Adresse", company["adresse"]),
        ("Activité principale (APE)", company["activite"]),
        ("Catégorie juridique", random.choice(["5710 - SAS", "5720 - SARL", "5499 - SA", "5498 - EURL"])),
        ("Date de création", format_date(random_date(2005, 2018))),
        ("Statut", "Actif"),
    ]

    for label, value in fields:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"{label} :")
        c.setFont("Helvetica", 11)
        c.drawString(250, y, str(value))
        y -= 25

    # Cadre statut
    y -= 25
    c.setStrokeColor(HexColor("#0055A4"))
    c.setFillColor(HexColor("#e8f0fe"))
    c.roundRect(50, y - 25, w - 100, 40, 5, fill=1, stroke=1)
    c.setFillColor(color_insee)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, y - 12, "ÉTABLISSEMENT ACTIF AU RÉPERTOIRE SIRENE")

    # Pied de page
    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, f"INSEE — Attestation SIRENE — {ref}")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()


# ============================================================
# IMAGE EFFECTS
# ============================================================

def _pdf_to_cv2(pdf_path):
    """Convertit un PDF en image numpy BGR via PyMuPDF."""
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    mat = fitz.Matrix(200 / 72, 200 / 72)
    pix = page.get_pixmap(matrix=mat)
    doc.close()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n).copy()
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img


def apply_dirty_scan(pdf_path, output_jpg_path):
    """Convertit un PDF en JPG avec rotation, bruit et flou via PyMuPDF."""
    img = _pdf_to_cv2(pdf_path)

    # Rotation aléatoire ±6°
    angle = random.uniform(-6, 6)
    h_img, w_img = img.shape[:2]
    center = (w_img // 2, h_img // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    img = cv2.warpAffine(img, M, (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)

    # Bruit gaussien fort (grain de scanner)
    noise = np.random.normal(0, 18, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Flou modéré
    img = cv2.GaussianBlur(img, (5, 5), 1.2)

    # Variation de luminosité plus marquée (simule un scan)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] + random.randint(-25, 5), 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    cv2.imwrite(str(output_jpg_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])


def apply_smartphone_scan(pdf_path, output_jpg_path):
    """Simule une photo prise au smartphone : perspective warp + gradient de lumière."""
    img = _pdf_to_cv2(pdf_path)
    h_img, w_img = img.shape[:2]

    # --- Perspective warp ---
    margin_x = int(w_img * 0.06)
    margin_y = int(h_img * 0.06)
    src = np.float32([[0, 0], [w_img, 0], [w_img, h_img], [0, h_img]])
    dst = np.float32([
        [random.randint(margin_x // 2, margin_x), random.randint(margin_y // 2, margin_y)],
        [w_img - random.randint(margin_x // 2, margin_x), random.randint(0, margin_y // 2)],
        [w_img - random.randint(0, margin_x // 2), h_img - random.randint(margin_y // 2, margin_y)],
        [random.randint(0, margin_x // 2), h_img - random.randint(0, margin_y // 2)],
    ])
    M_persp = cv2.getPerspectiveTransform(src, dst)
    img = cv2.warpPerspective(img, M_persp, (w_img, h_img),
                              borderMode=cv2.BORDER_REPLICATE)

    # --- Rotation légère ±4° ---
    angle = random.uniform(-4, 4)
    center = (w_img // 2, h_img // 2)
    M_rot = cv2.getRotationMatrix2D(center, angle, 1.0)
    img = cv2.warpAffine(img, M_rot, (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)

    # --- Gradient de luminosité (ombre du téléphone) ---
    gradient = np.zeros((h_img, w_img), dtype=np.float32)
    direction = random.choice(["left", "right", "top", "bottom"])
    if direction == "left":
        gradient = np.tile(np.linspace(0.65, 1.0, w_img), (h_img, 1)).astype(np.float32)
    elif direction == "right":
        gradient = np.tile(np.linspace(1.0, 0.65, w_img), (h_img, 1)).astype(np.float32)
    elif direction == "top":
        gradient = np.tile(np.linspace(0.65, 1.0, h_img), (w_img, 1)).T.astype(np.float32)
    else:
        gradient = np.tile(np.linspace(1.0, 0.65, h_img), (w_img, 1)).T.astype(np.float32)

    img = (img.astype(np.float32) * gradient[:, :, np.newaxis]).clip(0, 255).astype(np.uint8)

    # --- Bruit modéré ---
    noise = np.random.normal(0, 12, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # --- Flou léger ---
    img = cv2.GaussianBlur(img, (3, 3), 0.7)

    cv2.imwrite(str(output_jpg_path), img, [cv2.IMWRITE_JPEG_QUALITY, 78])


def apply_heavy_degradation(pdf_path, output_jpg_path):
    """Simule un document très dégradé : pixelisé, très basse résolution, taches."""
    img = _pdf_to_cv2(pdf_path)
    h_img, w_img = img.shape[:2]

    # Réduction de résolution drastique (pixelisation)
    scale = random.uniform(0.15, 0.25)
    small = cv2.resize(img, (int(w_img * scale), int(h_img * scale)),
                       interpolation=cv2.INTER_LINEAR)
    img = cv2.resize(small, (w_img, h_img), interpolation=cv2.INTER_NEAREST)

    # Rotation ±8°
    angle = random.uniform(-8, 8)
    center = (w_img // 2, h_img // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    img = cv2.warpAffine(img, M, (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)

    # Bruit très fort
    noise = np.random.normal(0, 30, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Flou prononcé
    img = cv2.GaussianBlur(img, (7, 7), 2.5)

    # Taches aléatoires (simule un scan très abîmé)
    for _ in range(random.randint(3, 8)):
        cx = random.randint(0, w_img)
        cy = random.randint(0, h_img)
        radius = random.randint(10, 50)
        color = random.randint(100, 180)
        cv2.circle(img, (cx, cy), radius, (color, color, color), -1)

    # Baisser le contraste
    img = cv2.convertScaleAbs(img, alpha=random.uniform(0.5, 0.7), beta=random.randint(20, 50))

    cv2.imwrite(str(output_jpg_path), img, [cv2.IMWRITE_JPEG_QUALITY, 45])


# ============================================================
# SCÉNARIOS DE GÉNÉRATION
# ============================================================

def generate_scn1_perfect(index):
    """SCN-1 : Documents PDF natifs, 100% conformes."""
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    while valideur == emetteur:
        valideur = pick_team()

    doc_type = random.choice(["facture", "facture", "devis"])
    date = random_date()
    items = generate_line_items()

    if doc_type == "facture":
        num = gen_invoice_number()
        filename = f"SCN1_facture_{index:03d}.pdf"
        filepath = OUTPUT_DIR / filename
        # 🔥 AJOUT
        upload_raw_only(filepath, filename, "SCN-9")
        total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
            filepath, company, client, items, num,
            format_date(date), emetteur, valideur, company["siret"]
        )
        ground_truth.append({
            "filename": filename,
            "scenario": "SCN-1",
            "doc_type": "facture",
            "emetteur": emetteur,
            "valideur": valideur,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": company["siret"],
            "client": client["nom"],
            "total_ht": total_ht,
            "tva": tva,
            "total_ttc": ttc_disp,
            "is_valid": True,
            "error_type": None,
            "linked_files": [],
        })
    else:
        num = gen_devis_number()
        filename = f"SCN1_devis_{index:03d}.pdf"
        filepath = OUTPUT_DIR / filename
        # 🔥 AJOUT
        upload_raw_only(filepath, filename, "SCN-9")
        total_ht, tva, ttc = draw_devis_pdf(
            filepath, company, client, items, num,
            format_date(date), emetteur, company["siret"]
        )
        ground_truth.append({
            "filename": filename,
            "scenario": "SCN-1",
            "doc_type": "devis",
            "emetteur": emetteur,
            "valideur": None,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": company["siret"],
            "client": client["nom"],
            "total_ht": total_ht,
            "tva": tva,
            "total_ttc": ttc,
            "is_valid": True,
            "error_type": None,
            "linked_files": [],
        })

    counters["SCN-1"] += 1


def generate_scn2_dirty(index):
    """SCN-2 : Documents convertis en JPG avec dégradations (scanner).
    Génère différents types de documents (facture, devis, urssaf, kbis, siret) en scan bruité.
    """
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    while valideur == emetteur:
        valideur = pick_team()

    temp_pdf = OUTPUT_DIR / f"_temp_scn2_{index}.pdf"

    # Varier le type de document scanné
    doc_types = ["facture", "facture", "devis", "urssaf", "kbis", "attestation_siret"]
    doc_type = random.choice(doc_types)

    gt_entry = {
        "scenario": "SCN-2",
        "doc_type": doc_type,
        "emetteur": emetteur,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": company["siret"],
        "is_valid": True,
        "error_type": "dirty_scan",
        "degradation": "dirty_scan",
        "linked_files": [],
    }

    if doc_type == "facture":
        items = generate_line_items()
        date = random_date()
        num = gen_invoice_number()
        total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, valideur, company["siret"]
        )
        gt_entry.update({"valideur": valideur, "client": client["nom"],
                         "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp})
    elif doc_type == "devis":
        items = generate_line_items()
        date = random_date()
        num = gen_devis_number()
        total_ht, tva, ttc = draw_devis_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, company["siret"]
        )
        gt_entry.update({"valideur": None, "client": client["nom"],
                         "total_ht": total_ht, "tva": tva, "total_ttc": ttc})
    elif doc_type == "urssaf":
        emission = random_date(2025, 2026)
        expiration = emission + timedelta(days=random.randint(180, 365))
        draw_urssaf_pdf(temp_pdf, company, emission, expiration, emetteur, company["siret"])
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "date_emission": format_date(emission),
                         "date_expiration": format_date(expiration)})
    elif doc_type == "kbis":
        dirigeant = pick_team()
        date_immat = random_date(2010, 2020)
        capital = random.choice([1000, 5000, 10000, 50000, 100000])
        draw_kbis_pdf(temp_pdf, company, dirigeant, company["siret"], date_immat, capital)
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "dirigeant": dirigeant,
                         "date_immatriculation": format_date(date_immat), "capital_social": capital})
    elif doc_type == "attestation_siret":
        date_deliv = random_date(2025, 2026)
        draw_siret_pdf(temp_pdf, company, company["siret"], date_deliv)
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "date_delivrance": format_date(date_deliv)})

    filename = f"SCN2_scan_{index:03d}.jpg"
    jpg_path = OUTPUT_DIR / filename
    # 🔥 AJOUT
    upload_raw_only(jpg_path, filename, "SCN-9")
    apply_dirty_scan(temp_pdf, jpg_path)
    temp_pdf.unlink(missing_ok=True)

    gt_entry["filename"] = filename
    ground_truth.append(gt_entry)
    counters["SCN-2"] += 1


def generate_scn3_siret_mismatch(index):
    """SCN-3 : SIRET affiché != SIRET réel de l'entreprise."""
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    items = generate_line_items()
    date = random_date()
    num = gen_invoice_number()
    fake_siret = random_siret()

    filename = f"SCN3_siret_mismatch_{index:03d}.pdf"
    filepath = OUTPUT_DIR / filename
    # 🔥 AJOUT
    upload_raw_only(filepath, filename, "SCN-9")
    total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
        filepath, company, client, items, num,
        format_date(date), emetteur, valideur, fake_siret
    )

    ground_truth.append({
        "filename": filename,
        "scenario": "SCN-3",
        "doc_type": "facture",
        "emetteur": emetteur,
        "valideur": valideur,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": fake_siret,
        "client": client["nom"],
        "total_ht": total_ht,
        "tva": tva,
        "total_ttc": ttc_disp,
        "is_valid": False,
        "error_type": "siret_mismatch",
        "linked_files": [],
    })
    counters["SCN-3"] += 1


def generate_scn4_urssaf_expired(index):
    """SCN-4 : Attestation URSSAF avec date d'expiration passée."""
    company = pick_company()
    emetteur = pick_team()

    emission = random_date(2023, 2024)
    expiration = emission + timedelta(days=random.randint(180, 365))
    if expiration >= datetime(2026, 1, 1):
        expiration = datetime(2025, random.randint(1, 12), random.randint(1, 28))

    filename = f"SCN4_urssaf_expired_{index:03d}.pdf"
    filepath = OUTPUT_DIR / filename
    # 🔥 AJOUT
    upload_raw_only(filepath, filename, "SCN-9")
    draw_urssaf_pdf(filepath, company, emission, expiration, emetteur, company["siret"])

    ground_truth.append({
        "filename": filename,
        "scenario": "SCN-4",
        "doc_type": "urssaf",
        "emetteur": emetteur,
        "valideur": None,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": company["siret"],
        "client": None,
        "date_emission": format_date(emission),
        "date_expiration": format_date(expiration),
        "total_ht": None,
        "tva": None,
        "total_ttc": None,
        "is_valid": False,
        "error_type": "urssaf_expired",
        "linked_files": [],
    })
    counters["SCN-4"] += 1


def generate_scn5_vat_error(index):
    """SCN-5 : Facture où HT + TVA != TTC."""
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    items = generate_line_items()
    date = random_date()
    num = gen_invoice_number()

    filename = f"SCN5_vat_error_{index:03d}.pdf"
    filepath = OUTPUT_DIR / filename
    # 🔥 AJOUT
    upload_raw_only(filepath, filename, "SCN-9")
    total_ht, tva, ttc_correct, ttc_displayed = draw_invoice_pdf(
        filepath, company, client, items, num,
        format_date(date), emetteur, valideur, company["siret"],
        force_vat_error=True
    )

    ground_truth.append({
        "filename": filename,
        "scenario": "SCN-5",
        "doc_type": "facture",
        "emetteur": emetteur,
        "valideur": valideur,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": company["siret"],
        "client": client["nom"],
        "total_ht": total_ht,
        "tva": tva,
        "total_ttc": ttc_displayed,
        "total_ttc_correct": ttc_correct,
        "is_valid": False,
        "error_type": "vat_calculation_error",
        "linked_files": [],
    })
    counters["SCN-5"] += 1


def generate_scn6_smartphone(index):
    """SCN-6 : Photo smartphone avec perspective warp + gradient de lumière.
    Génère différents types de documents en photo smartphone.
    """
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    while valideur == emetteur:
        valideur = pick_team()

    temp_pdf = OUTPUT_DIR / f"_temp_scn6_{index}.pdf"

    doc_types = ["facture", "devis", "urssaf", "kbis", "attestation_siret"]
    doc_type = random.choice(doc_types)

    gt_entry = {
        "scenario": "SCN-6",
        "doc_type": doc_type,
        "emetteur": emetteur,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": company["siret"],
        "is_valid": True,
        "error_type": "smartphone_photo",
        "degradation": "smartphone",
        "linked_files": [],
    }

    if doc_type == "facture":
        items = generate_line_items()
        date = random_date()
        num = gen_invoice_number()
        total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, valideur, company["siret"]
        )
        gt_entry.update({"valideur": valideur, "client": client["nom"],
                         "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp})
    elif doc_type == "devis":
        items = generate_line_items()
        date = random_date()
        num = gen_devis_number()
        total_ht, tva, ttc = draw_devis_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, company["siret"]
        )
        gt_entry.update({"valideur": None, "client": client["nom"],
                         "total_ht": total_ht, "tva": tva, "total_ttc": ttc})
    elif doc_type == "urssaf":
        emission = random_date(2025, 2026)
        expiration = emission + timedelta(days=random.randint(180, 365))
        draw_urssaf_pdf(temp_pdf, company, emission, expiration, emetteur, company["siret"])
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "date_emission": format_date(emission),
                         "date_expiration": format_date(expiration)})
    elif doc_type == "kbis":
        dirigeant = pick_team()
        date_immat = random_date(2010, 2020)
        capital = random.choice([1000, 5000, 10000, 50000, 100000])
        draw_kbis_pdf(temp_pdf, company, dirigeant, company["siret"], date_immat, capital)
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "dirigeant": dirigeant,
                         "date_immatriculation": format_date(date_immat), "capital_social": capital})
    elif doc_type == "attestation_siret":
        date_deliv = random_date(2025, 2026)
        draw_siret_pdf(temp_pdf, company, company["siret"], date_deliv)
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "date_delivrance": format_date(date_deliv)})

    filename = f"SCN6_smartphone_{index:03d}.jpg"
    jpg_path = OUTPUT_DIR / filename
    # 🔥 AJOUT
    upload_raw_only(jpg_path, filename, "SCN-9")
    apply_smartphone_scan(temp_pdf, jpg_path)
    temp_pdf.unlink(missing_ok=True)

    gt_entry["filename"] = filename
    ground_truth.append(gt_entry)
    counters["SCN-6"] += 1


def apply_partial_occlusion(pdf_path, output_pdf_path, zones_to_hide):
    """Ouvre un PDF et dessine des rectangles blancs sur des zones aléatoires
    pour simuler des champs partiellement manquants/illisibles.
    Retourne la liste des champs masqués.
    """
    doc = fitz.open(str(pdf_path))
    page = doc[0]
    pw, ph = page.rect.width, page.rect.height

    hidden_fields = []
    zone_defs = {
        "siret": fitz.Rect(pw * 0.5, 0, pw, ph * 0.12),
        "total": fitz.Rect(pw * 0.4, ph * 0.55, pw * 0.95, ph * 0.75),
        "header_left": fitz.Rect(0, 0, pw * 0.4, ph * 0.12),
        "client": fitz.Rect(pw * 0.5, ph * 0.1, pw, ph * 0.22),
        "footer": fitz.Rect(0, ph * 0.92, pw, ph),
    }

    for zone_name in zones_to_hide:
        if zone_name in zone_defs:
            rect = zone_defs[zone_name]
            page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
            hidden_fields.append(zone_name)

    doc.save(str(output_pdf_path))
    doc.close()
    return hidden_fields


def generate_scn10_partial(index):
    """SCN-10 : Documents avec champs partiellement manquants ou masqués.
    Simule des documents tronqués, mal scannés avec des parties manquantes.
    """
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    temp_pdf = OUTPUT_DIR / f"_temp_scn10_{index}.pdf"

    doc_type = random.choice(["facture", "devis"])
    items = generate_line_items()
    date = random_date()

    if doc_type == "facture":
        num = gen_invoice_number()
        total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, valideur, company["siret"]
        )
    else:
        num = gen_devis_number()
        total_ht, tva, ttc = draw_devis_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, company["siret"]
        )
        ttc_disp = ttc

    # Choisir 1 à 2 zones à masquer
    possible_zones = ["siret", "total", "client", "footer"]
    nb_zones = random.randint(1, 2)
    zones = random.sample(possible_zones, nb_zones)

    filename = f"SCN10_partial_{index:03d}.pdf"
    filepath = OUTPUT_DIR / filename
    
    # 🔥 AJOUT
    upload_raw_only(filepath, filename, "SCN-9")
    hidden = apply_partial_occlusion(temp_pdf, filepath, zones)
    temp_pdf.unlink(missing_ok=True)

    ground_truth.append({
        "filename": filename,
        "scenario": "SCN-10",
        "doc_type": doc_type,
        "emetteur": emetteur,
        "valideur": valideur if doc_type == "facture" else None,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": company["siret"],
        "client": client["nom"],
        "total_ht": total_ht,
        "tva": tva,
        "total_ttc": ttc_disp,
        "is_valid": True,
        "error_type": "partial_occlusion",
        "hidden_fields": hidden,
        "linked_files": [],
    })
    counters["SCN-10"] += 1


def generate_scn9_pixelized(index):
    """SCN-9 : Documents très dégradés — pixelisés, taches, très basse qualité.
    Teste les limites de l'OCR et de la classification.
    """
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    temp_pdf = OUTPUT_DIR / f"_temp_scn9_{index}.pdf"

    doc_types = ["facture", "devis", "urssaf", "kbis"]
    doc_type = random.choice(doc_types)

    gt_entry = {
        "scenario": "SCN-9",
        "doc_type": doc_type,
        "emetteur": emetteur,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": company["siret"],
        "is_valid": True,
        "error_type": "heavy_degradation",
        "degradation": "pixelized",
        "linked_files": [],
    }

    if doc_type == "facture":
        items = generate_line_items()
        num = gen_invoice_number()
        date = random_date()
        total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, valideur, company["siret"]
        )
        gt_entry.update({"valideur": valideur, "client": client["nom"],
                         "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp})
    elif doc_type == "devis":
        items = generate_line_items()
        num = gen_devis_number()
        date = random_date()
        total_ht, tva, ttc = draw_devis_pdf(
            temp_pdf, company, client, items, num,
            format_date(date), emetteur, company["siret"]
        )
        gt_entry.update({"valideur": None, "client": client["nom"],
                         "total_ht": total_ht, "tva": tva, "total_ttc": ttc})
    elif doc_type == "urssaf":
        emission = random_date(2025, 2026)
        expiration = emission + timedelta(days=random.randint(180, 365))
        draw_urssaf_pdf(temp_pdf, company, emission, expiration, emetteur, company["siret"])
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "date_emission": format_date(emission),
                         "date_expiration": format_date(expiration)})
    elif doc_type == "kbis":
        dirigeant = pick_team()
        date_immat = random_date(2010, 2020)
        capital = random.choice([1000, 5000, 10000, 50000, 100000])
        draw_kbis_pdf(temp_pdf, company, dirigeant, company["siret"], date_immat, capital)
        gt_entry.update({"valideur": None, "client": None, "total_ht": None, "tva": None,
                         "total_ttc": None, "dirigeant": dirigeant,
                         "date_immatriculation": format_date(date_immat), "capital_social": capital})

    filename = f"SCN9_pixelized_{index:03d}.jpg"
    jpg_path = OUTPUT_DIR / filename
    # sauvegarde
    image.save(jpg_path)
    # 🔥 AJOUT
    upload_raw_only(jpg_path, filename, "SCN-9")
    apply_heavy_degradation(temp_pdf, jpg_path)
    temp_pdf.unlink(missing_ok=True)

    gt_entry["filename"] = filename
    ground_truth.append(gt_entry)
    counters["SCN-9"] += 1


def generate_scn7_combined(index):
    """SCN-7 : Scénarios combinés — scan bruité + erreur (SIRET mismatch OU TVA fausse).
    Teste la capacité de l'IA à détecter des anomalies même sur des documents dégradés.
    """
    company = pick_company()
    client = pick_company()
    while client["siret"] == company["siret"]:
        client = pick_company()

    emetteur = pick_team()
    valideur = pick_team()
    items = generate_line_items()
    date = random_date()
    num = gen_invoice_number()

    # Choisir le type d'erreur
    error_choice = random.choice(["siret_mismatch", "vat_error"])
    if error_choice == "siret_mismatch":
        siret_display = random_siret()
        force_vat = False
    else:
        siret_display = company["siret"]
        force_vat = True

    # Choisir le type de dégradation
    degrad_choice = random.choice(["dirty_scan", "smartphone"])

    temp_pdf = OUTPUT_DIR / f"_temp_scn7_{index}.pdf"
    total_ht, tva, ttc_correct, ttc_displayed = draw_invoice_pdf(
        temp_pdf, company, client, items, num,
        format_date(date), emetteur, valideur, siret_display,
        force_vat_error=force_vat
    )

    filename = f"SCN7_combined_{index:03d}.jpg"
    jpg_path = OUTPUT_DIR / filename
    # 🔥 AJOUT
    upload_raw_only(jpg_path, filename, "SCN-9")
    if degrad_choice == "dirty_scan":
        apply_dirty_scan(temp_pdf, jpg_path)
    else:
        apply_smartphone_scan(temp_pdf, jpg_path)

    temp_pdf.unlink(missing_ok=True)

    ground_truth.append({
        "filename": filename,
        "scenario": "SCN-7",
        "doc_type": "facture",
        "emetteur": emetteur,
        "valideur": valideur,
        "entreprise": company["nom"],
        "siret_attendu": company["siret"],
        "siret_affiche": siret_display,
        "client": client["nom"],
        "total_ht": total_ht,
        "tva": tva,
        "total_ttc": ttc_displayed,
        "total_ttc_correct": ttc_correct if force_vat else None,
        "is_valid": False,
        "error_type": f"combined_{error_choice}_{degrad_choice}",
        "degradation": degrad_choice,
        "linked_files": [],
    })
    counters["SCN-7"] += 1


def generate_scn8_consistency():
    """SCN-8 : Packs de cohérence croisée (Facture + Kbis + URSSAF) par entreprise.
    Cas A (3 entreprises) : SIRET identique sur les 3 documents → valide.
    Cas B (2 entreprises) : SIRET facture != SIRET kbis → invalide.
    """
    # Sélectionner 5 entreprises distinctes
    companies_pool = random.sample(COMPANIES, min(5, len(COMPANIES)))

    for i, company in enumerate(companies_pool, 1):
        is_cas_b = i > 3  # 3 premiers = Cas A, 2 derniers = Cas B
        cas_label = "B" if is_cas_b else "A"

        client = pick_company()
        while client["siret"] == company["siret"]:
            client = pick_company()

        emetteur = pick_team()
        valideur = pick_team()
        while valideur == emetteur:
            valideur = pick_team()
        dirigeant = pick_team()

        # SIRET à afficher sur la facture
        if is_cas_b:
            facture_siret = random_siret()  # SIRET différent !
        else:
            facture_siret = company["siret"]  # SIRET correct

        # --- Noms de fichiers ---
        f_facture = f"SCN8_pack{i}_cas{cas_label}_facture.pdf"
        f_kbis = f"SCN8_pack{i}_cas{cas_label}_kbis.pdf"
        f_urssaf = f"SCN8_pack{i}_cas{cas_label}_urssaf.pdf"
        f_rib = f"SCN8_pack{i}_cas{cas_label}_rib.pdf"
        f_siret = f"SCN8_pack{i}_cas{cas_label}_siret.pdf"
        linked = [f_facture, f_kbis, f_urssaf, f_rib, f_siret]

        # --- Facture ---
        items = generate_line_items()
        date = random_date()
        num = gen_invoice_number()
        total_ht, tva, ttc, ttc_disp = draw_invoice_pdf(
            OUTPUT_DIR / f_facture, company, client, items, num,
            format_date(date), emetteur, valideur, facture_siret
        )
        ground_truth.append({
            "filename": f_facture,
            "scenario": "SCN-8",
            "doc_type": "facture",
            "emetteur": emetteur,
            "valideur": valideur,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": facture_siret,
            "client": client["nom"],
            "total_ht": total_ht,
            "tva": tva,
            "total_ttc": ttc_disp,
            "is_valid": not is_cas_b,
            "error_type": "siret_cross_mismatch" if is_cas_b else None,
            "linked_files": [f for f in linked if f != f_facture],
        })

        # --- Kbis (toujours le vrai SIRET) ---
        date_immat = random_date(2010, 2020)
        capital = random.choice([1000, 5000, 10000, 50000, 100000, 500000])
        draw_kbis_pdf(
            OUTPUT_DIR / f_kbis, company, dirigeant,
            company["siret"], date_immat, capital
        )
        ground_truth.append({
            "filename": f_kbis,
            "scenario": "SCN-8",
            "doc_type": "kbis",
            "emetteur": None,
            "valideur": None,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": company["siret"],
            "dirigeant": dirigeant,
            "date_immatriculation": format_date(date_immat),
            "capital_social": capital,
            "client": None,
            "total_ht": None,
            "tva": None,
            "total_ttc": None,
            "is_valid": True,
            "error_type": None,
            "linked_files": [f for f in linked if f != f_kbis],
        })

        # --- URSSAF (valide, date future) ---
        emission = random_date(2025, 2026)
        expiration = emission + timedelta(days=random.randint(180, 365))
        draw_urssaf_pdf(
            OUTPUT_DIR / f_urssaf, company, emission, expiration,
            emetteur, company["siret"]
        )
        ground_truth.append({
            "filename": f_urssaf,
            "scenario": "SCN-8",
            "doc_type": "urssaf",
            "emetteur": emetteur,
            "valideur": None,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": company["siret"],
            "client": None,
            "date_emission": format_date(emission),
            "date_expiration": format_date(expiration),
            "total_ht": None,
            "tva": None,
            "total_ttc": None,
            "is_valid": True,
            "error_type": None,
            "linked_files": [f for f in linked if f != f_urssaf],
        })

        # --- RIB ---
        iban = gen_iban()
        bic = gen_bic()
        draw_rib_pdf(
            OUTPUT_DIR / f_rib, company, company["siret"], iban, bic
        )
        ground_truth.append({
            "filename": f_rib,
            "scenario": "SCN-8",
            "doc_type": "rib",
            "emetteur": None,
            "valideur": None,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": company["siret"],
            "iban": iban,
            "bic": bic,
            "client": None,
            "total_ht": None,
            "tva": None,
            "total_ttc": None,
            "is_valid": True,
            "error_type": None,
            "linked_files": [f for f in linked if f != f_rib],
        })

        # --- Attestation SIRET ---
        date_siret = random_date(2025, 2026)
        draw_siret_pdf(
            OUTPUT_DIR / f_siret, company, company["siret"], date_siret
        )
        ground_truth.append({
            "filename": f_siret,
            "scenario": "SCN-8",
            "doc_type": "attestation_siret",
            "emetteur": None,
            "valideur": None,
            "entreprise": company["nom"],
            "siret_attendu": company["siret"],
            "siret_affiche": company["siret"],
            "client": None,
            "date_delivrance": format_date(date_siret),
            "total_ht": None,
            "tva": None,
            "total_ttc": None,
            "is_valid": True,
            "error_type": None,
            "linked_files": [f for f in linked if f != f_siret],
        })

        counters["SCN-8"] += 5  # 5 docs par pack


# ============================================================
# MAIN
# ============================================================
def assign_train_test_split(ground_truth_list, test_ratio=0.2):
    """Assigne chaque document au split train ou test.
    Les packs SCN-8 restent groupés dans le même split.
    """
    # Regrouper les packs SCN-8
    packs = {}
    standalone = []
    for entry in ground_truth_list:
        if entry["scenario"] == "SCN-8":
            # Extraire le numéro de pack
            parts = entry["filename"].split("_")
            pack_id = parts[1]  # e.g. "pack1"
            packs.setdefault(pack_id, []).append(entry)
        else:
            standalone.append(entry)

    # Shuffle standalone
    random.shuffle(standalone)
    split_idx = int(len(standalone) * (1 - test_ratio))
    for entry in standalone[:split_idx]:
        entry["split"] = "train"
    for entry in standalone[split_idx:]:
        entry["split"] = "test"

    # Assigner les packs (garder groupés)
    pack_keys = list(packs.keys())
    random.shuffle(pack_keys)
    pack_split_idx = max(1, int(len(pack_keys) * (1 - test_ratio)))
    for pk in pack_keys[:pack_split_idx]:
        for entry in packs[pk]:
            entry["split"] = "train"
    for pk in pack_keys[pack_split_idx:]:
        for entry in packs[pk]:
            entry["split"] = "test"


def add_classification_metadata(ground_truth_list):
    """Ajoute des métadonnées normalisées pour l'entraînement de classifieurs."""
    # Mapping des catégories normalisées
    category_map = {
        "facture": "FACTURE",
        "devis": "DEVIS",
        "urssaf": "ATTESTATION_URSSAF",
        "kbis": "EXTRAIT_KBIS",
        "rib": "RIB",
        "attestation_siret": "ATTESTATION_SIRET",
    }
    for entry in ground_truth_list:
        entry["category"] = category_map.get(entry["doc_type"], "INCONNU")
        entry["format"] = "image" if entry["filename"].endswith(".jpg") else "pdf"
        # Niveau de difficulté pour benchmark
        if entry.get("degradation") == "pixelized":
            entry["difficulty"] = "hard"
        elif entry.get("degradation") in ("dirty_scan", "smartphone"):
            entry["difficulty"] = "medium"
        elif entry.get("error_type") == "partial_occlusion":
            entry["difficulty"] = "medium"
        elif entry.get("error_type") and "combined" in str(entry.get("error_type", "")):
            entry["difficulty"] = "hard"
        else:
            entry["difficulty"] = "easy"


def main():
    print("=" * 60)
    print("  GÉNÉRATION DU DATASET — Hackathon 2026")
    print("=" * 60)
    print()

    # SCN-1 : 30 documents parfaits (PDF natifs, conformes)
    print("[SCN-1] Génération de 30 documents conformes...")
    for i in range(1, 31):
        generate_scn1_perfect(i)
    print(f"  -> {counters['SCN-1']} documents générés")

    # SCN-2 : 25 scans dégradés (tous types de documents)
    print("[SCN-2] Génération de 25 scans dégradés (JPG)...")
    for i in range(1, 26):
        generate_scn2_dirty(i)
    print(f"  -> {counters['SCN-2']} documents générés")

    # SCN-3 : 15 SIRET mismatch
    print("[SCN-3] Génération de 15 documents SIRET mismatch...")
    for i in range(1, 16):
        generate_scn3_siret_mismatch(i)
    print(f"  -> {counters['SCN-3']} documents générés")

    # SCN-4 : 15 URSSAF expirées
    print("[SCN-4] Génération de 15 attestations URSSAF expirées...")
    for i in range(1, 16):
        generate_scn4_urssaf_expired(i)
    print(f"  -> {counters['SCN-4']} documents générés")

    # SCN-5 : 10 erreurs TVA
    print("[SCN-5] Génération de 10 factures avec erreur TVA...")
    for i in range(1, 11):
        generate_scn5_vat_error(i)
    print(f"  -> {counters['SCN-5']} documents générés")

    # SCN-6 : 15 photos smartphone (tous types de documents)
    print("[SCN-6] Génération de 15 photos smartphone (perspective + gradient)...")
    for i in range(1, 16):
        generate_scn6_smartphone(i)
    print(f"  -> {counters['SCN-6']} documents générés")

    # SCN-7 : 15 scénarios combinés (scan + erreur)
    print("[SCN-7] Génération de 15 documents combinés (dégradation + erreur)...")
    for i in range(1, 16):
        generate_scn7_combined(i)
    print(f"  -> {counters['SCN-7']} documents générés")

    # SCN-8 : 5 packs cohérence croisée (Facture + Kbis + URSSAF + RIB + SIRET)
    print("[SCN-8] Génération de 5 packs de cohérence croisée...")
    generate_scn8_consistency()
    print(f"  -> {counters['SCN-8']} documents générés (5 packs x 5 docs)")

    # SCN-9 : 10 documents très dégradés (pixelisés)
    print("[SCN-9] Génération de 10 documents très dégradés (pixelisés)...")
    for i in range(1, 11):
        generate_scn9_pixelized(i)
    print(f"  -> {counters['SCN-9']} documents générés")

    # SCN-10 : 10 documents avec champs partiellement masqués
    print("[SCN-10] Génération de 10 documents avec champs manquants...")
    for i in range(1, 11):
        generate_scn10_partial(i)
    print(f"  -> {counters['SCN-10']} documents générés")

    # --- Post-traitement ---
    print()
    print("[POST] Ajout des métadonnées de classification...")
    add_classification_metadata(ground_truth)

    print("[POST] Assignation du split train/test (80/20)...")
    assign_train_test_split(ground_truth, test_ratio=0.2)

    # Sauvegarder ground_truth.json
    gt_path = BASE_DIR / "output" / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, ensure_ascii=False, indent=2)

    # Sauvegarder des fichiers train/test séparés
    train_data = [e for e in ground_truth if e.get("split") == "train"]
    test_data = [e for e in ground_truth if e.get("split") == "test"]

    train_path = BASE_DIR / "output" / "ground_truth_train.json"
    test_path = BASE_DIR / "output" / "ground_truth_test.json"
    with open(train_path, "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    with open(test_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print("  RÉSUMÉ")
    print("=" * 60)
    total = sum(counters.values())
    for scn, count in sorted(counters.items()):
        print(f"  {scn} : {count} documents")
    print(f"  {'-' * 30}")
    print(f"  TOTAL : {total} documents")
    print(f"  Train : {len(train_data)} | Test : {len(test_data)}")
    print()

    # Résumé par type de document
    from collections import Counter
    type_counts = Counter(e["doc_type"] for e in ground_truth)
    print("  Par type de document :")
    for dtype, cnt in sorted(type_counts.items()):
        print(f"    {dtype}: {cnt}")
    print()

    # Résumé par difficulté
    diff_counts = Counter(e.get("difficulty", "?") for e in ground_truth)
    print("  Par difficulté :")
    for diff, cnt in sorted(diff_counts.items()):
        print(f"    {diff}: {cnt}")
    print()

    print(f"  Documents : {OUTPUT_DIR}")
    print(f"  Ground truth : {gt_path}")
    print(f"  Train split : {train_path}")
    print(f"  Test split  : {test_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
