import json
import os


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_writer_context(findings_path, comparison_path):
    findings = load_json_file(findings_path)
    comparison = load_json_file(comparison_path)

    lines = []

    lines.append("PAPER FINDINGS:")
    for paper, paper_findings in findings.items():
        lines.append(f"\n{paper}:")
        for i, item in enumerate(paper_findings, 1):
            lines.append(f"{i}. {item}")

    lines.append("\nCROSS-PAPER COMPARISON:")

    paper_summaries = comparison.get("paper_summaries", {})
    for paper, summary in paper_summaries.items():
        lines.append(f"\n{paper}:")
        top_themes = summary.get("top_themes", [])
        if top_themes:
            lines.append("Top themes: " + ", ".join(top_themes))

        top_findings = summary.get("top_findings", [])
        if top_findings:
            lines.append("Top findings:")
            for i, item in enumerate(top_findings, 1):
                lines.append(f"{i}. {item}")

        numeric_claims = summary.get("numeric_claims", [])
        if numeric_claims:
            lines.append("Numeric claims:")
            for item in numeric_claims:
                lines.append(f"- {item['finding']} | numbers: {', '.join(item['numbers'])}")

    common_themes = comparison.get("common_themes", [])
    if common_themes:
        lines.append("\nCommon themes across papers: " + ", ".join(common_themes))
    else:
        lines.append("\nNo strong domain-specific common themes were found across the selected papers.")

    observations = comparison.get("cross_paper_observations", [])
    if observations:
        lines.append("\nCross-paper observations:")
        for obs in observations:
            lines.append(f"- {obs}")

    return "\n".join(lines)