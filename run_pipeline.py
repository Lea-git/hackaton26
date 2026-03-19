from extraction.pipeline import run_batch_extraction_pipeline, run_extraction_pipeline
from extraction.extract import DocumentExtractor
from PIL import Image


if __name__ == "__main__":
    
    run_batch_extraction_pipeline(prefix="dataset/")
    
    run_test_local = False
    if run_test_local:
        MODEL_PATH = "./extraction/model"
        extractor = DocumentExtractor(MODEL_PATH)
        sample_image_path = "./donut_dataset/train/SCN1_devis_007.jpg" 
        image = Image.open(sample_image_path).convert("RGB")
        result = extractor.extract(image)
        print(result)
        print("=====================================================")
        x = run_extraction_pipeline("dataset/SCN1_devis_010.pdf")
        print(x)
    