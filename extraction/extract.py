import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel


FIELD_ORDER = [
    "emetteur", "valideur", "entreprise", "siret", "iban", "bic",
    "client", "dirigeant", "capital_social", "date_delivrance",
    "date_immatriculation", "date_emission", "date_expiration",
    "total_ht", "tva", "total_ttc",
]


class DocumentExtractor:
    def __init__(self, model_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.processor = DonutProcessor.from_pretrained(model_path)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_path).to(self.device)
        self.model.eval()

    def extract(self, image: Image.Image) -> dict:
        """Extract fields from a document image. Image must be PIL image"""
        if image.mode != "RGB":
            image = image.convert("RGB")

        pixel_values = self.processor(
            images=image, return_tensors="pt"
        ).pixel_values.to(self.device)

        decoder_input_ids = self.processor.tokenizer(
            "<s_gt_parse>",
            add_special_tokens=False,
            return_tensors="pt",
        ).input_ids.to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=512,
                early_stopping=True,
                pad_token_id=self.processor.tokenizer.pad_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
            )

        raw = self.processor.tokenizer.decode(outputs[0], skip_special_tokens=False)

        try:
            parsed = self.processor.token2json(raw)
            if "gt_parse" in parsed:
                parsed = parsed["gt_parse"]
        except Exception:
            parsed = {}

        return {field: parsed.get(field, "") for field in FIELD_ORDER}
    