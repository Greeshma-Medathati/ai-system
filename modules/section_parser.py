import re

SECTION_PATTERNS = {
    "abstract": r"\babstract\b",
    "introduction": r"\bintroduction\b",
    "methodology": r"\b(methodology|methods|materials and methods)\b",
    "results": r"\b(results|findings)\b",
    "discussion": r"\bdiscussion\b",
    "conclusion": r"\b(conclusion|conclusions)\b",
}

def parse_sections(text: str):
    lines = text.splitlines()
    sections = {}
    current_section = "unknown"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip().lower()

        matched = None
        for section_name, pattern in SECTION_PATTERNS.items():
            if re.fullmatch(pattern, stripped):
                matched = section_name
                break

        if matched:
            current_section = matched
            if current_section not in sections:
                sections[current_section] = []
        else:
            sections[current_section].append(line)

    # convert lists to strings
    final_sections = {}
    for key, value in sections.items():
        final_sections[key] = "\n".join(value).strip()

    return final_sections