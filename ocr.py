import os
import cv2
import pytesseract
from pdf2image import convert_from_path

pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'


RAW_FOLDER = "data/raw"
CLEAN_FOLDER = "data/clean"


# -------------------------
# Prétraitement image
# -------------------------
def preprocess_image(image):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # réduction bruit
    blur = cv2.GaussianBlur(gray, (5,5), 0)

    # seuillage
    thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)[1]

    return thresh


# -------------------------
# OCR sur image
# ------------------------
def extract_text_from_image(image):

    processed = preprocess_image(image)

    text = pytesseract.image_to_string(
        processed,
        lang="fra"
    )

    return text


# -------------------------
# OCR sur PDF
# -------------------------
def extract_text_from_pdf(pdf_path):

    pages = convert_from_path(pdf_path)

    full_text = ""

    for page in pages:

        image = cv2.cvtColor(
            cv2.imread(page.filename),
            cv2.COLOR_BGR2RGB
        )

        text = extract_text_from_image(image)

        full_text += text + "\n"

    return full_text


# -------------------------
# Sauvegarde texte OCR
# -------------------------
def save_text(text, filename):

    os.makedirs(CLEAN_FOLDER, exist_ok=True)

    filepath = os.path.join(CLEAN_FOLDER, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)


# -------------------------
# Pipeline OCR
# -------------------------
def process_documents():

    files = os.listdir(RAW_FOLDER)

    for file in files:

        path = os.path.join(RAW_FOLDER, file)

        print(f"Processing : {file}")

        if file.lower().endswith(".pdf"):

            text = extract_text_from_pdf(path)

        else:

            image = cv2.imread(path)

            text = extract_text_from_image(image)

        output_name = file.split(".")[0] + ".txt"

        save_text(text, output_name)

        print("OCR terminé\n")


if __name__ == "__main__":

    process_documents()