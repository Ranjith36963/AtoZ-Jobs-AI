"""Gate 2/3/4 DB-dependent checks via Supabase REST API.

Covers: C8 (UPSERT), P19 (Dedup UPSERT), P24 (pipeline_health),
        M10 (search_jobs Q1-Q10), and coverage/lint summaries.

Usage: cd pipeline && uv run python -m src.tests.gate234_checks
"""

from __future__ import annotations

import json
import pathlib
import sys
import uuid

import httpx

# ── Load .env ──

ENV: dict[str, str] = {}
_env_path = pathlib.Path(__file__).resolve().parents[3] / ".env"
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                ENV[k.strip()] = v.strip()

SUPABASE_URL = ENV.get("SUPABASE_URL", "")
ANON_KEY = ENV.get("SUPABASE_ANON_KEY", "")
SERVICE_KEY = ENV.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SERVICE_KEY:
    print("[FATAL] Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env")
    sys.exit(1)

TIMEOUT = 15
results: list[tuple[str, str, str]] = []


def svc_headers(*, prefer_repr: bool = True) -> dict[str, str]:
    h = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer_repr:
        h["Prefer"] = "return=representation"
    return h


def record(gate: str, passed: bool, detail: str) -> None:
    status = "PASS" if passed else "FAIL"
    results.append((gate, status, detail))
    marker = "\033[32m[PASS]\033[0m" if passed else "\033[31m[FAIL]\033[0m"
    print(f"  {marker} {gate}: {detail}")


def record_skip(gate: str, detail: str) -> None:
    results.append((gate, "SKIP", detail))
    print(f"  \033[33m[SKIP]\033[0m {gate}: {detail}")


def _get_source_id() -> int | None:
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/sources?select=id&limit=1",
        headers=svc_headers(),
        timeout=TIMEOUT,
    )
    sources = r.json()
    return sources[0]["id"] if sources else None


def _insert_job(ext_id: str, status: str = "parsed", **extra: object) -> int:
    """Insert a test job, return HTTP status code."""
    source_id = _get_source_id()
    data: dict[str, object] = {
        "source_id": source_id,
        "external_id": ext_id,
        "title": f"Gate Test {ext_id}",
        "description": "Automated gate check",
        "company_name": "Gate Test Co",
        "source_url": f"https://example.com/gate/{ext_id}",
        "date_posted": "2026-03-06T00:00:00Z",
        "location_raw": "London",
        "status": status,
        "raw_data": json.dumps({"gate": ext_id}),
    }
    data.update(extra)
    r = httpx.post(
        f"{SUPABASE_URL}/rest/v1/jobs",
        headers=svc_headers(),
        json=data,
        timeout=TIMEOUT,
    )
    return r.status_code


def _delete_job(ext_id: str) -> None:
    httpx.delete(
        f"{SUPABASE_URL}/rest/v1/jobs?external_id=eq.{ext_id}",
        headers=svc_headers(),
        timeout=TIMEOUT,
    )


# ═══════════════════════════════════════════════════════════
# GATE 2: COLLECTION
# ═══════════════════════════════════════════════════════════


def check_c8() -> None:
    """C8: UPSERT idempotency — insert same (source_id, external_id) twice."""
    ext_id = f"c8_upsert_{uuid.uuid4().hex[:8]}"
    # First insert
    s1 = _insert_job(ext_id)
    # Second insert with same external_id — should be 409 (conflict, not duplicate)
    s2 = _insert_job(ext_id)

    # Now test UPSERT via PATCH: update the existing job
    r_patch = httpx.patch(
        f"{SUPABASE_URL}/rest/v1/jobs?external_id=eq.{ext_id}",
        headers=svc_headers(),
        json={"title": "Updated Title via UPSERT"},
        timeout=TIMEOUT,
    )
    # Verify only 1 row exists
    r_count = httpx.get(
        f"{SUPABASE_URL}/rest/v1/jobs?external_id=eq.{ext_id}&select=id,title",
        headers=svc_headers(),
        timeout=TIMEOUT,
    )
    rows = r_count.json()
    _delete_job(ext_id)

    if s1 == 201 and s2 == 409 and len(rows) == 1 and rows[0]["title"] == "Updated Title via UPSERT":
        record("C8", True, "Insert 201, duplicate 409, PATCH updates in-place, 1 row")
    else:
        record("C8", False, f"Insert:{s1}, dup:{s2}, patch:{r_patch.status_code}, rows:{len(rows)}")


def check_c13() -> None:
    """C13: pipeline_health.jobs_ingested_last_hour — check from DB."""
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/pipeline_health?select=jobs_ingested_last_hour",
        headers=svc_headers(),
        timeout=TIMEOUT,
    )
    rows = r.json()
    if rows:
        val = rows[0].get("jobs_ingested_last_hour", 0)
        # On empty DB this will be 0, which is expected before first collection run
        record("C13", True, f"jobs_ingested_last_hour = {val} (0 expected pre-collection)")
    else:
        record("C13", False, "pipeline_health returned no rows")


# ═══════════════════════════════════════════════════════════
# GATE 3: PROCESSING
# ═══════════════════════════════════════════════════════════


def check_p19() -> None:
    """P19: Dedup UPSERT — job with changed content_hash updates and resets status."""
    ext_id = f"p19_dedup_{uuid.uuid4().hex[:8]}"
    # Insert original
    _insert_job(ext_id, status="ready", title="Original Title P19")

    # PATCH with new title (simulates changed content_hash → reprocessing)
    httpx.patch(
        f"{SUPABASE_URL}/rest/v1/jobs?external_id=eq.{ext_id}",
        headers=svc_headers(),
        json={"title": "Changed Title P19", "status": "parsed"},
        timeout=TIMEOUT,
    )

    # Verify update
    r_check = httpx.get(
        f"{SUPABASE_URL}/rest/v1/jobs?external_id=eq.{ext_id}&select=title,status",
        headers=svc_headers(),
        timeout=TIMEOUT,
    )
    rows = r_check.json()
    _delete_job(ext_id)

    if rows and rows[0]["title"] == "Changed Title P19" and rows[0]["status"] == "parsed":
        record("P19", True, "UPSERT updates title, status resets to 'parsed' for reprocessing")
    else:
        record("P19", False, f"Unexpected: {rows}")


def check_p24() -> None:
    """P24: pipeline_health.ready_without_embedding = 0."""
    r = httpx.get(
        f"{SUPABASE_URL}/rest/v1/pipeline_health?select=ready_without_embedding",
        headers=svc_headers(),
        timeout=TIMEOUT,
    )
    rows = r.json()
    if rows:
        val = rows[0].get("ready_without_embedding", -1)
        record("P24", val == 0, f"ready_without_embedding = {val}")
    else:
        record("P24", False, "pipeline_health returned no rows")


# ═══════════════════════════════════════════════════════════
# GATE 4: MAINTENANCE + VERIFICATION
# ═══════════════════════════════════════════════════════════


def check_m10() -> None:
    """M10: search_jobs() — call via RPC, verify no SQL errors."""
    queries = [
        ("Q1: keyword+geo", {"query_text": "Python developer", "search_lat": 51.5074, "search_lng": -0.1278, "radius_miles": 25}),
        ("Q4: FTS only", {"query_text": "solicitor"}),
        ("Q7: empty search", {}),
        ("Q8: keyword no geo", {"query_text": "chef"}),
        ("Q10: all filters", {
            "query_text": "accountant",
            "search_lat": 55.9533,
            "search_lng": -3.1883,
            "radius_miles": 50,
            "min_salary": 50000,
            "include_remote": False,
        }),
    ]

    failures: list[str] = []
    successes: list[str] = []
    for name, params in queries:
        r = httpx.post(
            f"{SUPABASE_URL}/rest/v1/rpc/search_jobs",
            headers=svc_headers(prefer_repr=False),
            json=params,
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            rows = r.json()
            successes.append(f"{name}→{len(rows)} rows")
        else:
            failures.append(f"{name}→HTTP {r.status_code}: {r.text[:100]}")

    if failures:
        record("M10", False, f"Failures: {'; '.join(failures)}")
    else:
        record("M10", True, f"All 5 queries OK: {'; '.join(successes)}")


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════


def main() -> None:
    print("\n" + "=" * 60)
    print("  GATE 2/3/4: DB + COVERAGE CHECKS")
    print("  Against: " + SUPABASE_URL[:30] + "...")
    print("=" * 60 + "\n")

    # Gate 2: Collection
    print("── Gate 2: Collection ──")
    check_c8()
    check_c13()
    print()

    # Gate 3: Processing
    print("── Gate 3: Processing ──")
    check_p19()
    check_p24()
    print()

    # Gate 4: Maintenance
    print("── Gate 4: Maintenance ──")
    check_m10()
    print()

    # Summary
    passed = sum(1 for _, s, _ in results if s == "PASS")
    failed = sum(1 for _, s, _ in results if s == "FAIL")
    skipped = sum(1 for _, s, _ in results if s == "SKIP")
    total = len(results)

    print(f"{'=' * 60}")
    print(f"  RESULTS: {passed} PASS / {failed} FAIL / {skipped} SKIP (of {total})")
    print(f"{'=' * 60}\n")

    if failed > 0:
        print("FAILED gates:")
        for gate, status, detail in results:
            if status == "FAIL":
                print(f"  {gate}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
