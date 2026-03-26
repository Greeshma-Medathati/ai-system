import os
import json
from config import EXTRACTED_DIR, METADATA_DIR
from modules.methods_writer import generate_methods_comparison
from modules.results_writer import generate_results_synthesis
from modules.abstract_writer import generate_abstract
from modules.references import generate_references


def run_milestone3():
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    findings_path = os.path.join(EXTRACTED_DIR, "findings.json")
    comparison_path = os.path.join(EXTRACTED_DIR, "comparison.json")
    metadata_path = os.path.join(METADATA_DIR, "papers.json")

    if not os.path.exists(findings_path) or not os.path.exists(comparison_path):
        print("❌ Milestone 2 outputs not found. Run Milestone 2 first.")
        return

    with open(findings_path, "r", encoding="utf-8") as f:
        findings = json.load(f)

    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            papers = json.load(f)
    else:
        papers = []

    methods_text = generate_methods_comparison(findings_path, comparison_path)
    results_text = generate_results_synthesis(findings_path, comparison_path)
    abstract_text = generate_abstract(findings_path, comparison_path)

    references = generate_references(papers=papers, findings=findings)
    references_text = "\n".join(references) if references else "No references available."

    with open(os.path.join(EXTRACTED_DIR, "methods_comparison.txt"), "w", encoding="utf-8") as f:
        f.write(methods_text)

    with open(os.path.join(EXTRACTED_DIR, "results_synthesis.txt"), "w", encoding="utf-8") as f:
        f.write(results_text)

    with open(os.path.join(EXTRACTED_DIR, "abstract.txt"), "w", encoding="utf-8") as f:
        f.write(abstract_text)

    with open(os.path.join(EXTRACTED_DIR, "references.txt"), "w", encoding="utf-8") as f:
        f.write(references_text)

    final_draft = "\n\n".join([
        "ABSTRACT\n" + abstract_text,
        "METHODS COMPARISON\n" + methods_text,
        "RESULTS SYNTHESIS\n" + results_text,
        "REFERENCES\n" + references_text,
    ])

    with open(os.path.join(EXTRACTED_DIR, "final_review_draft.txt"), "w", encoding="utf-8") as f:
        f.write(final_draft)

    print("✅ Milestone 3 completed successfully!")
    print("Generated files:")
    print("- abstract.txt")
    print("- methods_comparison.txt")
    print("- results_synthesis.txt")
    print("- references.txt")
    print("- final_review_draft.txt")


if __name__ == "__main__":
    run_milestone3()