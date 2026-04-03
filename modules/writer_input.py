import json
import os


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_title_map():
    metadata_path = "data/metadata/papers.json"
    if not os.path.exists(metadata_path):
        return {}

    with open(metadata_path, "r", encoding="utf-8") as f:
        papers = json.load(f)

    title_map = {}
    for p in papers:
        paper_id = p.get("paperId", "")
        title = p.get("title", paper_id)
        if paper_id:
            title_map[f"{paper_id}.pdf"] = title

    return title_map


def pretty_name(pdf_name, title_map):
    return title_map.get(pdf_name, pdf_name)


def build_writer_context(findings_path, comparison_path):
    findings = load_json_file(findings_path)
    comparison = load_json_file(comparison_path)
    title_map = build_title_map()

    lines = []

    lines.append("PAPER FINDINGS:")
    for paper, paper_findings in findings.items():
        display_name = pretty_name(paper, title_map)
        lines.append(f"\n{display_name}:")
        for i, item in enumerate(paper_findings, 1):
            lines.append(f"{i}. {item}")

    lines.append("\nCROSS-PAPER COMPARISON:")

    paper_summaries = comparison.get("paper_summaries", {})
    for paper, summary in paper_summaries.items():
        display_name = pretty_name(paper, title_map)
        lines.append(f"\n{display_name}:")
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
                nums = item.get("numbers", [])
                lines.append(f"- {item['finding']} | numbers: {', '.join(nums)}")

    common_themes = comparison.get("common_themes", [])
    if common_themes:
        lines.append("\nCommon themes across papers: " + ", ".join(common_themes))
    else:
        lines.append("\nNo strong domain-specific common themes were found across the selected papers.")

    observations = comparison.get("cross_paper_observations", [])
    if observations:
        lines.append("\nCross-paper observations:")
        for obs in observations:
            # replace file ids inside observation lines too
            clean_obs = obs
            for pdf_name, title in title_map.items():
                clean_obs = clean_obs.replace(pdf_name, title)
            lines.append(f"- {clean_obs}")

    return "\n".join(lines)