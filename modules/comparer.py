import re
from collections import Counter

print("NEW COMPARER LOADED")

THEME_KEYWORDS = {
    "method": [
        "framework", "method", "approach", "model", "algorithm",
        "dynamic programming", "partition", "deployment", "design"
    ],
    "results": [
        "accuracy", "performance", "outperform", "improve", "throughput",
        "latency", "reduction", "increase", "score", "effective", "efficient"
    ],
    "safety": [
        "safety", "jailbreak", "attack", "vulnerable", "failure mode",
        "generalization", "competing objectives", "mismatched generalization"
    ],
    "evaluation": [
        "experiment", "evaluate", "evaluation", "benchmark", "dataset",
        "results show", "demonstrate"
    ]
}

# These are useful for per-paper summary,
# but too generic to be treated as meaningful cross-paper overlap.
GENERIC_THEMES = {"method", "results", "evaluation"}


def normalize(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def detect_themes(finding):
    s = normalize(finding)
    matched = []
    for theme, keywords in THEME_KEYWORDS.items():
        if any(kw in s for kw in keywords):
            matched.append(theme)
    return matched


def extract_numbers(text):
    # only capture percentages or decimal-style metrics,
    # avoid pulling numbers from names like GPT-4 where possible
    percent_matches = re.findall(r'\b\d+(?:\.\d+)?%\b', text)
    decimal_matches = re.findall(r'(?<![A-Za-z-])\b\d+\.\d+\b', text)

    numbers = percent_matches + decimal_matches
    return list(dict.fromkeys(numbers))  # remove duplicates, keep order


def compare_papers(paper_findings):
    print("INPUT TO COMPARER:", paper_findings)

    paper_summaries = {}
    global_theme_counter = Counter()
    observation_lines = []

    for paper_name, findings in paper_findings.items():
        themes = Counter()
        numeric_claims = []
        cleaned_findings = []

        for finding in findings:
            finding = finding.strip()
            if not finding:
                continue

            cleaned_findings.append(finding)

            found_themes = detect_themes(finding)
            for t in found_themes:
                themes[t] += 1
                global_theme_counter[t] += 1

            nums = extract_numbers(finding)
            if nums:
                numeric_claims.append({
                    "finding": finding,
                    "numbers": nums
                })

        top_themes = [theme for theme, _ in themes.most_common(3)]

        paper_summaries[paper_name] = {
            "top_findings": cleaned_findings[:5],
            "top_themes": top_themes,
            "numeric_claims": numeric_claims
        }

    # Only keep meaningful domain-specific overlaps
    common_themes = [
        theme for theme, count in global_theme_counter.items()
        if count >= 2 and theme not in GENERIC_THEMES
    ]

    if common_themes:
        observation_lines.append(
            "Common domain-specific themes across papers: " + ", ".join(common_themes) + "."
        )
    else:
        observation_lines.append(
            "No strong domain-specific common themes were found across the selected papers."
        )

    for paper_name, summary in paper_summaries.items():
        if summary["top_themes"]:
            observation_lines.append(
                f"{paper_name} mainly focuses on " + ", ".join(summary["top_themes"]) + "."
            )

        if summary["numeric_claims"]:
            observation_lines.append(
                f"{paper_name} includes measurable numeric or percentage-based claims."
            )

    return {
        "paper_summaries": paper_summaries,
        "common_themes": common_themes,
        "theme_distribution": dict(global_theme_counter),
        "cross_paper_observations": observation_lines
    }