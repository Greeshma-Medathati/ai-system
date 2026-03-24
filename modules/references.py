import json
import os
from config import METADATA_DIR


def format_authors_apa(authors):
    if not authors:
        return ""

    formatted = []
    for author in authors:
        name = author.get("name", "").strip()
        if not name:
            continue

        parts = name.split()
        if len(parts) == 1:
            formatted.append(parts[0])
        else:
            last = parts[-1]
            initials = " ".join([p[0].upper() + "." for p in parts[:-1] if p])
            formatted.append(f"{last}, {initials}")

    if len(formatted) == 1:
        return formatted[0]
    if len(formatted) == 2:
        return f"{formatted[0]} & {formatted[1]}"
    return ", ".join(formatted[:-1]) + f", & {formatted[-1]}"


def format_reference_apa(paper):
    authors = format_authors_apa(paper.get("authors", []))
    year = paper.get("year", "n.d.")
    title = paper.get("title", "Untitled").strip()

    if authors:
        return f"{authors} ({year}). {title}."
    return f"{title}. ({year})."


def generate_references():
    metadata_path = os.path.join(METADATA_DIR, "papers.json")
    if not os.path.exists(metadata_path):
        return []

    with open(metadata_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    references = [format_reference_apa(p) for p in papers]
    return references