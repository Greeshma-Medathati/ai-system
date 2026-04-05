"""
modules/rouge_scorer.py
-----------------------
Core ROUGE scoring engine. Pure Python — zero external dependencies.
Computes ROUGE-1, ROUGE-2, and ROUGE-L (Precision, Recall, F1).

This file only does math. It knows nothing about PDFs or file paths.
"""

import re
from collections import Counter


# ── Text helpers ──────────────────────────────────────────────────────────────

def _normalise(text: str) -> list:
    """Lowercase, strip punctuation, tokenise."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def _ngrams(tokens: list, n: int) -> Counter:
    return Counter(tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1))


def _lcs_length(x: list, y: list) -> int:
    """Dynamic-programming LCS (memory-efficient two-row version)."""
    m, n = len(x), len(y)
    if m == 0 or n == 0:
        return 0
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            curr[j] = prev[j - 1] + 1 if x[i-1] == y[j-1] else max(curr[j-1], prev[j])
        prev, curr = curr, [0] * (n + 1)
    return prev[n]


def _prf(match, pred, ref):
    p = match / pred if pred else 0.0
    r = match / ref  if ref  else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"p": round(p, 4), "r": round(r, 4), "f": round(f, 4)}


# ── Public API ────────────────────────────────────────────────────────────────

def compute_rouge(hypothesis: str, reference: str) -> dict:
    """
    Compute ROUGE-1, ROUGE-2, ROUGE-L between two plain-text strings.

    Parameters
    ----------
    hypothesis : str   The AI-generated literature review text.
    reference  : str   The concatenated abstracts from all input papers.

    Returns
    -------
    {
      'rouge-1': {'p': float, 'r': float, 'f': float},
      'rouge-2': {'p': float, 'r': float, 'f': float},
      'rouge-l': {'p': float, 'r': float, 'f': float},
    }
    or {'error': str} on any failure.
    """
    try:
        if not (hypothesis and hypothesis.strip()):
            return {"error": "Hypothesis (generated review) is empty."}
        if not (reference and reference.strip()):
            return {"error": "Reference (abstracts) is empty."}

        hyp = _normalise(hypothesis)
        ref = _normalise(reference)

        r1_hyp = _ngrams(hyp, 1);  r1_ref = _ngrams(ref, 1)
        r2_hyp = _ngrams(hyp, 2);  r2_ref = _ngrams(ref, 2)

        return {
            "rouge-1": _prf(sum((r1_hyp & r1_ref).values()), sum(r1_hyp.values()), sum(r1_ref.values())),
            "rouge-2": _prf(sum((r2_hyp & r2_ref).values()), sum(r2_hyp.values()), sum(r2_ref.values())),
            "rouge-l": _prf(_lcs_length(hyp, ref), len(hyp), len(ref)),
        }
    except Exception as exc:
        return {"error": str(exc)}


def format_rouge_report(scores: dict, title: str = "ROUGE Evaluation Report") -> str:
    """Return a formatted table string suitable for printing or Gradio display."""
    if "error" in scores:
        return f"[ROUGE ERROR] {scores['error']}"

    lines = [
        f"\n{'=' * 50}",
        f"  {title}",
        f"{'=' * 50}",
        f"{'Metric':<12} {'Precision':>10} {'Recall':>10} {'F1-Score':>10}",
        f"{'-' * 50}",
    ]
    for metric in ["rouge-1", "rouge-2", "rouge-l"]:
        if metric in scores:
            s = scores[metric]
            lines.append(f"{metric.upper():<12} {s['p']:>10.4f} {s['r']:>10.4f} {s['f']:>10.4f}")
    lines.append(f"{'=' * 50}\n")
    return "\n".join(lines)