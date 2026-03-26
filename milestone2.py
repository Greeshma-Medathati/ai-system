import os
import json

from modules.search import search_papers
from modules.downloader import is_pdf_accessible, download_pdf
from modules.dataset import save_metadata
from modules.extractor import extract_text_from_pdf
from modules.section_parser import parse_sections
from modules.findings import extract_key_findings
from modules.comparer import compare_papers


RAW_DIR = "data/raw_pdfs"
EXTRACTED_DIR = "data/extracted"


def get_local_pdfs(raw_dir):
    if not os.path.exists(raw_dir):
        return []
    return [
        os.path.join(raw_dir, f)
        for f in os.listdir(raw_dir)
        if f.lower().endswith(".pdf")
    ]


def run_milestone2():
    topic = "Large Language Models security and inference efficiency"
    paper_count = 2

    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    metadata = []
    all_sections = {}
    all_findings = {}

    # --------------------------------------------------
    # STEP 1: Prefer already downloaded local PDFs
    # --------------------------------------------------
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

            metadata.append(paper)
            pdf_paths.append(pdf_path)

    # --------------------------------------------------
    # STEP 2: Process each PDF
    # --------------------------------------------------
    print(f"Total PDFs to process: {len(pdf_paths)}")

    for pdf_path in pdf_paths:
        pdf_name = os.path.basename(pdf_path)
        print(f"\nProcessing: {pdf_name}")

        try:
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

    # --------------------------------------------------
    # STEP 3: Save metadata
    # --------------------------------------------------
    try:
        save_metadata(metadata)
    except Exception as e:
        print("Warning: save_metadata failed:", e)

    # --------------------------------------------------
    # STEP 4: Save sections
    # --------------------------------------------------
    with open(os.path.join(EXTRACTED_DIR, "sections.json"), "w", encoding="utf-8") as f:
        json.dump(all_sections, f, indent=4, ensure_ascii=False)

    # --------------------------------------------------
    # STEP 5: Save findings
    # --------------------------------------------------
    with open(os.path.join(EXTRACTED_DIR, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(all_findings, f, indent=4, ensure_ascii=False)

    print("\nALL FINDINGS:")
    print(json.dumps(all_findings, indent=2, ensure_ascii=False))

    # --------------------------------------------------
    # STEP 6: Compare papers
    # --------------------------------------------------
    comparison = compare_papers(all_findings)

    print("\nCOMPARISON OUTPUT:")
    print(json.dumps(comparison, indent=4, ensure_ascii=False))

    with open(os.path.join(EXTRACTED_DIR, "comparison.json"), "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=4, ensure_ascii=False)

    print("\nMilestone 2 completed successfully!")


if __name__ == "__main__":
    run_milestone2()