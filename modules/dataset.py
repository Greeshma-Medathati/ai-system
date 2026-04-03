import os
import json
from config import METADATA_DIR


def save_metadata(papers):
    os.makedirs(METADATA_DIR, exist_ok=True)
    path = os.path.join(METADATA_DIR, "papers.json")

    structured = []
    for p in papers:
        structured.append({
            "paperId": p.get("paperId", ""),
            "title": p.get("title", "Unknown Title"),
            "authors": p.get("authors", []),
            "year": p.get("year", None),
            "venue": p.get("venue", ""),
            "openAccessPdf": p.get("openAccessPdf", {}),
            "citationCount": p.get("citationCount", 0),
            "localPdfPath": p.get("localPdfPath", ""),
            "titleSource": p.get("titleSource", "")
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(structured, f, indent=4, ensure_ascii=False)

    return path