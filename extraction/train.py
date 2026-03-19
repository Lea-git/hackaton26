import os
import gc
import json
import torch
from dataclasses import dataclass
from typing import Any
from datasets import load_dataset
from transformers import (
    DonutProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
)

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

DATASET_PATH = "./donut_dataset"
MODEL_ID = "naver-clova-ix/donut-base"
OUTPUT_DIR = "./extraction/model"
MAX_LENGTH = 512
IMAGE_SIZE = [960, 720]  # [height, width]

processor = DonutProcessor.from_pretrained(MODEL_ID)

processor.image_processor.size = {"height": IMAGE_SIZE[0], "width": IMAGE_SIZE[1]}
processor.image_processor.do_align_long_axis = False

new_special_tokens = [
    "<s_gt_parse>", "</s_gt_parse>",
    "<s_emetteur>",            "</s_emetteur>",
    "<s_valideur>",            "</s_valideur>",
    "<s_entreprise>",          "</s_entreprise>",
    "<s_siret>",               "</s_siret>",
    "<s_iban>",                "</s_iban>",
    "<s_bic>",                 "</s_bic>",
    "<s_client>",              "</s_client>",
    "<s_dirigeant>",           "</s_dirigeant>",
    "<s_capital_social>",      "</s_capital_social>",
    "<s_date_delivrance>",     "</s_date_delivrance>",
    "<s_date_immatriculation>","</s_date_immatriculation>",
    "<s_date_emission>",       "</s_date_emission>",
    "<s_date_expiration>",     "</s_date_expiration>",
    "<s_total_ht>",            "</s_total_ht>",
    "<s_tva>",                 "</s_tva>",
    "<s_total_ttc>",           "</s_total_ttc>",
]
processor.tokenizer.add_special_tokens({"additional_special_tokens": new_special_tokens})

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = VisionEncoderDecoderModel.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32
)
model.decoder.resize_token_embeddings(len(processor.tokenizer))
model = model.to(device)
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids("<s_gt_parse>")
model.config.eos_token_id = processor.tokenizer.eos_token_id
model.config.encoder.image_size = IMAGE_SIZE
model.config.tie_word_embeddings = False
model.config.use_cache = False
model.generation_config.max_length = MAX_LENGTH
model.gradient_checkpointing_enable()

FIELD_ORDER = [
    "emetteur", "valideur", "entreprise", "siret", "iban", "bic",
    "client", "dirigeant", "capital_social", "date_delivrance",
    "date_immatriculation", "date_emission", "date_expiration",
    "total_ht", "tva", "total_ttc",
]

def gt_parse_to_token_str(gt_parse):
    inner = ""
    for field in FIELD_ORDER:
        value = gt_parse.get(field)
        value_str = "" if value is None else str(value)
        inner += f"<s_{field}>{value_str}</s_{field}>"
    return f"<s_gt_parse>{inner}</s_gt_parse>"

def preprocess_function(examples):
    pixel_values = processor(
        images=examples["image"],
        return_tensors="pt",
    ).pixel_values  # shape: (batch, C, H, W)

    token_strings = []
    for gt_str in examples["ground_truth"]:
        gt_dict = json.loads(gt_str)
        gt_parse = gt_dict["gt_parse"]
        token_strings.append(gt_parse_to_token_str(gt_parse))

    encoding = processor.tokenizer(
        token_strings,
        add_special_tokens=False,
        max_length=MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    labels = encoding.input_ids
    labels[labels == processor.tokenizer.pad_token_id] = -100

    return {
        "pixel_values": pixel_values,
        "labels": labels,
    }

dataset = load_dataset("imagefolder", data_dir=DATASET_PATH)
print(f"Dataset loaded: {dataset}")

original_columns = dataset["train"].column_names
processed_dataset = dataset.map(
    preprocess_function,
    batched=True,
    remove_columns=original_columns,
    desc="Preprocessing dataset",
)

processed_dataset.set_format(type="torch", columns=["pixel_values", "labels"])


training_args = Seq2SeqTrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    learning_rate=3e-5,
    weight_decay=0.01,
    warmup_steps=100,
    max_steps=2000,
    lr_scheduler_type="cosine",
    save_steps=200,
    logging_steps=20,
    save_total_limit=3,
    load_best_model_at_end=False,
    fp16=True,
    gradient_checkpointing=True,
    predict_with_generate=False,
    eval_strategy="no",
    dataloader_pin_memory=False,
    push_to_hub=False,
    report_to="none",
)


@dataclass
class DonutDataCollator:
    def __call__(self, features: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        pixel_values = torch.stack([f["pixel_values"] for f in features])
        labels = torch.stack([f["labels"] for f in features])
        return {"pixel_values": pixel_values, "labels": labels}

gc.collect()
torch.cuda.empty_cache()

print(f"VRAM used after model load: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
print(f"VRAM free after model load: {(torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_allocated()) / 1024**3:.2f} GB")


trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=processed_dataset["train"],
    # eval_dataset=processed_dataset["test"],
    data_collator=DonutDataCollator(),
)

def main():
    print("=== Starting Donut fine-tuning ===")
    print(f"  Decoder start token id : {model.config.decoder_start_token_id}")
    print(f"  Vocab size              : {len(processor.tokenizer)}")
    print(f"  Train samples          : {len(processed_dataset['train'])}")
    if "test" in processed_dataset:
        print(f"  Test samples           : {len(processed_dataset['test'])}")

    trainer.train()
    
    model.save_pretrained(OUTPUT_DIR)
    processor.save_pretrained(OUTPUT_DIR)
    print(f"\nModel and processor saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()