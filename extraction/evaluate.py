import json
import os
from collections import defaultdict
from pathlib import Path
from PIL import Image

from extraction.extract import DocumentExtractor

MODEL_PATH   = "./extraction/model"
DATASET_PATH = "./donut_dataset"

FIELD_ORDER = [
    "emetteur", "valideur", "entreprise", "siret", "iban", "bic",
    "client", "dirigeant", "capital_social", "date_delivrance",
    "date_immatriculation", "date_emission", "date_expiration",
    "total_ht", "tva", "total_ttc",
]

def normalize(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()

def token_f1(pred: str, gold: str) -> float:
    pred_tokens = pred.split()
    gold_tokens = gold.split()
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = set(pred_tokens) & set(gold_tokens)
    if not common:
        return 0.0
    precision = sum(pred_tokens.count(t) for t in common) / len(pred_tokens)
    recall    = sum(gold_tokens.count(t) for t in common) / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def load_samples(split: str) -> list[dict]:
    metadata_path = os.path.join(DATASET_PATH, split, "metadata.jsonl")
    samples = []
    with open(metadata_path, "r", encoding="utf-8") as f:
        for line in f:
            entry    = json.loads(line.strip())
            gt_dict  = json.loads(entry["ground_truth"])
            gt_parse = gt_dict.get("gt_parse", gt_dict)
            samples.append({
                "file_name": entry["file_name"],
                "image_path": os.path.join(DATASET_PATH, split, entry["file_name"]),
                "gt": gt_parse,
            })
    return samples

def evaluate_split(split: str, extractor: DocumentExtractor) -> dict:
    samples = load_samples(split)
    print(f"\nEvaluation sur le set '{split}' ({len(samples)} documents)...\n")

    field_exact  = defaultdict(lambda: {"correct": 0, "total": 0})
    field_f1_sum = defaultdict(float)
    field_count  = defaultdict(int)
    doc_exact_all = 0
    results_log   = []

    for sample in samples:
        if not os.path.exists(sample["image_path"]):
            print(f"  WARNING: image introuvable — {sample['image_path']}")
            continue
        image = Image.open(sample["image_path"]).convert("RGB")
        pred = extractor.extract(image)
        
        gt   = sample["gt"]

        doc_all_correct = True
        doc_result = {"file": sample["file_name"], "fields": {}}

        for field in FIELD_ORDER:
            gold_raw = gt.get(field)
            pred_raw = pred.get(field)
            gold = normalize(gold_raw)
            p    = normalize(pred_raw)

            if gold == "" and p == "":
                doc_result["fields"][field] = {"status": "N/A"}
                continue

            exact = int(p == gold)
            f1    = token_f1(p, gold)

            field_exact[field]["correct"] += exact
            field_exact[field]["total"]   += 1
            field_f1_sum[field]           += f1
            field_count[field]            += 1

            if not exact:
                doc_all_correct = False

            doc_result["fields"][field] = {
                "gold":  gold_raw,
                "pred":  pred_raw,
                "exact": bool(exact),
                "f1":    round(f1, 3),
            }

        if doc_all_correct:
            doc_exact_all += 1

        results_log.append(doc_result)
        status = "✓" if doc_all_correct else "✗"
        print(f"  [{status}] {sample['file_name']}")

    total_docs = len(results_log)
    print("\n" + "=" * 65)
    print(f"  {split.upper()} — FIELD-LEVEL RESULTS")
    print("=" * 65)
    print(f"{'Field':<30} {'Exact Match':>12} {'Token F1':>10}")
    print("-" * 65)

    all_exact_scores = []
    all_f1_scores    = []

    for field in FIELD_ORDER:
        total = field_exact[field]["total"]
        if total == 0:
            print(f"  {field:<28} {'N/A':>12} {'N/A':>10}")
            continue
        exact_pct = field_exact[field]["correct"] / total * 100
        avg_f1    = field_f1_sum[field] / field_count[field] * 100
        all_exact_scores.append(exact_pct)
        all_f1_scores.append(avg_f1)
        print(f"  {field:<28} {exact_pct:>10.1f}%  {avg_f1:>8.1f}%")

    print("-" * 65)
    if all_exact_scores:
        macro_exact = sum(all_exact_scores) / len(all_exact_scores)
        macro_f1    = sum(all_f1_scores) / len(all_f1_scores)
        print(f"  {'MACRO AVERAGE':<28} {macro_exact:>10.1f}%  {macro_f1:>8.1f}%")

    print("\n" + "=" * 65)
    if total_docs > 0:
        print(f"  Document-level Exact Match : {doc_exact_all}/{total_docs}  ({doc_exact_all/total_docs*100:.1f}%)")
    print("=" * 65)

    output_path = f"./extraction/evaluation_{split}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results_log, f, indent=2, ensure_ascii=False)
    print(f"\nRésultats détaillés sauvegardés dans {output_path}")

    return results_log


if __name__ == "__main__":
    print("Chargement du modèle...")
    extractor = DocumentExtractor(MODEL_PATH)
    print("Modèle chargé.\n")

    evaluate_split("train", extractor)
    evaluate_split("test", extractor)
