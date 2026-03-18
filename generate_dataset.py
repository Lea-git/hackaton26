#!/usr/bin/env python3
"""
generate_dataset.py — Génération d'un dataset synthétique de documents administratifs.
Hackathon 2026 — Plateforme de traitement de documents.

Les documents sont générés en mémoire et uploadés directement dans la Raw zone
du Data Lake MinIO — aucun fichier n'est écrit sur le disque local.

Usage :
    python generate_dataset.py
    python generate_dataset.py --prefix 2026/custom/
"""

import argparse
import io
import json
import math
import os
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from faker import Faker
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from datalake import DataLakeClient

# ─────────────────────────────────────────────────────────────
#  Seeds & configuration
# ─────────────────────────────────────────────────────────────
fake = Faker("fr_FR")
random.seed(42)
Faker.seed(42)
np.random.seed(42)

BASE_DIR = Path(__file__).parent
DEFAULT_PREFIX = "dataset/"

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
counters = {f"SCN-{i}": 0 for i in range(1, 11)}


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def pick_team():
    return random.choice(TEAM_MEMBERS)

def pick_company():
    return random.choice(COMPANIES)

def random_siret():
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
    digits = "".join(random.choices(string.digits, k=23))
    return f"FR76 {digits[:4]} {digits[4:8]} {digits[8:12]} {digits[12:16]} {digits[16:20]} {digits[20:]}"

def gen_bic():
    banks = ["BNPAFRPP", "SOGEFRPP", "CRLYFRPP", "AGRIFRPP", "CEPAFRPP",
             "CMCIFRPP", "CCBPFRPP", "BFCOFRPP", "NATXFRPP", "BOUSFRPP"]
    return random.choice(banks)

def random_date(start_year=2025, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

def format_date(dt):
    return dt.strftime("%d/%m/%Y")

def generate_line_items(count=None):
    if count is None:
        count = random.randint(2, 6)
    descriptions = [
        "Prestation de conseil en informatique", "Développement application web",
        "Maintenance serveurs (forfait mensuel)", "Audit de sécurité SI",
        "Formation équipe technique", "Licence logicielle annuelle",
        "Hébergement cloud (trimestre)", "Support technique niveau 2",
        "Installation réseau fibre optique", "Fourniture matériel informatique",
        "Travaux de maçonnerie", "Pose de cloisons sèches",
        "Nettoyage industriel (forfait)", "Gardiennage site (mois)",
        "Transport marchandises", "Consultation RH", "Rénovation bureaux",
        "Câblage électrique bâtiment", "Étude de faisabilité technique",
        "Intégration API partenaires",
    ]
    items = []
    for _ in range(count):
        qty = random.randint(1, 10)
        unit_price = round(random.uniform(150, 3500), 2)
        total_ht = round(qty * unit_price, 2)
        items.append({"description": random.choice(descriptions),
                      "qty": qty, "unit_price": unit_price, "total_ht": total_ht})
    return items


# ─────────────────────────────────────────────────────────────
#  PDF builders → retournent des bytes (en mémoire)
# ─────────────────────────────────────────────────────────────

def build_invoice_pdf(company, client, items, invoice_num, date_str,
                      emetteur, valideur, siret_display, tva_rate=0.20,
                      force_vat_error=False):
    """Construit une facture PDF en mémoire et retourne (bytes, total_ht, tva, ttc, ttc_disp)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    color_primary = HexColor("#1a5276")
    color_accent  = HexColor("#2980b9")
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
    c.drawString(30, y,      f"Émis par : {emetteur}")
    c.drawString(30, y - 14, f"Validé par : {valideur}")

    c.setFillColor(color_accent)
    c.rect(w - 250, y - 10, 220, 60, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w - 240, y + 30, "CLIENT")
    c.setFont("Helvetica", 9)
    c.drawString(w - 240, y + 16, client["nom"])
    c.drawString(w - 240, y + 3,  f"SIRET : {client['siret']}")
    c.drawString(w - 240, y - 10, client["adresse"][:40])

    y_table = y - 50
    data = [["Description", "Qté", "PU HT (€)", "Total HT (€)"]]
    for item in items:
        data.append([item["description"][:40], str(item["qty"]),
                     f"{item['unit_price']:.2f}", f"{item['total_ht']:.2f}"])

    total_ht   = sum(i["total_ht"] for i in items)
    tva_amount = round(total_ht * tva_rate, 2)
    total_ttc  = round(total_ht + tva_amount, 2)

    if force_vat_error:
        error_delta    = round(random.uniform(5, 80), 2) * random.choice([1, -1])
        total_ttc_disp = round(total_ttc + error_delta, 2)
    else:
        total_ttc_disp = total_ttc

    data.append(["", "", "Total HT",             f"{total_ht:.2f}"])
    data.append(["", "", f"TVA ({int(tva_rate*100)}%)", f"{tva_amount:.2f}"])
    data.append(["", "", "Total TTC",             f"{total_ttc_disp:.2f}"])

    t = Table(data, colWidths=[220, 40, 80, 90])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_primary),
        ("TEXTCOLOR",  (0, 0), (-1, 0), white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ALIGN",      (1, 0), (-1, -1), "RIGHT"),
        ("GRID",       (0, 0), (-1, -4), 0.5, HexColor("#cccccc")),
        ("BACKGROUND", (2, -3), (-1, -1), HexColor("#ecf0f1")),
        ("FONTNAME",   (2, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE",  (2, -3), (-1, -3), 1, color_primary),
    ]))
    _, t_h = t.wrap(0, 0)
    t.drawOn(c, 30, y_table - t_h)

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawString(30, 40, f"{company['nom']} — SIRET {siret_display} — {company['adresse']}")
    c.drawString(30, 28, "TVA intracommunautaire : FR" + siret_display[:11])
    c.drawCentredString(w / 2, 15, "Document généré automatiquement — Hackathon 2026")
    c.save()

    return buf.getvalue(), total_ht, tva_amount, total_ttc, total_ttc_disp


def build_devis_pdf(company, client, items, devis_num, date_str,
                    emetteur, siret_display, tva_rate=0.20):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    color_primary = HexColor("#1b4332")
    color_accent  = HexColor("#2d6a4f")
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
    c.drawString(w - 240, y + 8,  client["nom"])
    c.drawString(w - 240, y - 5,  f"SIRET : {client['siret']}")

    y_table = y - 50
    data = [["Description", "Qté", "PU HT (€)", "Total HT (€)"]]
    for item in items:
        data.append([item["description"][:40], str(item["qty"]),
                     f"{item['unit_price']:.2f}", f"{item['total_ht']:.2f}"])

    total_ht   = sum(i["total_ht"] for i in items)
    tva_amount = round(total_ht * tva_rate, 2)
    total_ttc  = round(total_ht + tva_amount, 2)
    data.append(["", "", "Total HT",             f"{total_ht:.2f}"])
    data.append(["", "", f"TVA ({int(tva_rate*100)}%)", f"{tva_amount:.2f}"])
    data.append(["", "", "Total TTC",             f"{total_ttc:.2f}"])

    t = Table(data, colWidths=[220, 40, 80, 90])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_primary),
        ("TEXTCOLOR",  (0, 0), (-1, 0), white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("ALIGN",      (1, 0), (-1, -1), "RIGHT"),
        ("GRID",       (0, 0), (-1, -4), 0.5, HexColor("#cccccc")),
        ("BACKGROUND", (2, -3), (-1, -1), HexColor("#ecf0f1")),
        ("FONTNAME",   (2, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE",  (2, -3), (-1, -3), 1, color_primary),
    ]))
    _, t_h = t.wrap(0, 0)
    t.drawOn(c, 30, y_table - t_h)

    c.setFont("Helvetica", 7)
    c.setFillColor(HexColor("#888888"))
    c.drawString(30, 40, f"{company['nom']} — SIRET {siret_display} — {company['adresse']}")
    c.drawCentredString(w / 2, 15, "Document généré automatiquement — Hackathon 2026")
    c.save()

    return buf.getvalue(), total_ht, tva_amount, total_ttc


def build_urssaf_pdf(company, date_emission, date_expiration, emetteur, siret_display):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
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
    c.drawString(50, y,      "Je soussigné(e), l'URSSAF, atteste que l'entreprise ci-dessous")
    c.drawString(50, y - 18, "est à jour de ses obligations déclaratives et de paiement.")

    y -= 55
    for label, value in [("Entreprise :", company["nom"]), ("SIRET :", siret_display),
                          ("Adresse :", company["adresse"]), ("Activité :", company["activite"])]:
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y, label)
        c.setFont("Helvetica", 11);      c.drawString(160, y, value)
        y -= 22

    y -= 45
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, f"Date d'émission :  {format_date(date_emission)}")
    y -= 25
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(50, y, f"Date d'expiration :  {format_date(date_expiration)}")

    y -= 60
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    c.drawString(50, y,      f"Délivré par : {emetteur}")
    c.drawString(50, y - 18, "Pour le Directeur de l'URSSAF")

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

    return buf.getvalue()


def build_kbis_pdf(company, dirigeant, siret_display, date_immat, capital):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    color_greffe = HexColor("#2c3e50")
    color_gold   = HexColor("#c9a84c")
    c.setFillColor(color_greffe)
    c.rect(0, h - 110, w, 110, fill=1, stroke=0)
    c.setStrokeColor(color_gold); c.setLineWidth(2)
    c.line(30, h - 108, w - 30, h - 108)
    c.setFillColor(color_gold); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 25, "RÉPUBLIQUE FRANÇAISE")
    c.setFillColor(white); c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 52, "EXTRAIT KBIS")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 72, "Greffe du Tribunal de Commerce")
    kbis_num = gen_kbis_number()
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 90,  f"Réf : {kbis_num}")
    c.drawCentredString(w / 2, h - 102, f"Délivré le : {format_date(random_date(2025, 2026))}")

    y = h - 145
    c.setFillColor(black)
    siren, nic = siret_display[:9], siret_display[9:]
    for label, value in [
        ("Dénomination sociale", company["nom"]),
        ("SIREN", siren), ("NIC (Siège)", nic), ("SIRET (Siège)", siret_display),
        ("Forme juridique", random.choice(["SAS", "SARL", "SA", "EURL", "SCI"])),
        ("Adresse du siège", company["adresse"]),
        ("Activité (NAF)", company["activite"]),
        ("Date d'immatriculation", format_date(date_immat)),
        ("Capital social", f"{capital:,.0f} EUR".replace(",", " ")),
        ("Dirigeant", dirigeant),
        ("Qualité", random.choice(["Président", "Gérant", "Directeur Général"])),
    ]:
        c.setFont("Helvetica-Bold", 11); c.drawString(50,  y, f"{label} :")
        c.setFont("Helvetica", 11);      c.drawString(230, y, str(value))
        y -= 28

    y -= 30
    c.setStrokeColor(HexColor("#27ae60")); c.setFillColor(HexColor("#eafaf1"))
    c.roundRect(50, y - 25, w - 100, 40, 5, fill=1, stroke=1)
    c.setFillColor(HexColor("#27ae60")); c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, y - 12, "INSCRIPTION ACTIVE AU RCS")

    y -= 70
    c.setFillColor(HexColor("#555555")); c.setFont("Helvetica", 8)
    c.drawString(50, y,      "Le présent extrait est délivré en application des articles R.123-150 et suivants")
    c.drawString(50, y - 12, "du Code de Commerce. Il certifie l'inscription au Registre du Commerce et des Sociétés.")

    c.setFont("Helvetica", 7); c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, f"Greffe du Tribunal de Commerce — {kbis_num}")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()

    return buf.getvalue()


def build_rib_pdf(company, siret_display, iban, bic):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    color_bank  = HexColor("#1a237e")
    color_light = HexColor("#e8eaf6")
    c.setFillColor(color_bank); c.rect(0, h - 80, w, 80, fill=1, stroke=0)
    c.setFillColor(white); c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 40, "RELEVÉ D'IDENTITÉ BANCAIRE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 60, "RIB — Coordonnées Bancaires")

    y = h - 120
    c.setFillColor(color_light); c.roundRect(40, y - 80, w - 80, 90, 5, fill=1, stroke=0)
    c.setFillColor(black); c.setFont("Helvetica-Bold", 12)
    c.drawString(60, y - 10, "Titulaire du compte")
    c.setFont("Helvetica", 11)
    c.drawString(60, y - 30, company["nom"])
    c.drawString(60, y - 48, company["adresse"])
    c.drawString(60, y - 66, f"SIRET : {siret_display}")

    y -= 110
    iban_clean = iban.replace(" ", "")
    col_widths = [120, 120, 140, 80]
    t = Table(
        [["Code Banque", "Code Guichet", "N° de Compte", "Clé RIB"],
         [iban_clean[4:9], iban_clean[9:14], iban_clean[14:25], iban_clean[25:27]]],
        colWidths=col_widths
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), color_bank),
        ("TEXTCOLOR",  (0, 0), (-1, 0), white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",   (0, 1), (-1, 1), "Courier-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 11),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("GRID",       (0, 0), (-1, -1), 1, HexColor("#cccccc")),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    _, t_h = t.wrap(0, 0)
    t.drawOn(c, (w - sum(col_widths)) / 2, y - t_h)

    y -= t_h + 40
    c.setFillColor(color_light); c.roundRect(40, y - 70, w - 80, 80, 5, fill=1, stroke=0)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 12); c.drawString(60,  y - 10, "IBAN :")
    c.setFont("Courier-Bold", 13);   c.drawString(130, y - 10, iban)
    c.setFont("Helvetica-Bold", 12); c.drawString(60,  y - 40, "BIC / SWIFT :")
    c.setFont("Courier-Bold", 13);   c.drawString(180, y - 40, bic)

    y -= 100
    c.setFont("Helvetica-Bold", 11); c.drawString(60, y, "Domiciliation :")
    c.setFont("Helvetica", 11)
    banque = random.choice(["BNP Paribas", "Société Générale", "Crédit Agricole", "Caisse d'Épargne"])
    c.drawString(180, y, f"{banque} — Agence Centrale")

    c.setFont("Helvetica", 7); c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, f"{company['nom']} — SIRET {siret_display}")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()

    return buf.getvalue()


def build_siret_pdf(company, siret_display, date_delivrance):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    color_insee = HexColor("#0055A4")
    c.setFillColor(color_insee); c.rect(0, h - 110, w, 110, fill=1, stroke=0)
    c.setFillColor(HexColor("#FFD700")); c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2, h - 20, "RÉPUBLIQUE FRANÇAISE")
    c.setFillColor(white); c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 48, "ATTESTATION DE SITUATION SIRENE")
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 68, "INSEE — Institut National de la Statistique et des Études Économiques")
    ref = f"SIRENE-{random.randint(100000, 999999)}"
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, h - 85,  f"Réf : {ref}")
    c.drawCentredString(w / 2, h - 98,  f"Délivré le : {format_date(date_delivrance)}")

    y = h - 145
    c.setFillColor(black); c.setFont("Helvetica", 11)
    c.drawString(50, y,      "L'INSEE certifie que l'établissement ci-dessous est inscrit")
    c.drawString(50, y - 18, "au répertoire national des entreprises et des établissements (SIRENE).")

    siren, nic = siret_display[:9], siret_display[9:]
    y -= 55
    for label, value in [
        ("Dénomination", company["nom"]), ("SIREN", siren), ("NIC", nic),
        ("SIRET", siret_display), ("Adresse", company["adresse"]),
        ("Activité principale (APE)", company["activite"]),
        ("Catégorie juridique", random.choice(["5710 - SAS", "5720 - SARL", "5499 - SA", "5498 - EURL"])),
        ("Date de création", format_date(random_date(2005, 2018))),
        ("Statut", "Actif"),
    ]:
        c.setFont("Helvetica-Bold", 11); c.drawString(50,  y, f"{label} :")
        c.setFont("Helvetica", 11);      c.drawString(250, y, str(value))
        y -= 25

    y -= 25
    c.setStrokeColor(color_insee); c.setFillColor(HexColor("#e8f0fe"))
    c.roundRect(50, y - 25, w - 100, 40, 5, fill=1, stroke=1)
    c.setFillColor(color_insee); c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(w / 2, y - 12, "ÉTABLISSEMENT ACTIF AU RÉPERTOIRE SIRENE")

    c.setFont("Helvetica", 7); c.setFillColor(HexColor("#888888"))
    c.drawCentredString(w / 2, 30, f"INSEE — Attestation SIRENE — {ref}")
    c.drawCentredString(w / 2, 18, "Document généré automatiquement — Hackathon 2026")
    c.save()

    return buf.getvalue()


# ─────────────────────────────────────────────────────────────
#  Effets image — travaillent sur bytes PDF → bytes JPG
# ─────────────────────────────────────────────────────────────

def _pdf_bytes_to_cv2(pdf_bytes: bytes) -> np.ndarray:
    """Ouvre un PDF depuis des bytes et retourne une image BGR numpy."""
    doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    mat  = fitz.Matrix(200 / 72, 200 / 72)
    pix  = page.get_pixmap(matrix=mat)
    doc.close()
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n).copy()
    return cv2.cvtColor(img, cv2.COLOR_RGBA2BGR if pix.n == 4 else cv2.COLOR_RGB2BGR)


def _cv2_to_jpg_bytes(img: np.ndarray, quality: int = 85) -> bytes:
    """Encode une image numpy en bytes JPEG."""
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Échec de l'encodage JPEG")
    return buf.tobytes()


def apply_dirty_scan(pdf_bytes: bytes) -> bytes:
    img = _pdf_bytes_to_cv2(pdf_bytes)
    h_img, w_img = img.shape[:2]
    M = cv2.getRotationMatrix2D((w_img // 2, h_img // 2), random.uniform(-6, 6), 1.0)
    img = cv2.warpAffine(img, M, (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)
    noise = np.random.normal(0, 18, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (5, 5), 1.2)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int16)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] + random.randint(-25, 5), 0, 255)
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return _cv2_to_jpg_bytes(img, quality=85)


def apply_smartphone_scan(pdf_bytes: bytes) -> bytes:
    img = _pdf_bytes_to_cv2(pdf_bytes)
    h_img, w_img = img.shape[:2]
    mx, my = int(w_img * 0.06), int(h_img * 0.06)
    src = np.float32([[0, 0], [w_img, 0], [w_img, h_img], [0, h_img]])
    dst = np.float32([
        [random.randint(mx // 2, mx),     random.randint(my // 2, my)],
        [w_img - random.randint(mx // 2, mx), random.randint(0, my // 2)],
        [w_img - random.randint(0, mx // 2),  h_img - random.randint(my // 2, my)],
        [random.randint(0, mx // 2),          h_img - random.randint(0, my // 2)],
    ])
    img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst),
                               (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)
    M = cv2.getRotationMatrix2D((w_img // 2, h_img // 2), random.uniform(-4, 4), 1.0)
    img = cv2.warpAffine(img, M, (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)
    direction = random.choice(["left", "right", "top", "bottom"])
    if direction == "left":
        g = np.tile(np.linspace(0.65, 1.0, w_img), (h_img, 1))
    elif direction == "right":
        g = np.tile(np.linspace(1.0, 0.65, w_img), (h_img, 1))
    elif direction == "top":
        g = np.tile(np.linspace(0.65, 1.0, h_img), (w_img, 1)).T
    else:
        g = np.tile(np.linspace(1.0, 0.65, h_img), (w_img, 1)).T
    img = (img.astype(np.float32) * g[:, :, np.newaxis].astype(np.float32)).clip(0, 255).astype(np.uint8)
    noise = np.random.normal(0, 12, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0.7)
    return _cv2_to_jpg_bytes(img, quality=78)


def apply_heavy_degradation(pdf_bytes: bytes) -> bytes:
    img = _pdf_bytes_to_cv2(pdf_bytes)
    h_img, w_img = img.shape[:2]
    scale = random.uniform(0.15, 0.25)
    small = cv2.resize(img, (int(w_img * scale), int(h_img * scale)), interpolation=cv2.INTER_LINEAR)
    img   = cv2.resize(small, (w_img, h_img), interpolation=cv2.INTER_NEAREST)
    M = cv2.getRotationMatrix2D((w_img // 2, h_img // 2), random.uniform(-8, 8), 1.0)
    img = cv2.warpAffine(img, M, (w_img, h_img), borderMode=cv2.BORDER_REPLICATE)
    noise = np.random.normal(0, 30, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = cv2.GaussianBlur(img, (7, 7), 2.5)
    for _ in range(random.randint(3, 8)):
        color = random.randint(100, 180)
        cv2.circle(img, (random.randint(0, w_img), random.randint(0, h_img)),
                   random.randint(10, 50), (color, color, color), -1)
    img = cv2.convertScaleAbs(img, alpha=random.uniform(0.5, 0.7), beta=random.randint(20, 50))
    return _cv2_to_jpg_bytes(img, quality=45)


def apply_partial_occlusion(pdf_bytes: bytes, zones_to_hide: list) -> tuple[bytes, list]:
    """Masque des zones sur un PDF en mémoire. Retourne (bytes, champs_masqués)."""
    doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[0]
    pw, ph = page.rect.width, page.rect.height

    zone_defs = {
        "siret":       fitz.Rect(pw * 0.5, 0,        pw,        ph * 0.12),
        "total":       fitz.Rect(pw * 0.4, ph * 0.55, pw * 0.95, ph * 0.75),
        "header_left": fitz.Rect(0,        0,         pw * 0.4,  ph * 0.12),
        "client":      fitz.Rect(pw * 0.5, ph * 0.1,  pw,        ph * 0.22),
        "footer":      fitz.Rect(0,        ph * 0.92, pw,        ph),
    }
    hidden = []
    for zone_name in zones_to_hide:
        if zone_name in zone_defs:
            page.draw_rect(zone_defs[zone_name], color=(1, 1, 1), fill=(1, 1, 1))
            hidden.append(zone_name)

    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue(), hidden


# ─────────────────────────────────────────────────────────────
#  Upload helper
# ─────────────────────────────────────────────────────────────

def upload(client: DataLakeClient, object_name: str, data: bytes, content_type: str):
    """Upload bytes directement dans la Raw zone."""
    stream = io.BytesIO(data)
    client.client.put_object(
        "raw-documents",
        object_name,
        stream,
        length=len(data),
        content_type=content_type,
    )
    print(f"  [RAW ✓] {object_name}")


# ─────────────────────────────────────────────────────────────
#  Scénarios
# ─────────────────────────────────────────────────────────────

def generate_scn1_perfect(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()
    while valideur == emetteur:
        valideur = pick_team()

    doc_type = random.choice(["facture", "facture", "devis"])
    date     = random_date()
    items    = generate_line_items()

    if doc_type == "facture":
        num = gen_invoice_number()
        filename = f"SCN1_facture_{index:03d}.pdf"
        pdf_bytes, total_ht, tva, ttc, ttc_disp = build_invoice_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, valideur, company["siret"])
        upload(client, f"{prefix}{filename}", pdf_bytes, "application/pdf")
        ground_truth.append({
            "filename": filename, "scenario": "SCN-1", "doc_type": "facture",
            "emetteur": emetteur, "valideur": valideur,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": company["siret"], "client": client_c["nom"],
            "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp,
            "is_valid": True, "error_type": None, "linked_files": [],
        })
    else:
        num = gen_devis_number()
        filename = f"SCN1_devis_{index:03d}.pdf"
        pdf_bytes, total_ht, tva, ttc = build_devis_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, company["siret"])
        upload(client, f"{prefix}{filename}", pdf_bytes, "application/pdf")
        ground_truth.append({
            "filename": filename, "scenario": "SCN-1", "doc_type": "devis",
            "emetteur": emetteur, "valideur": None,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": company["siret"], "client": client_c["nom"],
            "total_ht": total_ht, "tva": tva, "total_ttc": ttc,
            "is_valid": True, "error_type": None, "linked_files": [],
        })
    counters["SCN-1"] += 1


def _build_any_doc(company, client_c, emetteur, valideur, doc_type, temp=False):
    """Construit n'importe quel type de document et retourne (bytes, gt_extra_fields)."""
    extra = {}
    if doc_type == "facture":
        items = generate_line_items()
        num   = gen_invoice_number()
        date  = random_date()
        pdf, total_ht, tva, ttc, ttc_disp = build_invoice_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, valideur, company["siret"])
        extra = {"valideur": valideur, "client": client_c["nom"],
                 "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp}
    elif doc_type == "devis":
        items = generate_line_items()
        num   = gen_devis_number()
        date  = random_date()
        pdf, total_ht, tva, ttc = build_devis_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, company["siret"])
        extra = {"valideur": None, "client": client_c["nom"],
                 "total_ht": total_ht, "tva": tva, "total_ttc": ttc}
    elif doc_type == "urssaf":
        emission    = random_date(2025, 2026)
        expiration  = emission + timedelta(days=random.randint(180, 365))
        pdf = build_urssaf_pdf(company, emission, expiration, emetteur, company["siret"])
        extra = {"valideur": None, "client": None, "total_ht": None, "tva": None,
                 "total_ttc": None, "date_emission": format_date(emission),
                 "date_expiration": format_date(expiration)}
    elif doc_type == "kbis":
        dirigeant   = pick_team()
        date_immat  = random_date(2010, 2020)
        capital     = random.choice([1000, 5000, 10000, 50000, 100000])
        pdf = build_kbis_pdf(company, dirigeant, company["siret"], date_immat, capital)
        extra = {"valideur": None, "client": None, "total_ht": None, "tva": None,
                 "total_ttc": None, "dirigeant": dirigeant,
                 "date_immatriculation": format_date(date_immat), "capital_social": capital}
    elif doc_type == "attestation_siret":
        date_deliv = random_date(2025, 2026)
        pdf = build_siret_pdf(company, company["siret"], date_deliv)
        extra = {"valideur": None, "client": None, "total_ht": None, "tva": None,
                 "total_ttc": None, "date_delivrance": format_date(date_deliv)}
    return pdf, extra


def generate_scn2_dirty(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()
    while valideur == emetteur:
        valideur = pick_team()

    doc_type  = random.choice(["facture", "facture", "devis", "urssaf", "kbis", "attestation_siret"])
    pdf_bytes, extra = _build_any_doc(company, client_c, emetteur, valideur, doc_type)
    jpg_bytes = apply_dirty_scan(pdf_bytes)

    filename = f"SCN2_scan_{index:03d}.jpg"
    upload(client, f"{prefix}{filename}", jpg_bytes, "image/jpeg")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-2", "doc_type": doc_type,
        "emetteur": emetteur, "entreprise": company["nom"],
        "siret_attendu": company["siret"], "siret_affiche": company["siret"],
        "is_valid": True, "error_type": "dirty_scan", "degradation": "dirty_scan",
        "linked_files": [], **extra,
    })
    counters["SCN-2"] += 1


def generate_scn3_siret_mismatch(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur    = pick_team()
    valideur    = pick_team()
    items       = generate_line_items()
    fake_siret  = random_siret()
    num         = gen_invoice_number()
    date        = random_date()

    pdf_bytes, total_ht, tva, ttc, ttc_disp = build_invoice_pdf(
        company, client_c, items, num, format_date(date),
        emetteur, valideur, fake_siret)

    filename = f"SCN3_siret_mismatch_{index:03d}.pdf"
    upload(client, f"{prefix}{filename}", pdf_bytes, "application/pdf")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-3", "doc_type": "facture",
        "emetteur": emetteur, "valideur": valideur,
        "entreprise": company["nom"], "siret_attendu": company["siret"],
        "siret_affiche": fake_siret, "client": client_c["nom"],
        "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp,
        "is_valid": False, "error_type": "siret_mismatch", "linked_files": [],
    })
    counters["SCN-3"] += 1


def generate_scn4_urssaf_expired(client, prefix, index):
    company  = pick_company()
    emetteur = pick_team()
    emission = random_date(2023, 2024)
    expiration = emission + timedelta(days=random.randint(180, 365))
    if expiration >= datetime(2026, 1, 1):
        expiration = datetime(2025, random.randint(1, 12), random.randint(1, 28))

    pdf_bytes = build_urssaf_pdf(company, emission, expiration, emetteur, company["siret"])
    filename  = f"SCN4_urssaf_expired_{index:03d}.pdf"
    upload(client, f"{prefix}{filename}", pdf_bytes, "application/pdf")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-4", "doc_type": "urssaf",
        "emetteur": emetteur, "valideur": None,
        "entreprise": company["nom"], "siret_attendu": company["siret"],
        "siret_affiche": company["siret"], "client": None,
        "date_emission": format_date(emission), "date_expiration": format_date(expiration),
        "total_ht": None, "tva": None, "total_ttc": None,
        "is_valid": False, "error_type": "urssaf_expired", "linked_files": [],
    })
    counters["SCN-4"] += 1


def generate_scn5_vat_error(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()
    items    = generate_line_items()
    num      = gen_invoice_number()
    date     = random_date()

    pdf_bytes, total_ht, tva, ttc_correct, ttc_displayed = build_invoice_pdf(
        company, client_c, items, num, format_date(date),
        emetteur, valideur, company["siret"], force_vat_error=True)

    filename = f"SCN5_vat_error_{index:03d}.pdf"
    upload(client, f"{prefix}{filename}", pdf_bytes, "application/pdf")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-5", "doc_type": "facture",
        "emetteur": emetteur, "valideur": valideur,
        "entreprise": company["nom"], "siret_attendu": company["siret"],
        "siret_affiche": company["siret"], "client": client_c["nom"],
        "total_ht": total_ht, "tva": tva, "total_ttc": ttc_displayed,
        "total_ttc_correct": ttc_correct,
        "is_valid": False, "error_type": "vat_calculation_error", "linked_files": [],
    })
    counters["SCN-5"] += 1


def generate_scn6_smartphone(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()
    while valideur == emetteur:
        valideur = pick_team()

    doc_type  = random.choice(["facture", "devis", "urssaf", "kbis", "attestation_siret"])
    pdf_bytes, extra = _build_any_doc(company, client_c, emetteur, valideur, doc_type)
    jpg_bytes = apply_smartphone_scan(pdf_bytes)

    filename = f"SCN6_smartphone_{index:03d}.jpg"
    upload(client, f"{prefix}{filename}", jpg_bytes, "image/jpeg")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-6", "doc_type": doc_type,
        "emetteur": emetteur, "entreprise": company["nom"],
        "siret_attendu": company["siret"], "siret_affiche": company["siret"],
        "is_valid": True, "error_type": "smartphone_photo", "degradation": "smartphone",
        "linked_files": [], **extra,
    })
    counters["SCN-6"] += 1


def generate_scn7_combined(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()
    items    = generate_line_items()
    num      = gen_invoice_number()
    date     = random_date()

    error_choice = random.choice(["siret_mismatch", "vat_error"])
    if error_choice == "siret_mismatch":
        siret_display = random_siret()
        force_vat     = False
    else:
        siret_display = company["siret"]
        force_vat     = True

    pdf_bytes, total_ht, tva, ttc_correct, ttc_displayed = build_invoice_pdf(
        company, client_c, items, num, format_date(date),
        emetteur, valideur, siret_display, force_vat_error=force_vat)

    degrad_choice = random.choice(["dirty_scan", "smartphone"])
    jpg_bytes = (apply_dirty_scan(pdf_bytes)
                 if degrad_choice == "dirty_scan"
                 else apply_smartphone_scan(pdf_bytes))

    filename = f"SCN7_combined_{index:03d}.jpg"
    upload(client, f"{prefix}{filename}", jpg_bytes, "image/jpeg")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-7", "doc_type": "facture",
        "emetteur": emetteur, "valideur": valideur,
        "entreprise": company["nom"], "siret_attendu": company["siret"],
        "siret_affiche": siret_display, "client": client_c["nom"],
        "total_ht": total_ht, "tva": tva, "total_ttc": ttc_displayed,
        "total_ttc_correct": ttc_correct if force_vat else None,
        "is_valid": False,
        "error_type": f"combined_{error_choice}_{degrad_choice}",
        "degradation": degrad_choice, "linked_files": [],
    })
    counters["SCN-7"] += 1


def generate_scn8_consistency(client, prefix):
    companies_pool = random.sample(COMPANIES, min(5, len(COMPANIES)))

    for i, company in enumerate(companies_pool, 1):
        is_cas_b  = i > 3
        cas_label = "B" if is_cas_b else "A"

        client_c = pick_company()
        while client_c["siret"] == company["siret"]:
            client_c = pick_company()
        emetteur  = pick_team()
        valideur  = pick_team()
        while valideur == emetteur:
            valideur = pick_team()
        dirigeant = pick_team()

        facture_siret = random_siret() if is_cas_b else company["siret"]

        f_facture = f"SCN8_pack{i}_cas{cas_label}_facture.pdf"
        f_kbis    = f"SCN8_pack{i}_cas{cas_label}_kbis.pdf"
        f_urssaf  = f"SCN8_pack{i}_cas{cas_label}_urssaf.pdf"
        f_rib     = f"SCN8_pack{i}_cas{cas_label}_rib.pdf"
        f_siret   = f"SCN8_pack{i}_cas{cas_label}_siret.pdf"
        linked    = [f_facture, f_kbis, f_urssaf, f_rib, f_siret]

        # Facture
        items = generate_line_items()
        num   = gen_invoice_number()
        date  = random_date()
        pdf, total_ht, tva, ttc, ttc_disp = build_invoice_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, valideur, facture_siret)
        upload(client, f"{prefix}{f_facture}", pdf, "application/pdf")
        ground_truth.append({
            "filename": f_facture, "scenario": "SCN-8", "doc_type": "facture",
            "emetteur": emetteur, "valideur": valideur,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": facture_siret, "client": client_c["nom"],
            "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp,
            "is_valid": not is_cas_b,
            "error_type": "siret_cross_mismatch" if is_cas_b else None,
            "linked_files": [f for f in linked if f != f_facture],
        })

        # Kbis
        date_immat = random_date(2010, 2020)
        capital    = random.choice([1000, 5000, 10000, 50000, 100000, 500000])
        pdf = build_kbis_pdf(company, dirigeant, company["siret"], date_immat, capital)
        upload(client, f"{prefix}{f_kbis}", pdf, "application/pdf")
        ground_truth.append({
            "filename": f_kbis, "scenario": "SCN-8", "doc_type": "kbis",
            "emetteur": None, "valideur": None,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": company["siret"], "dirigeant": dirigeant,
            "date_immatriculation": format_date(date_immat), "capital_social": capital,
            "client": None, "total_ht": None, "tva": None, "total_ttc": None,
            "is_valid": True, "error_type": None,
            "linked_files": [f for f in linked if f != f_kbis],
        })

        # URSSAF
        emission   = random_date(2025, 2026)
        expiration = emission + timedelta(days=random.randint(180, 365))
        pdf = build_urssaf_pdf(company, emission, expiration, emetteur, company["siret"])
        upload(client, f"{prefix}{f_urssaf}", pdf, "application/pdf")
        ground_truth.append({
            "filename": f_urssaf, "scenario": "SCN-8", "doc_type": "urssaf",
            "emetteur": emetteur, "valideur": None,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": company["siret"], "client": None,
            "date_emission": format_date(emission), "date_expiration": format_date(expiration),
            "total_ht": None, "tva": None, "total_ttc": None,
            "is_valid": True, "error_type": None,
            "linked_files": [f for f in linked if f != f_urssaf],
        })

        # RIB
        iban = gen_iban()
        bic  = gen_bic()
        pdf  = build_rib_pdf(company, company["siret"], iban, bic)
        upload(client, f"{prefix}{f_rib}", pdf, "application/pdf")
        ground_truth.append({
            "filename": f_rib, "scenario": "SCN-8", "doc_type": "rib",
            "emetteur": None, "valideur": None,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": company["siret"], "iban": iban, "bic": bic,
            "client": None, "total_ht": None, "tva": None, "total_ttc": None,
            "is_valid": True, "error_type": None,
            "linked_files": [f for f in linked if f != f_rib],
        })

        # Attestation SIRET
        date_siret = random_date(2025, 2026)
        pdf = build_siret_pdf(company, company["siret"], date_siret)
        upload(client, f"{prefix}{f_siret}", pdf, "application/pdf")
        ground_truth.append({
            "filename": f_siret, "scenario": "SCN-8", "doc_type": "attestation_siret",
            "emetteur": None, "valideur": None,
            "entreprise": company["nom"], "siret_attendu": company["siret"],
            "siret_affiche": company["siret"], "client": None,
            "date_delivrance": format_date(date_siret),
            "total_ht": None, "tva": None, "total_ttc": None,
            "is_valid": True, "error_type": None,
            "linked_files": [f for f in linked if f != f_siret],
        })

        counters["SCN-8"] += 5


def generate_scn9_pixelized(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()

    doc_type  = random.choice(["facture", "devis", "urssaf", "kbis"])
    pdf_bytes, extra = _build_any_doc(company, client_c, emetteur, valideur, doc_type)
    jpg_bytes = apply_heavy_degradation(pdf_bytes)

    filename = f"SCN9_pixelized_{index:03d}.jpg"
    upload(client, f"{prefix}{filename}", jpg_bytes, "image/jpeg")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-9", "doc_type": doc_type,
        "emetteur": emetteur, "entreprise": company["nom"],
        "siret_attendu": company["siret"], "siret_affiche": company["siret"],
        "is_valid": True, "error_type": "heavy_degradation", "degradation": "pixelized",
        "linked_files": [], **extra,
    })
    counters["SCN-9"] += 1


def generate_scn10_partial(client, prefix, index):
    company  = pick_company()
    client_c = pick_company()
    while client_c["siret"] == company["siret"]:
        client_c = pick_company()
    emetteur = pick_team()
    valideur = pick_team()

    doc_type = random.choice(["facture", "devis"])
    items    = generate_line_items()
    date     = random_date()

    if doc_type == "facture":
        num = gen_invoice_number()
        pdf_bytes, total_ht, tva, ttc, ttc_disp = build_invoice_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, valideur, company["siret"])
    else:
        num = gen_devis_number()
        pdf_bytes, total_ht, tva, ttc = build_devis_pdf(
            company, client_c, items, num, format_date(date),
            emetteur, company["siret"])
        ttc_disp = ttc

    zones  = random.sample(["siret", "total", "client", "footer"], random.randint(1, 2))
    pdf_bytes, hidden = apply_partial_occlusion(pdf_bytes, zones)

    filename = f"SCN10_partial_{index:03d}.pdf"
    upload(client, f"{prefix}{filename}", pdf_bytes, "application/pdf")
    ground_truth.append({
        "filename": filename, "scenario": "SCN-10", "doc_type": doc_type,
        "emetteur": emetteur, "valideur": valideur if doc_type == "facture" else None,
        "entreprise": company["nom"], "siret_attendu": company["siret"],
        "siret_affiche": company["siret"], "client": client_c["nom"],
        "total_ht": total_ht, "tva": tva, "total_ttc": ttc_disp,
        "is_valid": True, "error_type": "partial_occlusion",
        "hidden_fields": hidden, "linked_files": [],
    })
    counters["SCN-10"] += 1


# ─────────────────────────────────────────────────────────────
#  Post-traitement
# ─────────────────────────────────────────────────────────────

def assign_train_test_split(gt_list, test_ratio=0.2):
    packs, standalone = {}, []
    for entry in gt_list:
        if entry["scenario"] == "SCN-8":
            pack_id = entry["filename"].split("_")[1]
            packs.setdefault(pack_id, []).append(entry)
        else:
            standalone.append(entry)

    random.shuffle(standalone)
    split_idx = int(len(standalone) * (1 - test_ratio))
    for e in standalone[:split_idx]:
        e["split"] = "train"
    for e in standalone[split_idx:]:
        e["split"] = "test"

    pack_keys = list(packs.keys())
    random.shuffle(pack_keys)
    psplit = max(1, int(len(pack_keys) * (1 - test_ratio)))
    for pk in pack_keys[:psplit]:
        for e in packs[pk]: e["split"] = "train"
    for pk in pack_keys[psplit:]:
        for e in packs[pk]: e["split"] = "test"


def add_classification_metadata(gt_list):
    category_map = {
        "facture": "FACTURE", "devis": "DEVIS",
        "urssaf": "ATTESTATION_URSSAF", "kbis": "EXTRAIT_KBIS",
        "rib": "RIB", "attestation_siret": "ATTESTATION_SIRET",
    }
    for e in gt_list:
        e["category"] = category_map.get(e["doc_type"], "INCONNU")
        e["format"]   = "image" if e["filename"].endswith(".jpg") else "pdf"
        degrad = e.get("degradation", "")
        err    = str(e.get("error_type", ""))
        if degrad == "pixelized":
            e["difficulty"] = "hard"
        elif degrad in ("dirty_scan", "smartphone") or e.get("error_type") == "partial_occlusion":
            e["difficulty"] = "medium"
        elif "combined" in err:
            e["difficulty"] = "hard"
        else:
            e["difficulty"] = "easy"


# ─────────────────────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Génère le dataset synthétique et l'uploade directement dans MinIO.")
    parser.add_argument("--prefix", default=DEFAULT_PREFIX,
                        help=f"Préfixe des objets dans la Raw zone (défaut : {DEFAULT_PREFIX})")
    args = parser.parse_args()

    prefix = args.prefix if args.prefix.endswith("/") else args.prefix + "/"

    print("=" * 60)
    print("  GÉNÉRATION DU DATASET — Hackathon 2026")
    print(f"  Préfixe MinIO : {prefix}")
    print("=" * 60)

    dl = DataLakeClient()

    print("\n[SCN-1] 30 documents conformes...")
    for i in range(1, 31):
        generate_scn1_perfect(dl, prefix, i)
    print(f"  → {counters['SCN-1']} documents")

    print("[SCN-2] 25 scans dégradés...")
    for i in range(1, 26):
        generate_scn2_dirty(dl, prefix, i)
    print(f"  → {counters['SCN-2']} documents")

    print("[SCN-3] 15 SIRET mismatch...")
    for i in range(1, 16):
        generate_scn3_siret_mismatch(dl, prefix, i)
    print(f"  → {counters['SCN-3']} documents")

    print("[SCN-4] 15 URSSAF expirées...")
    for i in range(1, 16):
        generate_scn4_urssaf_expired(dl, prefix, i)
    print(f"  → {counters['SCN-4']} documents")

    print("[SCN-5] 10 erreurs TVA...")
    for i in range(1, 11):
        generate_scn5_vat_error(dl, prefix, i)
    print(f"  → {counters['SCN-5']} documents")

    print("[SCN-6] 15 photos smartphone...")
    for i in range(1, 16):
        generate_scn6_smartphone(dl, prefix, i)
    print(f"  → {counters['SCN-6']} documents")

    print("[SCN-7] 15 combinés (dégradation + erreur)...")
    for i in range(1, 16):
        generate_scn7_combined(dl, prefix, i)
    print(f"  → {counters['SCN-7']} documents")

    print("[SCN-8] 5 packs cohérence croisée...")
    generate_scn8_consistency(dl, prefix)
    print(f"  → {counters['SCN-8']} documents")

    print("[SCN-9] 10 documents très dégradés...")
    for i in range(1, 11):
        generate_scn9_pixelized(dl, prefix, i)
    print(f"  → {counters['SCN-9']} documents")

    print("[SCN-10] 10 documents champs manquants...")
    for i in range(1, 11):
        generate_scn10_partial(dl, prefix, i)
    print(f"  → {counters['SCN-10']} documents")

    # Post-traitement
    print("\n[POST] Métadonnées & split train/test...")
    add_classification_metadata(ground_truth)
    assign_train_test_split(ground_truth, test_ratio=0.2)

    # Upload des 3 fichiers ground truth directement dans MinIO
    for gt_name, gt_data in [
        ("ground_truth.json",       ground_truth),
        ("ground_truth_train.json", [e for e in ground_truth if e.get("split") == "train"]),
        ("ground_truth_test.json",  [e for e in ground_truth if e.get("split") == "test"]),
    ]:
        payload = json.dumps(gt_data, ensure_ascii=False, indent=2).encode("utf-8")
        dl.client.put_object(
            "raw-documents",
            f"{prefix}metadata/{gt_name}",
            io.BytesIO(payload),
            length=len(payload),
            content_type="application/json",
        )
        print(f"  [META ✓] {prefix}metadata/{gt_name}")

    # Résumé
    total = sum(counters.values())
    train_n = sum(1 for e in ground_truth if e.get("split") == "train")
    test_n  = sum(1 for e in ground_truth if e.get("split") == "test")

    print("\n" + "=" * 60)
    print("  RÉSUMÉ")
    print("=" * 60)
    for scn, count in sorted(counters.items()):
        print(f"  {scn} : {count} documents")
    print(f"  {'─' * 30}")
    print(f"  TOTAL : {total} documents  |  Train : {train_n}  |  Test : {test_n}")

    from collections import Counter
    print("\n  Par type :")
    for dtype, cnt in sorted(Counter(e["doc_type"] for e in ground_truth).items()):
        print(f"    {dtype}: {cnt}")
    print("\n  Par difficulté :")
    for diff, cnt in sorted(Counter(e.get("difficulty") for e in ground_truth).items()):
        print(f"    {diff}: {cnt}")

    stats = dl.get_stats()
    raw   = stats.get("raw", {})
    print(f"\n  Raw zone MinIO : {raw.get('nb_objects')} objets / {raw.get('total_size_kb')} Ko")
    print("=" * 60)


if __name__ == "__main__":
    main()
