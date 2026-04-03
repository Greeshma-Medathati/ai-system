import os
import json

from modules.search import search_papers
from modules.downloader import is_pdf_accessible, download_pdf
from modules.dataset import save_metadata
from modules.extractor import extract_text_from_pdf
from modules.section_parser import parse_sections
from modules.findings import extract_key_findings
from modules.comparer import compare_papers
from modules.pdf_metadata import extract_title_and_authors
from modules.paper_lookup import fetch_paper_metadata


RAW_DIR = "data/raw_pdfs"
EXTRACTED_DIR = "data/extracted"
METADATA_PATH = "data/metadata/papers.json"

TRAILING_WEAK_WORDS = {
    "via", "for", "with", "of", "on", "in", "to", "by", "and", "or", "the", "a", "an"
}


def get_local_pdfs(raw_dir):
    if not os.path.exists(raw_dir):
        return []
    return [
        os.path.join(raw_dir, f)
        for f in os.listdir(raw_dir)
        if f.lower().endswith(".pdf")
    ]


def load_existing_metadata():
    if not os.path.exists(METADATA_PATH):
        return {}
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            papers = json.load(f)
        return {p.get("paperId", ""): p for p in papers if p.get("paperId")}
    except Exception:
        return {}


def looks_truncated(title):
    if not title:
        return True
    words = title.strip().split()
    if not words:
        return True
    last_word = words[-1].lower().strip(".,:;!?")
    return last_word in TRAILING_WEAK_WORDS


def choose_best_title(api_title, old_title, pdf_title, paper_id):
    api_title = (api_title or "").strip()
    old_title = (old_title or "").strip()
    pdf_title = (pdf_title or "").strip()

    print(f"[TITLE DEBUG] {paper_id}")
    print(f"  API title: {api_title}")
    print(f"  OLD title: {old_title}")
    print(f"  PDF title: {pdf_title}")

    if api_title and not looks_truncated(api_title):
        print("  -> chosen source: API (clean)")
        return api_title, "api"

    if old_title and not looks_truncated(old_title):
        print("  -> chosen source: OLD METADATA (clean)")
        return old_title, "old"

    if pdf_title and not looks_truncated(pdf_title):
        print("  -> chosen source: PDF (clean)")
        return pdf_title, "pdf"

    candidates = [
        (api_title, "api"),
        (old_title, "old"),
        (pdf_title, "pdf"),
    ]
    candidates = [(t, s) for t, s in candidates if t]

    if candidates:
        best_title, best_source = max(candidates, key=lambda x: len(x[0]))
        print(f"  -> chosen source: {best_source} (longest fallback)")
        return best_title, best_source

    print("  -> chosen source: paper_id fallback")
    return paper_id, "paper_id"


def run_milestone2():
    topic = "Large Language Models security and inference efficiency"
    paper_count = 2

    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    metadata = []
    all_sections = {}
    all_findings = {}

    existing_metadata = load_existing_metadata()

    pdf_paths = get_local_pdfs(RAW_DIR)

    if pdf_paths:
        print(f"Using {len(pdf_paths)} local PDF(s) from {RAW_DIR}")
    else:
        print("No local PDFs found. Searching and downloading papers...")

        papers = search_papers(topic, limit=paper_count)
        print(f"Papers found: {len(papers)}")

        for paper in papers:
            print("PAPER FOUND:", paper.get("title"))

            pdf_info = paper.get("openAccessPdf", {})
            pdf_url = pdf_info.get("url")
            print("PDF URL:", pdf_url)

            if not pdf_url:
                print("SKIPPED: No PDF URL")
                continue

            if not is_pdf_accessible(pdf_url):
                print("SKIPPED: PDF not accessible")
                continue

            pdf_path = download_pdf(pdf_url, RAW_DIR)
            print("DOWNLOADED PATH:", pdf_path)

            if not pdf_path:
                print("SKIPPED: Download failed")
                continue

            paper["localPdfPath"] = pdf_path
            metadata.append(paper)
            pdf_paths.append(pdf_path)

    print(f"Total PDFs to process: {len(pdf_paths)}")

    for pdf_path in pdf_paths:
        pdf_name = os.path.basename(pdf_path)
        print(f"\nProcessing: {pdf_name}")

        try:
            paper_id = os.path.splitext(pdf_name)[0]

            already_present = any(
                m.get("localPdfPath") == pdf_path or m.get("paperId") == paper_id
                for m in metadata
            )

            if not already_present:
                old_meta = existing_metadata.get(paper_id, {})
                meta_api = fetch_paper_metadata(paper_id)
                meta_pdf = extract_title_and_authors(pdf_path)

                api_title = meta_api.get("title", "") if meta_api else ""
                old_title = old_meta.get("title", "") if old_meta else ""
                pdf_title = meta_pdf.get("title", "") if meta_pdf else ""

                final_title, title_source = choose_best_title(api_title, old_title, pdf_title, paper_id)

                if meta_api:
                    final_authors = meta_api.get("authors", []) or old_meta.get("authors", []) or [{"name": a} for a in meta_pdf.get("authors", [])]
                    final_year = meta_api.get("year", None)
                    if final_year in ("", None):
                        final_year = old_meta.get("year", None)

                    final_venue = meta_api.get("venue", "") or old_meta.get("venue", "")
                    final_open_access = meta_api.get("openAccessPdf", {}) or old_meta.get("openAccessPdf", {})
                    final_citation_count = meta_api.get("citationCount", 0) or old_meta.get("citationCount", 0)
                    final_paper_id = meta_api.get("paperId", paper_id)
                elif old_meta:
                    print("Using OLD SAVED METADATA")
                    final_authors = old_meta.get("authors", []) or [{"name": a} for a in meta_pdf.get("authors", [])]
                    final_year = old_meta.get("year", None)
                    final_venue = old_meta.get("venue", "")
                    final_open_access = old_meta.get("openAccessPdf", {})
                    final_citation_count = old_meta.get("citationCount", 0)
                    final_paper_id = old_meta.get("paperId", paper_id)
                else:
                    print("Using PDF fallback metadata extraction")
                    final_authors = [{"name": a} for a in meta_pdf.get("authors", [])]
                    final_year = None
                    final_venue = ""
                    final_open_access = {}
                    final_citation_count = 0
                    final_paper_id = paper_id

                print(f"[FINAL TITLE] {paper_id} -> {final_title}")
                print(f"[TITLE SOURCE] {paper_id} -> {title_source}")

                metadata.append({
                    "paperId": final_paper_id,
                    "title": final_title,
                    "authors": final_authors,
                    "year": final_year,
                    "venue": final_venue,
                    "openAccessPdf": final_open_access,
                    "citationCount": final_citation_count,
                    "localPdfPath": pdf_path,
                    "titleSource": title_source
                })

            text = extract_text_from_pdf(pdf_path)
            print("TEXT LENGTH:", len(text) if text else 0)

            if not text or not text.strip():
                print("SKIPPED: Empty extracted text")
                continue

            sections = parse_sections(text)
            print("SECTION KEYS:", list(sections.keys()) if sections else [])

            if not sections:
                print("SKIPPED: No sections parsed")
                continue

            all_sections[pdf_name] = sections

            findings = extract_key_findings(sections)
            print("FINDINGS COUNT:", len(findings))
            print("FINDINGS:", findings)

            all_findings[pdf_name] = findings

        except Exception as e:
            print(f"ERROR processing {pdf_name}: {e}")

    try:
        save_metadata(metadata)
    except Exception as e:
        print("Warning: save_metadata failed:", e)

    with open(os.path.join(EXTRACTED_DIR, "sections.json"), "w", encoding="utf-8") as f:
        json.dump(all_sections, f, indent=4, ensure_ascii=False)

    with open(os.path.join(EXTRACTED_DIR, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(all_findings, f, indent=4, ensure_ascii=False)

    print("\nALL FINDINGS:")
    print(json.dumps(all_findings, indent=2, ensure_ascii=False))

    comparison = compare_papers(all_findings)

    print("\nCOMPARISON OUTPUT:")
    print(json.dumps(comparison, indent=4, ensure_ascii=False))

    with open(os.path.join(EXTRACTED_DIR, "comparison.json"), "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=4, ensure_ascii=False)

    print("\nMilestone 2 completed successfully!")


if __name__ == "__main__":
    run_milestone2()