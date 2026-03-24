import os
import json
from config import EXTRACTED_DIR, METADATA_DIR
from modules.methods_writer import generate_methods_comparison
from modules.results_writer import generate_results_synthesis
from modules.abstract_writer import generate_abstract
from modules.references import generate_references


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text_file(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def build_title_map():
    metadata_path = os.path.join(METADATA_DIR, "papers.json")
    if not os.path.exists(metadata_path):
        return {}

    with open(metadata_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    title_map = {}
    for p in papers:
        pid = p.get("paperId", "")
        title = p.get("title", pid)
        if pid:
            title_map[f"{pid}.pdf"] = title
    return title_map


def run_milestone3():
    os.makedirs(EXTRACTED_DIR, exist_ok=True)

    sections = load_json_file(os.path.join(EXTRACTED_DIR, "sections.json"))
    findings = load_json_file(os.path.join(EXTRACTED_DIR, "findings.json"))
    comparison = load_text_file(os.path.join(EXTRACTED_DIR, "comparison.txt"))
    title_map = build_title_map()

    if not sections or not findings:
        print("❌ Milestone 2 outputs not found. Run Milestone 2 first.")
        return

    methods_text = generate_methods_comparison(sections, title_map)
    results_text = generate_results_synthesis(sections, findings, title_map)

    findings_text = json.dumps(findings, indent=2, ensure_ascii=False)
    abstract_text = generate_abstract(findings_text, comparison, methods_text, results_text)

    references = generate_references()
    references_text = "\n".join(references)

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