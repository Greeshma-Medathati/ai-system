"""
modules/evaluate_rouge.py
--------------------------
Evaluates the AI-generated literature review against reference text built
from sections.json (preferred) instead of re-extracting from PDFs.

Reference-building priority per paper:
    1. abstract
    2. abstract found inside unknown
    3. first useful chunk from introduction

Outputs:
    - data/extracted/abstracts_reference.txt
    - data/extracted/rouge_scores.json
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime

try:
    from modules.rouge_scorer import compute_rouge, format_rouge_report
except ImportError:
    from rouge_scorer import compute_rouge, format_rouge_report

try:
    from config import EXTRACTED_DIR
except ImportError:
    EXTRACTED_DIR = os.path.join("data", "extracted")

DEFAULT_DRAFT_PATH = os.path.join(EXTRACTED_DIR, "final_review_draft.txt")
DEFAULT_SECTIONS_PATH = os.path.join(EXTRACTED_DIR, "sections.json")
DEFAULT_OUTPUT_PATH = os.path.join(EXTRACTED_DIR, "rouge_scores.json")
DEFAULT_REFERENCE_PATH = os.path.join(EXTRACTED_DIR, "abstracts_reference.txt")


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("-\n", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_abstract_from_unknown(text: str) -> str:
    """
    Try to extract abstract-like content from the 'unknown' field.
    Works for patterns like:
      Abstract — ...
      _Abstract_ — ...
      ABSTRACT ...
    """
    if not text:
        return ""

    cleaned = text.replace("**", "").replace("_", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    patterns = [
        r"\babstract\b\s*[-—:]\s*(.+?)(?=\b(?:keywords?|index terms|introduction|i\.|1\.|ii\.|2\.)\b)",
        r"\babstract\b\s*(.+?)(?=\b(?:keywords?|index terms|introduction|i\.|1\.|ii\.|2\.)\b)",
        r"\babstract\b\s*[-—:]\s*(.+)",
        r"\babstract\b\s*(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE | re.DOTALL)
        if match:
            candidate = _clean_text(match.group(1))
            if len(candidate.split()) >= 30:
                return candidate

    return ""


def _fallback_from_introduction(text: str) -> str:
    """
    If abstract is unavailable, use the first meaningful chunk of introduction.
    """
    if not text:
        return ""

    cleaned = _clean_text(text)
    if not cleaned:
        return ""

    words = cleaned.split()
    return " ".join(words[:180]).strip()


def _get_reference_for_paper(pdf_name: str, paper_sections: dict) -> tuple:
    """
    Returns:
        (reference_text, source_used)
    where source_used is one of: abstract / unknown / introduction / skipped
    """
    abstract_text = _clean_text(paper_sections.get("abstract", ""))
    if len(abstract_text.split()) >= 30:
        return abstract_text, "abstract"

    unknown_text = _clean_text(paper_sections.get("unknown", ""))
    unknown_abstract = _extract_abstract_from_unknown(unknown_text)
    if len(unknown_abstract.split()) >= 30:
        return unknown_abstract, "unknown"

    intro_text = _clean_text(paper_sections.get("introduction", ""))
    intro_fallback = _fallback_from_introduction(intro_text)
    if len(intro_fallback.split()) >= 30:
        return intro_fallback, "introduction"

    return "", "skipped"


def build_reference_from_sections(
    sections_path: str = DEFAULT_SECTIONS_PATH,
    save_path: str = DEFAULT_REFERENCE_PATH,
) -> tuple:
    """
    Reads sections.json and builds one combined reference text.
    Also returns paper-wise extraction info for transparency.
    """
    if not os.path.exists(sections_path):
        print(f"[ROUGE] sections.json not found: {sections_path}")
        return "", []

    try:
        with open(sections_path, "r", encoding="utf-8") as f:
            sections_data = json.load(f)
    except Exception as exc:
        print(f"[ROUGE] Could not read sections.json: {exc}")
        return "", []

    combined_parts = []
    paper_details = []

    for pdf_name, paper_sections in sections_data.items():
        ref_text, source_used = _get_reference_for_paper(pdf_name, paper_sections)

        info = {
            "paper": pdf_name,
            "source_used": source_used,
            "word_count": len(ref_text.split()) if ref_text else 0,
        }
        paper_details.append(info)

        if ref_text:
            combined_parts.append(f"[{pdf_name} | source={source_used}]\n{ref_text}")
            print(f"[ROUGE] {pdf_name} -> {source_used} ({len(ref_text.split())} words)")
        else:
            print(f"[ROUGE] {pdf_name} -> skipped")

    if not combined_parts:
        return "", paper_details

    reference_text = "\n\n".join(combined_parts).strip()

    try:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(reference_text)
        print(f"[ROUGE] Reference text saved to: {save_path}")
    except Exception as exc:
        print(f"[ROUGE] Warning: Could not save reference text: {exc}")

    return reference_text, paper_details


def evaluate(
    draft_path: str = DEFAULT_DRAFT_PATH,
    sections_path: str = DEFAULT_SECTIONS_PATH,
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> dict:
    print("\n[ROUGE] ── Starting ROUGE Evaluation (sections.json based) ─────────────")

    if not os.path.exists(draft_path):
        return {"error": f"Generated review not found: {draft_path}"}

    try:
        with open(draft_path, "r", encoding="utf-8") as f:
            hypothesis = f.read().strip()
    except Exception as exc:
        return {"error": f"Could not read final_review_draft.txt: {exc}"}

    if not hypothesis:
        return {"error": "final_review_draft.txt is empty."}

    print(f"[ROUGE] Hypothesis : {draft_path} ({len(hypothesis.split())} words)")

    reference, paper_details = build_reference_from_sections(sections_path, DEFAULT_REFERENCE_PATH)
    if not reference:
        return {"error": "Could not build reference text from sections.json"}

    print(f"[ROUGE] Reference  : {len(reference.split())} words")

    scores = compute_rouge(hypothesis, reference)
    if "error" in scores:
        return scores

    report = format_rouge_report(
        scores,
        title="ROUGE Scores — Generated Review vs. sections.json Reference"
    )
    print(report)

    try:
        result = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "hypothesis": draft_path,
            "reference_source": sections_path,
            "paper_details": paper_details,
            "scores": scores,
        }
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"[ROUGE] Scores saved -> {output_path}")
    except Exception as exc:
        print(f"[ROUGE WARNING] Could not save JSON: {exc}")

    return scores


def safe_evaluate_and_display(
    draft_path: str = DEFAULT_DRAFT_PATH,
    sections_path: str = DEFAULT_SECTIONS_PATH,
    output_path: str = DEFAULT_OUTPUT_PATH,
) -> str:
    try:
        scores = evaluate(draft_path, sections_path, output_path)
        if "error" in scores:
            return f"⚠️ ROUGE evaluation skipped:\n{scores['error']}"
        return format_rouge_report(
            scores,
            title="ROUGE Scores — Generated Review vs. sections.json Reference"
        )
    except Exception as exc:
        return f"⚠️ ROUGE evaluation failed (non-critical):\n{exc}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate ROUGE using sections.json as reference source."
    )
    parser.add_argument(
        "--draft",
        default=DEFAULT_DRAFT_PATH,
        help=f"Path to final_review_draft.txt (default: {DEFAULT_DRAFT_PATH})"
    )
    parser.add_argument(
        "--sections",
        default=DEFAULT_SECTIONS_PATH,
        help=f"Path to sections.json (default: {DEFAULT_SECTIONS_PATH})"
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT_PATH,
        help=f"Where to save rouge_scores.json (default: {DEFAULT_OUTPUT_PATH})"
    )
    args = parser.parse_args()

    result = evaluate(
        draft_path=args.draft,
        sections_path=args.sections,
        output_path=args.output,
    )
    sys.exit(0 if "error" not in result else 1)