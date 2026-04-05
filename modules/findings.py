import re
from collections import Counter

import spacy

# Lightweight spaCy pipeline only for sentence splitting
nlp = spacy.blank("en")
if "sentencizer" not in nlp.pipe_names:
    nlp.add_pipe("sentencizer")


TARGET_SECTIONS = {
    "abstract",
    "introduction",
    "methods",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "findings",
}

SECTION_WEIGHTS = {
    "abstract": 3,
    "results": 4,
    "discussion": 3,
    "conclusion": 4,
    "findings": 4,
    "methods": 2,
    "methodology": 2,
    "introduction": 1,
}

KEYWORDS = {
    "propose": 3,
    "proposed": 3,
    "present": 2,
    "introduced": 2,
    "introduce": 2,
    "develop": 2,
    "demonstrate": 3,
    "demonstrates": 3,
    "show": 2,
    "shows": 2,
    "shown": 2,
    "result": 2,
    "results": 2,
    "finding": 2,
    "findings": 2,
    "improve": 3,
    "improved": 3,
    "improvement": 3,
    "outperform": 4,
    "outperforms": 4,
    "increase": 2,
    "increased": 2,
    "reduce": 2,
    "reduced": 2,
    "achieve": 3,
    "achieves": 3,
    "achieved": 3,
    "effective": 2,
    "efficient": 2,
    "robust": 2,
    "significant": 2,
    "state-of-the-art": 4,
    "sota": 4,
    "accuracy": 3,
    "precision": 3,
    "recall": 3,
    "f1": 3,
    "auc": 3,
    "benchmark": 2,
    "dataset": 2,
    "privacy": 3,
    "differential privacy": 4,
    "epsilon": 3,
    "attack": 3,
    "attacks": 3,
    "defense": 3,
    "defenses": 3,
    "membership inference": 4,
    "robustness": 2,
    "trade-off": 2,
    "lower bound": 2,
    "upper bound": 2,
    "empirical": 2,
    "evaluation": 2,
    "safety": 2,
    "security": 2,
    "explainability": 2,
    "fairness": 2,
    "bias": 2,
}

GENERIC_PHRASES = [
    "in this paper",
    "this study",
    "this work",
    "we discuss",
    "we explore",
    "is important",
    "can be used",
]

VAGUE_WORDS = ["may", "can", "could", "might"]

STRONG_RESULT_PHRASES = [
    "improves",
    "achieves",
    "outperforms",
    "reduces error",
    "significantly improves",
    "significantly reduces",
    "higher accuracy",
    "better performance",
    "greater accuracy",
]

NOISE_PATTERNS = [
    r"^\s*figure\s+\d+",
    r"^\s*fig\.\s*\d+",
    r"^\s*table\s+\d+",
    r"^\s*algorithm\s+\d+",
    r"^\s*appendix\b",
    r"^\s*references\b",
    r"^\s*copyright\b",
    r"^\s*arxiv\b",
    r"^\s*preprint\b",
    r"^\s*http[s]?://",
    r"^\s*www\.",
    r"^\s*\[\d+\]\s*$",
    r"^\s*\[[\d,\s]+\]",
    r"<br\s*/?>",
    r"<[a-z]+[^>]*>",
]

# Sentence-level patterns that indicate generic background/policy text
# not actual research contributions
GENERIC_SENTENCE_PATTERNS = [
    r"^for example[,\s]",
    r"^for instance[,\s]",
    r"^as an example[,\s]",
    r"^it is (important|worth|noted)",
    r"^the (following|above|below)",
    r"is based (in|on) a series of principles",
    r"list(s)? out\b",
    r"reminds? that\b",
    r"\bassessment is based\b",
    r"\bprinciples?:\s*1\)",
    r"^[A-Z][a-z]+ [A-Z][a-z]+ (–|-) [A-Z][a-z]+ [A-Z][a-z]+",
    r"^hence\b",
    r"^therefore\b",
    r"^thus\b",
    r"\bhuman touch\b",
    r"\bemotional connect",
    r"\bside effect\b",
    r"\bex ploiting\b",
    r"\bcompu tational\b",
    r"\binfra structure\b",
]

MIN_SCORE_THRESHOLD = 3

GENERIC_STOPWORDS = {
    "paper", "study", "method", "methods", "result", "results", "system",
    "approach", "model", "models", "evaluation", "analysis"
}


def split_sentences(text: str):
    if not text:
        return []
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


def clean_sentence(sentence: str) -> str:
    sentence = sentence.replace("||", " ")
    sentence = sentence.replace("##", " ")
    sentence = sentence.replace("_", " ")
    sentence = sentence.replace("\xad", "")
    sentence = sentence.replace("\ufb01", "fi")
    sentence = sentence.replace("\ufb02", "fl")
    # Fix 1: strip inline citations like [386], [297, 298, 299] before scoring
    sentence = re.sub(r"\[\d+(?:,\s*\d+)*\]", "", sentence)
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.strip()


def normalize_sentence(sentence: str) -> str:
    sentence = sentence.strip()
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence


def is_noise_sentence(sentence: str) -> bool:
    s = sentence.strip()
    s_lower = s.lower()

    if len(s) < 25:
        return True

    if len(s) > 600:
        return True

    # Pipe characters = table cell separators or HTML artifacts
    if "|" in s:
        return True

    if "||" in s or "##" in s:
        return True

    # HTML tags anywhere in sentence
    if re.search(r"<[a-zA-Z/][^>]*>", s):
        return True

    if "figure" in s_lower or "fig." in s_lower:
        return True

    for pattern in NOISE_PATTERNS:
        if re.search(pattern, s_lower):
            return True

    symbol_count = sum(1 for ch in s if not ch.isalnum() and not ch.isspace())
    if len(s) > 0 and symbol_count / len(s) > 0.25:
        return True

    if len(s) < 80 and s.isupper():
        return True

    # Filter sentences dominated by inline citations
    citation_density = len(re.findall(r"\[\d+\]", s))
    if citation_density > 3:
        return True

    # Sentence ends mid-expression — PDF extraction artifact
    if re.search(r"[-–]\s*\[?\s*$", s):
        return True

    # Sentence ends with open bracket or dangling punctuation
    if re.search(r"[\(\[{\-–]\s*$", s):
        return True

    # Generic background/policy sentences — not research contributions
    for pattern in GENERIC_SENTENCE_PATTERNS:
        if re.search(pattern, s_lower):
            return True

    # OCR split-word detection: two short fragments joined by a space mid-word
    # catches "ex ploiting", "compu tational", "sig nificant" etc.
    ocr_split = re.findall(r'\b([a-z]{2,4})\s([a-z]{4,}ing|[a-z]{4,}tion|[a-z]{4,}ment)\b', s_lower)
    if len(ocr_split) >= 2:
        return True

    return False


def score_sentence(sentence: str, section_name: str) -> int:
    s = sentence.lower()
    score = 0

    score += SECTION_WEIGHTS.get(section_name.lower(), 0)

    for phrase in GENERIC_PHRASES:
        if phrase in s:
            score -= 2

    # Stronger penalty: vague modal words per occurrence
    for word in VAGUE_WORDS:
        if re.search(rf"\b{re.escape(word)}\b", s):
            score -= 2  # was -1, raised to -2

    # Heavy penalty for "for example" / "for instance" openers
    if re.search(r"^for (example|instance)[,\s]", s):
        score -= 5

    # Heavy penalty for pure enumeration/list sentences (policy lists)
    if re.search(r"\d\)\s+\w", s) and s.count(";") >= 2:
        score -= 4

    for kw, weight in KEYWORDS.items():
        if kw in s:
            score += weight

    # Enhancement 1: smarter numeric scoring
    if re.search(r"\b\d+(\.\d+)?%\b", sentence):
        score += 3
    elif re.search(r"\b0\.\d{2,}\b", sentence):
        score += 3
    elif re.search(r"\b\d{1,3}x\b", sentence):
        score += 3
    elif re.search(r"\b\d+(\.\d+)?\b", sentence):
        score += 1

    contribution_patterns = [
        r"\bwe propose\b",
        r"\bwe present\b",
        r"\bwe introduce\b",
        r"\bwe demonstrate\b",
        r"\bour method\b",
        r"\bresults show\b",
        r"\bexperimental results\b",
        r"\bwe achieve\b",
        r"\bthis work\b",
    ]
    for pat in contribution_patterns:
        if re.search(pat, s):
            score += 3

    if any(phrase in s for phrase in STRONG_RESULT_PHRASES):
        score += 3

    if len(sentence) > 350:
        score -= 2

    # Reward ideal sentence length
    if 80 <= len(sentence) <= 250:
        score += 1

    return score


def sentence_signature(sentence: str) -> str:
    s = normalize_sentence(sentence).lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    return s


def is_similar(sent1: str, sent2: str, threshold: float = 0.65) -> bool:
    # Enhancement 3: lowered threshold from 0.8 to 0.65 for better dedup
    a = set(sentence_signature(sent1).split())
    b = set(sentence_signature(sent2).split())

    if not a or not b:
        return False

    overlap = len(a & b) / max(1, len(a | b))
    return overlap >= threshold


def get_fallback_sentences(sections: dict, seen: list, max_findings: int = 5):
    # Enhancement 6: accept `seen` so fallback deduplicates against all tiers
    priority_sections = ["abstract", "conclusion", "results", "discussion"]
    fallback = []

    for sec in priority_sections:
        text = sections.get(sec, "")
        if not text:
            continue

        for sent in split_sentences(text):
            sent = normalize_sentence(sent)
            sent = clean_sentence(sent)

            if is_noise_sentence(sent):
                continue
            if len(sent) < 25 or len(sent) > 500:
                continue
            if any(is_similar(sent, prev) for prev in seen):
                continue

            fallback.append(sent)
            if len(fallback) >= max_findings * 2:
                return fallback

    return fallback


def extract_key_findings(sections: dict, max_findings: int = 5):
    if not sections:
        return []

    candidates = []
    fallback_candidates = []

    for section_name, text in sections.items():
        if not text:
            continue

        sec = section_name.lower().strip()

        if sec not in TARGET_SECTIONS:
            continue

        sentences = split_sentences(text)

        for sent in sentences:
            sent = normalize_sentence(sent)
            sent = clean_sentence(sent)

            if is_noise_sentence(sent):
                continue

            if 25 <= len(sent) <= 500:
                fallback_candidates.append((SECTION_WEIGHTS.get(sec, 0), sent))

            score = score_sentence(sent, sec)
            if score >= MIN_SCORE_THRESHOLD:
                candidates.append((score, sent, sec))

    candidates.sort(key=lambda x: x[0], reverse=True)

    findings = []
    seen = []

    # Tier 1: scored candidates
    for score, sent, sec in candidates:
        if any(is_similar(sent, prev) for prev in seen):
            continue
        seen.append(sent)
        findings.append(sent)
        if len(findings) >= max_findings:
            break

    if findings:
        return findings

    # Tier 2: fallback by section weight
    fallback_candidates.sort(key=lambda x: x[0], reverse=True)
    for _, sent in fallback_candidates:
        if any(is_similar(sent, prev) for prev in seen):
            continue
        seen.append(sent)
        findings.append(sent)
        if len(findings) >= max_findings:
            break

    if findings:
        return findings

    # Tier 3: raw fallback — Enhancement 6: pass `seen` to avoid cross-tier duplicates
    for sent in get_fallback_sentences(sections, seen=seen, max_findings=max_findings):
        if any(is_similar(sent, prev) for prev in seen):
            continue
        seen.append(sent)
        findings.append(sent)
        if len(findings) >= max_findings:
            break

    return findings


def summarize_findings_keywords(findings: list, top_k: int = 5) -> list:
    tokens = []
    for finding in findings:
        words = re.findall(r"\b[a-zA-Z][a-zA-Z\-]{2,}\b", finding.lower())
        tokens.extend([w for w in words if w not in GENERIC_STOPWORDS])

    freq = Counter(tokens)
    return [word for word, _ in freq.most_common(top_k)]


# Enhancement 4: combined export so comparer.py can consume findings + keywords
# without re-tokenizing
def extract_findings_with_keywords(sections: dict, max_findings: int = 5) -> dict:
    findings = extract_key_findings(sections, max_findings)
    keywords = summarize_findings_keywords(findings, top_k=5)
    return {"findings": findings, "keywords": keywords}