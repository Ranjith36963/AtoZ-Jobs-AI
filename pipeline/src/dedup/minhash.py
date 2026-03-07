"""MinHash/LSH near-duplicate detection (SPEC.md §4.4).

Stage 3 of the 3-stage dedup architecture.
Uses datasketch with xxhash for fast MinHash signatures and LSH indexing.
"""

import xxhash
from datasketch import MinHash, MinHashLSH


def compute_minhash(text: str, num_perm: int = 128) -> MinHash:
    """Compute MinHash signature for a job description.

    Uses 3-character grams for robustness against formatting changes.

    Args:
        text: Job description text.
        num_perm: Number of hash permutations (default 128).

    Returns:
        MinHash signature.
    """
    m = MinHash(num_perm=num_perm, hashfunc=xxhash.xxh64_intdigest)
    text = text.lower().strip()
    # Tokenize into 3-grams (character level for robustness)
    for i in range(len(text) - 2):
        m.update(text[i : i + 3].encode("utf-8"))
    return m


def build_lsh_index(
    jobs: list[dict[str, object]],
    threshold: float = 0.5,
    num_perm: int = 128,
) -> MinHashLSH:
    """Build LSH index from job descriptions.

    Args:
        jobs: List of job dicts with 'id' and 'description_plain'.
        threshold: Jaccard similarity threshold for candidate detection.
        num_perm: Number of hash permutations.

    Returns:
        Populated MinHashLSH index.
    """
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for job in jobs:
        desc = str(job.get("description_plain", ""))
        if not desc.strip():
            continue
        mh = compute_minhash(desc, num_perm)
        job_key = str(job["id"])
        try:
            lsh.insert(job_key, mh)
        except ValueError:
            # Duplicate key — skip
            pass
    return lsh


def find_lsh_candidates(
    lsh: MinHashLSH,
    job_id: str,
    minhash: MinHash,
) -> list[str]:
    """Find near-duplicate candidates from LSH index.

    Args:
        lsh: Populated MinHashLSH index.
        job_id: ID of the query job (excluded from results).
        minhash: MinHash signature of the query job.

    Returns:
        List of candidate job IDs (as strings).
    """
    results = lsh.query(minhash)
    return [r for r in results if r != job_id]
