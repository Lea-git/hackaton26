import torch
import json
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel


MODEL_PATH = "./extraction/model"
# IMAGE_PATH = "./donut_dataset/train/SCN1_devis_002.jpg" 
# IMAGE_PATH = "./donut_dataset/test/SCN1_facture_028.jpg" 
# IMAGE_PATH = "./donut_dataset/test/SCN4_urssaf_expired_007.jpg" 
IMAGE_PATH = "./donut_dataset/test/SCN8_pack3_casA_rib.jpg" 

processor = DonutProcessor.from_pretrained(MODEL_PATH)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
model.eval()

image = Image.open(IMAGE_PATH).convert("RGB")

pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)

decoder_input_ids = processor.tokenizer(
    "<s_gt_parse>",
    add_special_tokens=False,
    return_tensors="pt",
).input_ids.to(device)

with torch.no_grad():
    outputs = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=512,
        early_stopping=True,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        use_cache=True,
        num_beams=1,
    )

raw = processor.tokenizer.decode(outputs[0], skip_special_tokens=False)
print("Raw output:", raw)

sequence = raw.replace("<s_gt_parse>", "").replace("</s_gt_parse>", "").strip()

result = processor.token2json(raw)
print("\nExtracted fields:")
print(json.dumps(result, indent=2, ensure_ascii=False))
