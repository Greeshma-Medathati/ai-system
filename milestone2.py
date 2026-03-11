import os
import json
from config import PDF_DIR, EXTRACTED_DIR
from modules.extractor import extract_text_from_pdf
from modules.section_parser import parse_sections
from modules.findings import extract_key_findings
from modules.comparer import compare_papers

def run_milestone2():
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

    if not pdf_files:
        print("❌ No PDFs found in data/raw_pdfs/")
        return

    all_sections = {}
    all_findings = {}

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        print(f"\n📄 Processing: {pdf_file}")

        text = extract_text_from_pdf(pdf_path)
        if not text:
            continue

        sections = parse_sections(text)
        all_sections[pdf_file] = sections

        findings = extract_key_findings(sections)
        all_findings[pdf_file] = findings

    comparison = compare_papers(all_findings)

    # Save outputs
    with open(os.path.join(EXTRACTED_DIR, "sections.json"), "w", encoding="utf-8") as f:
        json.dump(all_sections, f, indent=4, ensure_ascii=False)

    with open(os.path.join(EXTRACTED_DIR, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(all_findings, f, indent=4, ensure_ascii=False)

    with open(os.path.join(EXTRACTED_DIR, "comparison.txt"), "w", encoding="utf-8") as f:
        f.write(comparison)

    print("\n✅ Milestone 2 Completed Successfully!")
    print("📁 Saved:")
    print(" - data/extracted/sections.json")
    print(" - data/extracted/findings.json")
    print(" - data/extracted/comparison.txt")

if __name__ == "__main__":
    run_milestone2()