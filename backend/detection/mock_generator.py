import argparse
import json
import random
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parent


def create_test_json(file_path, siret, vendor, ht, ttc):
    data = {
        "document_type": "facture",
        "siret": siret,
        "vendor_name": vendor,
        "montant_ht": ht,
        "montant_ttc": ttc,
    }
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2, ensure_ascii=False)


def generate_baseline_files():
    create_test_json(BASE_DIR / "facture_ok.json", "44306184100047", "GOOGLE FRANCE", 1000, 1200)
    create_test_json(BASE_DIR / "facture_math_error.json", "44306184100047", "GOOGLE FRANCE", 1000, 5000)
    create_test_json(BASE_DIR / "facture_fake_siret.json", "12345678901234", "GOOGLE FRANCE", 1000, 1200)


def generate_ml_dataset(output_dir="ml_dataset", normal_count=80, anomaly_count=40, difficulty="hard", seed=42):
    rng = random.Random(seed)
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path

    output_path.mkdir(parents=True, exist_ok=True)

    labels: List[Dict[str, object]] = []
    siret = "44306184100047"
    vendor = "GOOGLE FRANCE"

    for index in range(1, normal_count + 1):
        ttc = max(200.0, rng.gauss(1500.0, 220.0))
        ttc = round(ttc, 2)
        ht = round(ttc / 1.20, 2)
        file_name = f"invoice_normal_{index:03d}.json"
        create_test_json(output_path / file_name, siret, vendor, ht, ttc)
        labels.append(
            {
                "file": file_name,
                "expected_ml_anomaly": 0,
                "montant_ttc": ttc,
            }
        )

    anomaly_idx = 1
    if difficulty == "extreme":
        for _ in range(anomaly_count):
            # Extreme mode: anomalies are close to normal values, so detection is harder.
            if rng.random() < 0.5:
                ttc = round(rng.gauss(900.0, 140.0), 2)
            else:
                ttc = round(rng.gauss(2250.0, 220.0), 2)
            ttc = max(150.0, min(3200.0, ttc))
            ht = round(ttc / 1.20, 2)
            file_name = f"invoice_anomaly_{anomaly_idx:03d}.json"
            create_test_json(output_path / file_name, siret, vendor, ht, ttc)
            labels.append(
                {
                    "file": file_name,
                    "expected_ml_anomaly": 1,
                    "montant_ttc": ttc,
                }
            )
            anomaly_idx += 1
    elif difficulty == "hard":
        for _ in range(anomaly_count):
            if rng.random() < 0.5:
                ttc = round(rng.gauss(500.0, 150.0), 2)
            else:
                ttc = round(rng.gauss(3000.0, 400.0), 2)
            ttc = max(100.0, ttc)
            ht = round(ttc / 1.20, 2)
            file_name = f"invoice_anomaly_{anomaly_idx:03d}.json"
            create_test_json(output_path / file_name, siret, vendor, ht, ttc)
            labels.append(
                {
                    "file": file_name,
                    "expected_ml_anomaly": 1,
                    "montant_ttc": ttc,
                }
            )
            anomaly_idx += 1
    else:
        low_anomaly_count = anomaly_count // 2
        high_anomaly_count = anomaly_count - low_anomaly_count

        for _ in range(low_anomaly_count):
            ttc = round(rng.uniform(50.0, 350.0), 2)
            ht = round(ttc / 1.20, 2)
            file_name = f"invoice_anomaly_{anomaly_idx:03d}.json"
            create_test_json(output_path / file_name, siret, vendor, ht, ttc)
            labels.append(
                {
                    "file": file_name,
                    "expected_ml_anomaly": 1,
                    "montant_ttc": ttc,
                }
            )
            anomaly_idx += 1

        for _ in range(high_anomaly_count):
            ttc = round(rng.uniform(3500.0, 9000.0), 2)
            ht = round(ttc / 1.20, 2)
            file_name = f"invoice_anomaly_{anomaly_idx:03d}.json"
            create_test_json(output_path / file_name, siret, vendor, ht, ttc)
            labels.append(
                {
                    "file": file_name,
                    "expected_ml_anomaly": 1,
                    "montant_ttc": ttc,
                }
            )
            anomaly_idx += 1

    labels_payload = {
        "description": "1 means anomaly on montant_ttc, 0 means normal",
        "difficulty": difficulty,
        "normal_count": normal_count,
        "anomaly_count": anomaly_count,
        "records": labels,
    }

    labels_file = output_path / "labels_ml.json"
    with labels_file.open("w", encoding="utf-8") as file_handle:
        json.dump(labels_payload, file_handle, indent=2, ensure_ascii=False)

    return {
        "output_dir": str(output_path),
        "labels_file": str(labels_file),
        "total_files": normal_count + anomaly_count,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate baseline invoices and ML evaluation dataset")
    parser.add_argument("--output-dir", default="ml_dataset")
    parser.add_argument("--normal-count", type=int, default=80)
    parser.add_argument("--anomaly-count", type=int, default=40)
    parser.add_argument("--difficulty", choices=["easy", "hard", "extreme"], default="extreme")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_baseline_files()
    dataset_info = generate_ml_dataset(
        output_dir=args.output_dir,
        normal_count=args.normal_count,
        anomaly_count=args.anomaly_count,
        difficulty=args.difficulty,
        seed=args.seed,
    )
    print(f"Dataset generated ({args.difficulty} difficulty)")
    print(json.dumps(dataset_info, indent=2, ensure_ascii=False))