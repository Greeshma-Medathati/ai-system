import re
import fitz


AFFILIATION_WORDS = {
    "university", "institute", "college", "department", "school",
    "laboratory", "lab", "research", "center", "centre", "academy",
    "faculty", "hospital", "corp", "inc", "ltd", "company",
    "hong kong", "china", "usa", "uk", "india"
}

BAD_AUTHOR_TOKENS = {
    "fellow", "ieee", "member", "senior member", "student member",
    "corresponding author"
}


def clean_line(line):
    line = re.sub(r"\s+", " ", line).strip()
    line = line.strip(",-;: ")
    return line


def is_email_or_url(line):
    s = line.lower()
    return "@" in s or "http://" in s or "https://" in s or "www." in s


def looks_like_affiliation(line):
    s = line.lower()
    return any(word in s for word in AFFILIATION_WORDS)


def is_bad_title_line(line):
    s = line.lower().strip()

    if not s:
        return True
    if len(s) < 8:
        return True
    if is_email_or_url(s):
        return True
    if s in {"abstract", "introduction", "keywords"}:
        return True
    if s.startswith("arxiv") or s.startswith("doi"):
        return True
    return False


def clean_author_name(name):
    name = clean_line(name)
    if not name:
        return ""

    for token in ["Fellow", "IEEE", "Member", "Senior Member", "Student Member", "Corresponding Author"]:
        name = re.sub(rf"\b{re.escape(token)}\b", "", name, flags=re.IGNORECASE)

    name = re.sub(r"[\d*†‡§]+", "", name)
    name = re.sub(r"\s+", " ", name).strip(" ,;:")
    if not name:
        return ""

    if name.lower() in BAD_AUTHOR_TOKENS:
        return ""

    return name


def looks_like_author_line(line):
    s = clean_line(line)

    if not s:
        return False
    if len(s) < 3 or len(s) > 80:
        return False
    if is_email_or_url(s):
        return False
    if looks_like_affiliation(s):
        return False

    low = s.lower()
    if low in {"abstract", "introduction", "keywords"}:
        return False

    temp = clean_author_name(s)
    if not temp:
        return False

    parts = re.split(r",| and ", temp)
    valid_name_parts = 0

    for part in parts:
        part = part.strip()
        if not part:
            continue

        words = part.split()
        if not (1 <= len(words) <= 5):
            continue

        capital_like = sum(
            1 for w in words
            if w and (w[0].isupper() or len(w) == 1)
        )

        if capital_like >= max(1, len(words) - 1):
            valid_name_parts += 1

    return valid_name_parts >= 1


def extract_title_and_authors(pdf_path):
    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        return {"title": "", "authors": []}

    page = doc[0]
    blocks = page.get_text("dict").get("blocks", [])

    lines = []
    for block in blocks:
        if "lines" not in block:
            continue
        for line in block["lines"]:
            text_parts = []
            max_size = 0
            for span in line["spans"]:
                text = span.get("text", "").strip()
                if text:
                    text_parts.append(text)
                    max_size = max(max_size, span.get("size", 0))
            line_text = clean_line(" ".join(text_parts))
            if line_text:
                lines.append({
                    "text": line_text,
                    "size": max_size
                })

    if not lines:
        doc.close()
        return {"title": "", "authors": []}

    # Step 1: find main title start line
    sorted_by_size = sorted(lines, key=lambda x: x["size"], reverse=True)

    title = ""
    title_size = 0
    title_index = -1

    for item in sorted_by_size:
        if not is_bad_title_line(item["text"]):
            title = item["text"]
            title_size = item["size"]
            break

    if not title:
        for item in lines:
            if not is_bad_title_line(item["text"]):
                title = item["text"]
                title_size = item["size"]
                break

    for i, item in enumerate(lines):
        if item["text"] == title:
            title_index = i
            break

    # Step 2: merge next line(s) if they look like title continuation
    lines_merged = 1
    if title and title_index != -1:
        merged = [title]

        for next_item in lines[title_index + 1:title_index + 4]:
            next_text = next_item["text"]
            next_low = next_text.lower()

            # hard stops
            if next_low in {"abstract", "introduction", "keywords"}:
                break
            if is_email_or_url(next_text):
                break
            if looks_like_affiliation(next_text):
                break

            word_count = len(next_text.split())

            # only treat as author line if it's short enough
            if word_count <= 5 and looks_like_author_line(next_text):
                break

            if next_item["size"] >= title_size * 0.60 and len(next_text) > 3:
                merged.append(next_text)
                lines_merged += 1
            else:
                break

        title = " ".join(merged).strip()

    # Step 3: detect authors — start AFTER all merged title lines
    authors = []
    if title_index != -1:
        author_search_start = title_index + lines_merged
        candidate_lines = lines[author_search_start:author_search_start + 8]

        for item in candidate_lines:
            line = item["text"]
            low = line.lower()

            if low == "abstract":
                break
            if is_email_or_url(line):
                continue
            if looks_like_affiliation(line):
                continue

            if looks_like_author_line(line):
                split_names = re.split(r",| and ", line)
                cleaned_names = []

                for name in split_names:
                    name = clean_author_name(name)
                    if not name:
                        continue
                    if looks_like_affiliation(name):
                        continue
                    if is_email_or_url(name):
                        continue
                    cleaned_names.append(name)

                if cleaned_names:
                    authors = cleaned_names
                    break

    doc.close()
    return {
        "title": title,
        "authors": authors
    }