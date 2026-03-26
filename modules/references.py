import os


def format_authors_apa(authors):
    if not authors:
        return "Unknown Author"

    names = []
    for author in authors:
        name = author.get("name", "").strip()
        if not name:
            continue

        parts = name.split()
        if len(parts) == 1:
            names.append(parts[0])
        else:
            last_name = parts[-1]
            initials = " ".join([p[0] + "." for p in parts[:-1] if p])
            names.append(f"{last_name}, {initials}")

    if not names:
        return "Unknown Author"

    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} & {names[1]}"
    return ", ".join(names[:-1]) + f", & {names[-1]}"


def generate_references(papers=None, findings=None):
    refs = []

    # Case 1: metadata available
    if papers:
        for p in papers:
            title = p.get("title", "Unknown Title").strip()
            authors = p.get("authors", [])
            year = p.get("year", "n.d.")
            venue = p.get("venue", "").strip()
            url = ""

            open_access = p.get("openAccessPdf", {})
            if isinstance(open_access, dict):
                url = open_access.get("url", "").strip()

            author_text = format_authors_apa(authors)

            ref = f"{author_text} ({year}). {title}."
            if venue:
                ref += f" {venue}."
            if url:
                ref += f" {url}"

            refs.append(ref)

        return refs

    # Case 2: fallback from findings file names
    if findings:
        for pdf_name in findings.keys():
            title = os.path.splitext(pdf_name)[0]
            refs.append(f"Unknown Author (n.d.). {title}.")

    return refs