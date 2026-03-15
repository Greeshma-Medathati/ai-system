import os
import json

from config import PDF_DIR, EXTRACTED_DIR
from modules.extractor import extract_text_from_pdf
from modules.section_parser import parse_sections
from modules.findings import extract_key_findings
from modules.comparer import compare_papers
from modules.reviewer import generate_literature_review


def run_milestone2():
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

    if not pdf_files:
        print("❌ No PDFs found in data/raw_pdfs/")
        return

    all_sections = {}
    all_findings = {}
    paper_titles = {}

    for pdf_file in pdf_files:

        pdf_path = os.path.join(PDF_DIR, pdf_file)
        print(f"\n📄 Processing: {pdf_file}")

        text = extract_text_from_pdf(pdf_path)

        if not text:
            print("⚠️ No text extracted.")
            continue

        # Parse sections
        sections = parse_sections(text)
        all_sections[pdf_file] = sections

        # Extract findings
        findings = extract_key_findings(sections)
        all_findings[pdf_file] = findings

        # Clean title (remove .pdf)
        paper_titles[pdf_file] = pdf_file.replace(".pdf", "")

    # Generate comparison
    comparison = compare_papers(all_findings)

    # Generate literature review narrative
    literature_review = generate_literature_review(all_findings, paper_titles)

    # Save sections
    with open(os.path.join(EXTRACTED_DIR, "sections.json"), "w", encoding="utf-8") as f:
        json.dump(all_sections, f, indent=4, ensure_ascii=False)

    # Save findings
    with open(os.path.join(EXTRACTED_DIR, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(all_findings, f, indent=4, ensure_ascii=False)

    # Save comparison
    with open(os.path.join(EXTRACTED_DIR, "comparison.txt"), "w", encoding="utf-8") as f:
        f.write(comparison)

    # Save literature review
    with open(os.path.join(EXTRACTED_DIR, "literature_review.txt"), "w", encoding="utf-8") as f:
        f.write(literature_review)

    print("\n✅ Milestone 2 Completed Successfully!")
    print("\n📁 Files Generated:")
    print(" - sections.json")
    print(" - findings.json")
    print(" - comparison.txt")
    print(" - literature_review.txt")


if __name__ == "__main__":
    run_milestone2()