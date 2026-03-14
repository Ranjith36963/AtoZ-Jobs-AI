"""SpaCy PhraseMatcher for skill extraction (SPEC.md §3.2).

Phase 2 upgrade from Phase 1's regex SkillMatcher.
Drop-in replacement: extract(text, max_skills) → list[str].
Two-layer PhraseMatcher: LOWER for general skills, ORTH for acronyms.
"""

import spacy
from spacy.matcher import PhraseMatcher


class SpaCySkillMatcher:
    """ESCO + UK-specific skill extraction via SpaCy PhraseMatcher."""

    def __init__(self, skills_dict: dict[str, str]) -> None:
        """Initialize with skills dictionary.

        Args:
            skills_dict: Maps lowercase_pattern → canonical_name.
        """
        self.nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "lemmatizer"])
        self._canonical_map: dict[str, str] = {}

        # Layer 1: case-insensitive general skills
        self._lower_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        # Layer 2: case-sensitive acronyms (AWS, SQL, ACCA, CIPD)
        self._orth_matcher = PhraseMatcher(self.nlp.vocab, attr="ORTH")

        lower_patterns = []
        orth_patterns = []

        for pattern_text, canonical in skills_dict.items():
            self._canonical_map[pattern_text] = canonical
            doc = self.nlp.make_doc(pattern_text)

            if pattern_text.isupper() and len(pattern_text) <= 6:
                orth_patterns.append(doc)
            else:
                lower_patterns.append(doc)

        if lower_patterns:
            self._lower_matcher.add("SKILLS_LOWER", lower_patterns)
        if orth_patterns:
            self._orth_matcher.add("SKILLS_ORTH", orth_patterns)

    def extract(self, text: str, max_skills: int = 15) -> list[str]:
        """Extract skills from text. Returns canonical names, deduped, max 15."""
        if not text or not text.strip():
            return []

        doc = self.nlp(text)
        found: dict[str, int] = {}

        for matcher in [self._orth_matcher, self._lower_matcher]:
            for _match_id, start, end in matcher(doc):
                span_text = doc[start:end].text.lower()
                if span_text in self._canonical_map:
                    canonical = self._canonical_map[span_text]
                    found[canonical] = found.get(canonical, 0) + 1

        ranked = sorted(found.items(), key=lambda x: x[1], reverse=True)
        return [name for name, _ in ranked[:max_skills]]
