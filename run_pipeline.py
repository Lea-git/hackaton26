from extraction.pipeline import run_batch_extraction_pipeline, run_extraction_pipeline
from extraction.extract import DocumentExtractor
from PIL import Image


if __name__ == "__main__":
    
    run_batch_extraction_pipeline()
    
    run_test_local = False
    if run_test_local:
        MODEL_PATH = "./extraction/model"
        extractor = DocumentExtractor(MODEL_PATH)
        sample_image_path = "./donut_dataset/train/SCN1_devis_002.jpg" 
        image = Image.open(sample_image_path).convert("RGB")
        result = extractor.extract(image)
        print(result)
        print("=====================================================")
        run_extraction_pipeline("SCN-9/2026/03/18/SCN1_devis_002.pdf")
    