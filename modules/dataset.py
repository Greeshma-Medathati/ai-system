import os
import json
from config import METADATA_DIR

def save_metadata(selected_papers: list):
    os.makedirs(METADATA_DIR, exist_ok=True)
    path = os.path.join(METADATA_DIR, "papers.json")

    clean_data = []

    for p in selected_papers:
        clean_data.append({
            "paperId": p.get("paperId"),
            "title": p.get("title"),
            "year": p.get("year"),
            "localPdfPath": p.get("localPdfPath")
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean_data, f, indent=4, ensure_ascii=False)

    return path