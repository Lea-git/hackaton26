import argparse
import json
from pathlib import Path

from document_validator import DocumentValidator


def evaluate_ml_only(dataset_dir="ml_dataset", labels_file="labels_ml.json", report_path="ml_report.json"):
    dataset_path = Path(dataset_dir)
    labels_path = dataset_path / labels_file

    if not labels_path.exists():
        raise FileNotFoundError(
            f"Labels file not found: {labels_path}. Run mock_generator.py first."
        )

    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if not records:
        raise ValueError("No records found in labels file.")

    validator = DocumentValidator()

    tp = tn = fp = fn = 0

    for row in records:
        file_name = row.get("file")
        y_true = int(row.get("expected_ml_anomaly", 0))

        invoice_path = dataset_path / str(file_name)
        if not invoice_path.exists():
            continue

        invoice = json.loads(invoice_path.read_text(encoding="utf-8"))
        y_pred = 1 if validator._is_ml_anomaly(invoice.get("montant_ttc")) else 0

        if y_true == 1 and y_pred == 1:
            tp += 1
        elif y_true == 0 and y_pred == 0:
            tn += 1
        elif y_true == 0 and y_pred == 1:
            fp += 1
        else:
            fn += 1

    total = tp + tn + fp + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / total if total else 0.0

    print("ML only evaluation")
    print(f"Dataset: {dataset_path}")
    print(f"Samples used: {total}")
    print(f"TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"Precision={precision:.4f}")
    print(f"Recall={recall:.4f}")
    print(f"F1={f1:.4f}")
    print(f"Accuracy={accuracy:.4f}")

    report = {
        "dataset": str(dataset_path),
        "labels_file": str(labels_path),
        "samples_used": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }

    report_file = Path(report_path)
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Report saved: {report_file}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate ML anomaly detection only")
    parser.add_argument("--dataset-dir", default="ml_dataset")
    parser.add_argument("--labels-file", default="labels_ml.json")
    parser.add_argument("--report", default="ml_report.json")
    args = parser.parse_args()

    try:
        evaluate_ml_only(
            dataset_dir=args.dataset_dir,
            labels_file=args.labels_file,
            report_path=args.report,
        )
    except Exception as exc:
        print(f"Evaluation error: {exc}")
