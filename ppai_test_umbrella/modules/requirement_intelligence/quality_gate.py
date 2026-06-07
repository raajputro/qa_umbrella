from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Tuple

ALLOWED_TITLE_PREFIXES = ("Verify that", "Ensure that", "Validate that")
ALLOWED_TYPES = {"positive", "negative", "boundary", "edge"}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "at", "by",
    "with", "is", "are", "be", "as", "from", "that", "this", "will", "shall",
    "should", "can", "may", "must", "user", "system", "field", "button", "page",
    "screen", "verify", "ensure", "validate", "confirm", "assert", "check"
}


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []


def normalize_text(text: str) -> str:
    text = str(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_set(text: str) -> set[str]:
    return {t for t in normalize_text(text).split() if t and t not in _STOPWORDS}


def testcase_signature(tc: Dict[str, Any]) -> str:
    parts = [
        tc.get("title", ""),
        tc.get("type", ""),
        tc.get("evidence_quote", ""),
        " ".join(_as_list(tc.get("source_requirement_ids"))),
    ]
    tokens = sorted(token_set(" ".join(parts)))
    return " ".join(tokens)


def similarity(a: str, b: str) -> float:
    a_set, b_set = token_set(a), token_set(b)
    if not a_set or not b_set:
        return 0.0
    jaccard = len(a_set & b_set) / len(a_set | b_set)
    seq = SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()
    return max(jaccard, seq)


def evidence_is_present(evidence_quote: str, source_text: str) -> bool:
    evidence = normalize_text(evidence_quote)
    source = normalize_text(source_text)
    if len(evidence) < 8:
        return False
    if evidence in source:
        return True
    # Check similarity line-by-line to handle short quotes against large documents
    for line in source_text.splitlines():
        norm_line = normalize_text(line)
        if len(norm_line) >= 8 and similarity(evidence, norm_line) > 0.80:
            return True
            
    return False


def validate_testcase(tc: Dict[str, Any], source_text: str) -> Tuple[bool, List[str]]:
    reasons: List[str] = []

    if not isinstance(tc, dict):
        return False, ["not a dict"]

    title = str(tc.get("title", "")).strip()
    if not title.startswith(ALLOWED_TITLE_PREFIXES):
        reasons.append("invalid title prefix")

    tc_type = str(tc.get("type", "")).strip().lower()
    if tc_type not in ALLOWED_TYPES:
        reasons.append("invalid type")
    else:
        tc["type"] = tc_type

    if tc.get("assumption_flag") is True:
        reasons.append("assumption_flag=true")

    evidence = str(tc.get("evidence_quote", "")).strip()
    if not evidence:
        reasons.append("missing evidence_quote")
    elif not evidence_is_present(evidence, source_text):
        reasons.append("evidence_quote not found in SRS source text")

    steps = _as_list(tc.get("steps"))
    expected = _as_list(tc.get("expected_result"))
    if not steps:
        reasons.append("missing steps")
    if not expected:
        reasons.append("missing expected_result")

    # Boundary tests must cite actual numeric/date/status/limit evidence.
    if tc_type == "boundary":
        boundary_text = " ".join([title, evidence, " ".join(expected)])
        if not re.search(r"\b(min|max|minimum|maximum|greater than|less than|not beyond|within|before|after|current month|limit|\d+)\b", boundary_text, re.I):
            reasons.append("boundary case has no explicit boundary evidence")

    # Clean normalized list fields.
    tc["steps"] = steps
    tc["expected_result"] = expected
    tc["preconditions"] = _as_list(tc.get("preconditions"))
    tc["source_requirement_ids"] = _as_list(tc.get("source_requirement_ids")) or ["REQ-UNMAPPED"]
    tc["evidence_quote"] = evidence
    tc["assumption_flag"] = bool(tc.get("assumption_flag", False))

    return not reasons, reasons


def filter_and_deduplicate(
    test_cases: Iterable[Dict[str, Any]],
    source_text: str,
    existing: Iterable[Dict[str, Any]] | None = None,
    similarity_threshold: float = 0.78,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    signatures: List[str] = []

    for old in existing or []:
        if isinstance(old, dict):
            signatures.append(testcase_signature(old))

    for tc in test_cases or []:
        if not isinstance(tc, dict):
            rejected.append({"test_case": tc, "reasons": ["not a dict"]})
            continue

        ok, reasons = validate_testcase(tc, source_text)
        sig = testcase_signature(tc)

        if ok:
            for old_sig in signatures:
                if similarity(sig, old_sig) >= similarity_threshold:
                    ok = False
                    reasons.append("duplicate or near-duplicate behavior")
                    break

        if ok:
            signatures.append(sig)
            accepted.append(tc)
        else:
            rejected.append({"test_case": tc, "reasons": reasons})

    return accepted, rejected
