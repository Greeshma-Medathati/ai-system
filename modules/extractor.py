import os
import pymupdf4llm
from config import EXTRACTED_DIR

def extract_text_from_pdf(pdf_path: str):
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    try:
        text = pymupdf4llm.to_markdown(pdf_path)
        return text
    except Exception as e:
        print(f"❌ Error extracting text from {pdf_path}: {e}")
        return None