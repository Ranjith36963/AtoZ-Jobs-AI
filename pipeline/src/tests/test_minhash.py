"""Tests for MinHash/LSH near-duplicate detection (SPEC.md §4.4, Gates D8-D9)."""

from src.dedup.minhash import build_lsh_index, compute_minhash, find_lsh_candidates


class TestComputeMinHash:
    """MinHash signature computation tests."""

    def test_identical_texts_high_jaccard(self) -> None:
        """Gate D8: Identical texts → Jaccard ≈ 1.0."""
        text = "Senior Python Developer required for London-based fintech startup"
        mh1 = compute_minhash(text)
        mh2 = compute_minhash(text)
        assert mh1.jaccard(mh2) > 0.99

    def test_similar_texts_above_threshold(self) -> None:
        """Gate D8: Same content, different formatting → Jaccard > 0.5."""
        text_a = "We are looking for a Senior Python Developer to join our team in London. Must have experience with Django, PostgreSQL, and AWS."
        text_b = "Senior Python Developer - London. Experience with Django, PostgreSQL and AWS required. Join our growing team."
        mh1 = compute_minhash(text_a)
        mh2 = compute_minhash(text_b)
        assert mh1.jaccard(mh2) > 0.3  # Similar but reformatted

    def test_different_texts_low_jaccard(self) -> None:
        """Gate D9: Completely unrelated texts → Jaccard < 0.3."""
        text_a = "Senior Python Developer for a fintech company in London with Django and AWS experience"
        text_b = "Head Chef required for busy restaurant in Manchester. Must have experience with fine dining and team management."
        mh1 = compute_minhash(text_a)
        mh2 = compute_minhash(text_b)
        assert mh1.jaccard(mh2) < 0.3

    def test_short_text(self) -> None:
        """Short text produces valid MinHash."""
        mh = compute_minhash("Python")
        assert mh is not None

    def test_empty_text(self) -> None:
        """Empty text produces valid MinHash (no grams but still valid)."""
        mh = compute_minhash("")
        assert mh is not None

    def test_case_insensitive(self) -> None:
        """Different casing → same MinHash."""
        mh1 = compute_minhash("Python Developer London")
        mh2 = compute_minhash("python developer london")
        assert mh1.jaccard(mh2) > 0.99


class TestBuildLshIndex:
    """LSH index building and querying tests."""

    def test_build_index(self) -> None:
        jobs = [
            {"id": 1, "description_plain": "Python developer with Django experience"},
            {"id": 2, "description_plain": "Java developer with Spring Boot experience"},
            {"id": 3, "description_plain": "Python developer with Django and PostgreSQL experience"},
        ]
        lsh = build_lsh_index(jobs)
        assert lsh is not None

    def test_find_candidates(self) -> None:
        """Near-duplicate found in LSH index."""
        # Create two very similar descriptions and one different
        base = "We are looking for a Senior Python Developer to join our team in London. The ideal candidate will have extensive experience with Django, PostgreSQL, Docker, and AWS. This is a permanent full-time role offering competitive salary."
        similar = "We are looking for a Senior Python Developer to join our team in London. The ideal candidate should have strong experience with Django, PostgreSQL, Docker, and AWS. This is a permanent full-time position with competitive pay."
        different = "Head Chef required for a busy Italian restaurant in Manchester. Must have experience managing a kitchen team and creating seasonal menus. NVQ Level 3 in catering required."

        jobs = [
            {"id": 1, "description_plain": base},
            {"id": 2, "description_plain": similar},
            {"id": 3, "description_plain": different},
        ]
        lsh = build_lsh_index(jobs, threshold=0.5)

        mh1 = compute_minhash(base)
        candidates = find_lsh_candidates(lsh, "1", mh1)
        # Job 2 should be a candidate (similar), job 3 should not
        assert "2" in candidates
        # Job 3 (chef) should not be a near-duplicate of Python dev
        assert "3" not in candidates

    def test_excludes_self(self) -> None:
        """Query excludes the job itself."""
        jobs = [
            {"id": 1, "description_plain": "Python developer in London"},
        ]
        lsh = build_lsh_index(jobs)
        mh = compute_minhash("Python developer in London")
        candidates = find_lsh_candidates(lsh, "1", mh)
        assert "1" not in candidates

    def test_empty_descriptions_skipped(self) -> None:
        """Jobs with empty descriptions are not indexed."""
        jobs = [
            {"id": 1, "description_plain": ""},
            {"id": 2, "description_plain": "   "},
            {"id": 3, "description_plain": "Valid Python developer description"},
        ]
        lsh = build_lsh_index(jobs)
        # Should not crash, index should have only job 3
        mh = compute_minhash("Valid Python developer description")
        candidates = find_lsh_candidates(lsh, "99", mh)
        assert "3" in candidates
