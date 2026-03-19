from pdf2image import convert_from_path
from PIL import Image
import os
import json


PDF_SOURCE_DIR = "./output/raw_zone"
OUTPUT_DIR = "./donut_dataset"
GROUND_TRUTH_PATH = "./output/ground_truth.json"
POPPLER_PATH = "C:/poppler/poppler-25.12.0/Library/bin"


def pdf_to_jpg(pdf_path, output_folder):
    """Converts the first page of a PDF to a high-quality JPEG."""
    images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    filename = os.path.basename(pdf_path).rsplit('.', 1)[0] + ".jpg"
    save_path = os.path.join(output_folder, filename)
    images[0].save(save_path, "JPEG")
    return filename

def process_existing_image(image_path, output_folder):
    """Standardizes an existing image to RGB JPEG format."""
    filename = os.path.basename(image_path).rsplit('.', 1)[0] + ".jpg"
    save_path = os.path.join(output_folder, filename)
    with Image.open(image_path) as img:
        rgb_img = img.convert("RGB")
        rgb_img.save(save_path, "JPEG")
    return filename

def create_metadata_line(image_filename, original_json):
    """Formats the JSON data into the 'gt_parse' string for Donut"""
    extract_fields = {
        "emetteur": original_json.get("emetteur"),
        "valideur": original_json.get("valideur"),
        "entreprise": original_json.get("entreprise"),
        "siret": original_json.get("siret_affiche"),
        "iban": original_json.get("iban"),
        "bic": original_json.get("bic"),
        "client": original_json.get("client"),
        "dirigeant": original_json.get("dirigeant"),
        "capital_social": original_json.get("capital_social"),
        "date_delivrance": original_json.get("date_delivrance"),
        "date_immatriculation": original_json.get("date_immatriculation"),
        "date_emission": original_json.get("date_emission"),
        "date_expiration": original_json.get("date_expiration"),
        "total_ht": original_json.get("total_ht"),
        "tva": original_json.get("tva"),
        "total_ttc": original_json.get("total_ttc")
    }
    ground_truth = {"gt_parse": extract_fields}
    line = {
        "file_name": image_filename,
        "ground_truth": json.dumps(ground_truth, ensure_ascii=False)
    }
    return json.dumps(line, ensure_ascii=False)

def main():
    if not os.path.exists(GROUND_TRUTH_PATH):
        print(f"Error: {GROUND_TRUTH_PATH} not found.")
        return

    with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
        dataset_entries = json.load(f)

    for entry in dataset_entries:
        split = entry.get("split", "train")
        file_format = entry.get("format", "pdf").lower()
        target_folder = os.path.join(OUTPUT_DIR, split)
        os.makedirs(target_folder, exist_ok=True)
        source_path = os.path.join(PDF_SOURCE_DIR, entry["filename"])
        if not os.path.exists(source_path):
            print(f"Skipping: {source_path} does not exist.")
            continue

        try:
            if file_format == "pdf":
                jpg_filename = pdf_to_jpg(source_path, target_folder)
            else:
                jpg_filename = process_existing_image(source_path, target_folder)
            
            metadata_line = create_metadata_line(jpg_filename, entry)
            jsonl_path = os.path.join(target_folder, "metadata.jsonl")
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(metadata_line + "\n")
                
            print(f"Processed: {jpg_filename} ({file_format}) -> {split}")
            
        except Exception as e:
            print(f"Error processing {entry['filename']}: {e}")

if __name__ == "__main__":
    main()