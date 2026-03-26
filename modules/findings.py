import re

RESULT_KEYWORDS = [
    "accuracy", "achieved", "outperform", "outperforms", "improve", "improves",
    "improved", "improvement", "result", "results show", "score", "performance",
    "proposed", "show", "demonstrate", "demonstrates", "significantly",
    "reduction", "increase", "f1", "precision", "recall", "bleu", "rouge",
    "our model", "our approach", "we propose", "we present", "we show",
    "experimental results", "the results show", "effective", "efficient",
    "framework", "method", "approach", "dynamic programming", "latency",
    "throughput", "vulnerable", "vulnerability", "failure mode", "failure modes",
    "jailbreak", "attack", "attacks", "safety", "generalization",
    "competing objectives", "mismatched generalization", "we find",
    "we investigate", "we formulate", "we solve", "we introduce"
]

BAD_KEYWORDS = [
    "table", "figure", "appendix", "section", "supplementary", "supplement",
    "acknowledgment", "acknowledgement", "funding", "grant", "foundation",
    "project no", "project number", "national natural science foundation",
    "copyright", "license", "arxiv", "preprint"
]

SECTION_WEIGHTS = {
    "abstract": 4,
    "results": 3,
    "conclusion": 3,
    "discussion": 2,
    "findings": 2,
    "methodology": 1,
    "methods": 1
}

TARGET_SECTIONS = ["abstract", "results", "conclusion", "discussion", "findings"]


def normalize_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_sentences(text):
    text = normalize_text(text)
    if not text:
        return []
    return re.split(r'(?<=[.!?])\s+', text)


def normalize(sentence):
    s = sentence.lower()
    s = re.sub(r'[^a-z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def is_similar(a, b, threshold=0.7):
    wa = set(normalize(a).split())
    wb = set(normalize(b).split())
    if not wa or not wb:
        return False
    overlap = len(wa & wb) / max(1, min(len(wa), len(wb)))
    return overlap >= threshold


def is_noise_sentence(sentence):
    s = sentence.lower().strip()

    if len(sentence) < 40 or len(sentence) > 320:
        return True

    # heavy citation/code/funding style lines
    if re.search(r'[A-Z]{1,5}\d{1,4}[/-]\d+', sentence):
        return True

    if s.count(",") > 5 and len(s.split()) < 20:
        return True

    if any(bad in s for bad in [
        "national natural science foundation",
        "hong kong rgc",
        "grant no",
        "project no",
        "supported by",
        "funded by"
    ]):
        return True

    # pure table/figure reference style lines
    if re.match(r'^(table|figure|fig\.|appendix)\s*\d+', s):
        return True

    if s.startswith("for results on") or s.startswith("table ") or s.startswith("figure "):
        return True

    return False


def score_sentence(sentence, section_name=""):
    s = sentence.lower()
    score = 0

    # positive keyword score
    score += sum(1 for kw in RESULT_KEYWORDS if kw in s)

    # numeric boosts
    if re.search(r'\b\d+(\.\d+)?\s*%\b', s):
        score += 3
    elif re.search(r'\b\d+(\.\d+)?\b', s):
        score += 1

    # section boost
    score += SECTION_WEIGHTS.get(section_name.lower(), 0)

    # penalize noisy references to tables/figures/appendix
    for bad in BAD_KEYWORDS:
        if bad in s:
            score -= 3

    # prefer declarative research contribution/findings sentences
    if any(x in s for x in [
        "we propose", "we present", "we introduce", "we formulate",
        "results show", "we find", "our results", "we conclude",
        "outperforms", "vulnerable", "failure modes"
    ]):
        score += 2

    # penalize sentences that are only references to results location
    if any(x in s for x in [
        "table 1 presents", "table 2 presents", "table 3 presents",
        "shown in table", "see table", "shown in figure", "see appendix"
    ]):
        score -= 5

    return score


def extract_key_findings(sections, max_findings=5):
    candidate_sentences = []

    for section_name, text in sections.items():
        if not text:
            continue

        section_lower = section_name.lower()
        if not any(t in section_lower for t in TARGET_SECTIONS):
            continue

        sentences = split_sentences(text)

        for sent in sentences:
            sent = sent.strip()
            if is_noise_sentence(sent):
                continue

            score = score_sentence(sent, section_lower)
            if score > 0:
                candidate_sentences.append((score, sent))

    candidate_sentences.sort(key=lambda x: x[0], reverse=True)

    findings = []
    for _, sent in candidate_sentences:
        if any(is_similar(sent, existing) for existing in findings):
            continue
        findings.append(sent)
        if len(findings) >= max_findings:
            break

    return findings