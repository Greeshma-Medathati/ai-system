import re

SECTION_PATTERNS = {
    "abstract": r"\babstract\b",
    "introduction": r"\bintroduction\b",
    "methods": r"\b(methodology|methods|materials and methods|method|training methodology|training parameters)\b",
    "results": r"\b(results|findings|results and discussion|models comparison|performance metrics|results and accuracy assessment|experimental results|experimental results and comparisons)\b",
    "discussion": r"\bdiscussion\b",
    "conclusion": r"\b(conclusion|conclusions)\b",
    "references": r"\breferences\b",
}


def normalize_heading(line: str) -> str:
    line = line.strip().lower()

    # remove markdown symbols
    line = re.sub(r'[#*_`>\[\]\(\)]', ' ', line)

    # remove section numbering like 1, 1., 1.1, 3.2.1
    line = re.sub(r'^\d+(\.\d+)*\.?\s*', '', line)

    # normalize spaces
    line = re.sub(r'\s+', ' ', line).strip()

    return line


def detect_section(line: str):
    cleaned = normalize_heading(line)

    # headings are usually short lines
    if len(cleaned.split()) > 8:
        return None

    for section_name, pattern in SECTION_PATTERNS.items():
        if re.search(pattern, cleaned):
            return section_name

    return None


def parse_sections(text: str):
    lines = text.splitlines()

    sections = {
        "abstract": [],
        "introduction": [],
        "methods": [],
        "results": [],
        "discussion": [],
        "conclusion": [],
        "unknown": [],
    }

    current_section = "unknown"

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if current_section:
                sections[current_section].append("")
            continue

        matched_section = detect_section(stripped)

        if matched_section:
            if matched_section == "references":
                break
            current_section = matched_section
            continue

        sections[current_section].append(line)

    final_sections = {}
    for key, value in sections.items():
        final_sections[key] = "\n".join(value).strip()

    return final_sections