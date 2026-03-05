"""Skill extraction — regex + dictionary matching (SPEC.md §3.8).

Pure Python regex + ESCO dictionary. No SpaCy. No LLM.
"""

import re
from collections import Counter

from src.skills.dictionary import SKILLS_DICT

# Pre-build regex patterns for multi-word skills (sorted longest first)
_MULTI_WORD_PATTERNS: list[tuple[re.Pattern[str], str]] = []
_SINGLE_WORD_KEYS: dict[str, str] = {}

for key, canonical in sorted(SKILLS_DICT.items(), key=lambda x: -len(x[0])):
    if " " in key or "." in key or "/" in key or "-" in key:
        # Multi-word or special char: use regex
        escaped = re.escape(key)
        _MULTI_WORD_PATTERNS.append(
            (re.compile(r"\b" + escaped + r"\b", re.IGNORECASE), canonical)
        )
    else:
        _SINGLE_WORD_KEYS[key.lower()] = canonical

MAX_SKILLS = 15


def extract_skills(text: str) -> list[tuple[str, float]]:
    """Extract skills from text using dictionary matching.

    Returns list of (canonical_skill_name, confidence) tuples,
    ordered by frequency of mention, capped at 15.
    Confidence is 1.0 for exact matches.
    """
    if not text or not text.strip():
        return []

    text_lower = text.lower()
    counts: Counter[str] = Counter()

    # Multi-word patterns first (greedy, longest match)
    for pattern, canonical in _MULTI_WORD_PATTERNS:
        matches = pattern.findall(text_lower)
        if matches:
            counts[canonical] += len(matches)

    # Single-word tokenization
    tokens = re.findall(r"\b[\w#+.]+\b", text_lower)
    for token in tokens:
        canonical = _SINGLE_WORD_KEYS.get(token)
        if canonical and canonical not in counts:
            counts[canonical] += 1
        elif canonical:
            counts[canonical] += 1

    # Deduplicate: if both "aws" and "amazon web services" matched,
    # they map to the same canonical — Counter handles this automatically

    # Order by frequency, cap at MAX_SKILLS
    top_skills = counts.most_common(MAX_SKILLS)

    return [(skill, 1.0) for skill, _count in top_skills]
