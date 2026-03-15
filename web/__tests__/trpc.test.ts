import { describe, it, expect, vi, beforeEach } from "vitest";

// ── Mock Supabase clients ──────────────────────────────────────────────
const mockSupabaseFrom = vi.fn();
const mockAdminFrom = vi.fn();
const mockAdminInsert = vi.fn();

vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(async () => ({
    from: mockSupabaseFrom,
  })),
}));

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: () => ({
    from: mockAdminFrom,
  }),
}));

// Import router after mocks are set up
import { appRouter } from "@/server/routers";

describe("tRPC routers", () => {
  const caller = appRouter.createCaller({});

  beforeEach(() => {
    vi.clearAllMocks();
    // Default admin mock for audit logging (fire-and-forget)
    mockAdminFrom.mockReturnValue({
      insert: mockAdminInsert.mockResolvedValue({ error: null }),
    });
  });

  // ── Facets ────────────────────────────────────────────────────────

  it("facets.counts groups by facet_type correctly", async () => {
    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockResolvedValue({
        data: [
          { facet_type: "category", facet_value: "technology", job_count: 10 },
          { facet_type: "category", facet_value: "finance", job_count: 5 },
          { facet_type: "work_type", facet_value: "remote", job_count: 8 },
          { facet_type: "seniority", facet_value: "mid", job_count: 12 },
          { facet_type: "employment_type", facet_value: "full-time", job_count: 20 },
        ],
        error: null,
      }),
    });

    const result = await caller.facets.counts();

    expect(result.categories).toEqual([
      { value: "technology", count: 10 },
      { value: "finance", count: 5 },
    ]);
    expect(result.workTypes).toEqual([{ value: "remote", count: 8 }]);
    expect(result.seniorities).toEqual([{ value: "mid", count: 12 }]);
    expect(result.employmentTypes).toEqual([{ value: "full-time", count: 20 }]);
  });

  it("facets.counts returns empty arrays on error", async () => {
    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockResolvedValue({
        data: null,
        error: { message: "relation not found" },
      }),
    });

    const result = await caller.facets.counts();

    expect(result).toEqual({
      categories: [],
      workTypes: [],
      seniorities: [],
      employmentTypes: [],
    });
  });

  it("facets.salaryHistogram maps buckets correctly", async () => {
    const mockOrder = vi.fn().mockResolvedValue({
      data: [
        { bucket: 1, bucket_min: 20000, bucket_max: 30000, job_count: 5 },
        { bucket: 2, bucket_min: 30000, bucket_max: 40000, job_count: 10 },
        { bucket: 3, bucket_min: 40000, bucket_max: 50000, job_count: 8 },
      ],
      error: null,
    });

    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        order: mockOrder,
      }),
    });

    const result = await caller.facets.salaryHistogram();

    expect(result.buckets).toEqual([
      { min: 20000, max: 30000, count: 5 },
      { min: 30000, max: 40000, count: 10 },
      { min: 40000, max: 50000, count: 8 },
    ]);
    expect(result.totalWithSalary).toBe(23);
  });

  // ── Search ────────────────────────────────────────────────────────

  it("search.query maps Modal response to SearchResult[]", async () => {
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          results: [
            {
              id: 42,
              title: "Python Developer",
              company_name: "TechCo",
              description_plain: "Great job",
              location_city: "London",
              location_region: "Greater London",
              location_type: "onsite",
              salary_annual_min: 40000,
              salary_annual_max: 60000,
              salary_predicted_min: null,
              salary_predicted_max: null,
              salary_is_predicted: false,
              employment_type: ["full-time"],
              seniority_level: "mid",
              category: "technology",
              date_posted: "2026-03-01",
              source_url: "https://example.com/job/42",
              rrf_score: 0.85,
              rerank_score: 0.92,
              embedding: [0.1, 0.2, 0.3], // should be stripped
            },
          ],
          total: 1,
          latency_ms: 150,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    // Set MODAL_SEARCH_URL for this test
    const originalUrl = process.env.MODAL_SEARCH_URL;
    process.env.MODAL_SEARCH_URL = "https://modal.test/search";

    // Re-import to pick up env change
    vi.resetModules();
    vi.mock("@/lib/supabase/server", () => ({
      createClient: vi.fn(async () => ({
        from: mockSupabaseFrom,
      })),
    }));
    vi.mock("@/lib/supabase/admin", () => ({
      createAdminClient: () => ({
        from: mockAdminFrom,
      }),
    }));
    const { appRouter: freshRouter } = await import("@/server/routers");
    const freshCaller = freshRouter.createCaller({});

    const result = await freshCaller.search.query({ q: "python developer" });

    expect(result.results).toHaveLength(1);
    expect(result.results[0].title).toBe("Python Developer");
    expect(result.results[0].rrf_score).toBe(0.85);
    expect(result.results[0].rerank_score).toBe(0.92);
    // embedding should NOT be present
    expect("embedding" in result.results[0]).toBe(false);
    expect(result.total).toBe(1);
    expect(result.latencyMs).toBe(150);

    process.env.MODAL_SEARCH_URL = originalUrl;
    mockFetch.mockRestore();
  });

  it("search.query returns empty when MODAL_SEARCH_URL is not set", async () => {
    const result = await caller.search.query({ q: "developer" });
    expect(result.results).toEqual([]);
    expect(result.total).toBe(0);
  });

  it("search.query validates input - rejects empty query", async () => {
    await expect(caller.search.query({ q: "" })).rejects.toThrow();
  });

  it("search.query validates input - rejects oversized query", async () => {
    await expect(
      caller.search.query({ q: "a".repeat(501) }),
    ).rejects.toThrow();
  });

  // ── Job ───────────────────────────────────────────────────────────

  it("job.byId returns null for missing job", async () => {
    const mockSingle = vi.fn().mockResolvedValue({
      data: null,
      error: { message: "not found", code: "PGRST116" },
    });
    const mockEqStatus = vi.fn().mockReturnValue({ single: mockSingle });
    const mockEqId = vi.fn().mockReturnValue({ eq: mockEqStatus });

    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: mockEqId,
      }),
    });

    const result = await caller.job.byId({ id: 99999 });
    expect(result).toBeNull();
  });

  it("job.byId returns JobDetail for existing job", async () => {
    const mockSingle = vi.fn().mockResolvedValue({
      data: {
        id: 1,
        title: "Python Developer",
        company_name: "TechCo",
        description: "<p>Great job</p>",
        description_plain: "Great job",
        location_raw: "London",
        location_city: "London",
        location_region: "Greater London",
        location_postcode: "EC1A",
        location_type: "onsite",
        salary_annual_min: 40000,
        salary_annual_max: 60000,
        salary_predicted_min: null,
        salary_predicted_max: null,
        salary_is_predicted: false,
        salary_raw: "40000-60000",
        salary_currency: "GBP",
        salary_period: "annual",
        salary_confidence: null,
        employment_type: ["full-time"],
        seniority_level: "mid",
        category: "technology",
        visa_sponsorship: null,
        date_posted: "2026-03-01",
        date_expires: null,
        date_crawled: "2026-03-01",
        source_url: "https://example.com/job/1",
        companies: {
          name: "TechCo Ltd",
          sic_codes: ["62012"],
          company_status: "active",
          date_of_creation: "2020-01-01",
          website: "https://techco.com",
        },
        job_skills: [
          {
            confidence: 0.95,
            is_required: true,
            skills: {
              name: "Python",
              esco_uri: "http://data.europa.eu/esco/skill/python",
              skill_type: "knowledge",
            },
          },
          {
            confidence: 0.8,
            is_required: false,
            skills: {
              name: "Django",
              esco_uri: null,
              skill_type: "knowledge",
            },
          },
        ],
      },
      error: null,
    });
    const mockEqStatus = vi.fn().mockReturnValue({ single: mockSingle });
    const mockEqId = vi.fn().mockReturnValue({ eq: mockEqStatus });

    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: mockEqId,
      }),
    });

    const result = await caller.job.byId({ id: 1 });

    expect(result).not.toBeNull();
    expect(result!.title).toBe("Python Developer");
    expect(result!.company).toEqual({
      name: "TechCo Ltd",
      sic_codes: ["62012"],
      company_status: "active",
      date_of_creation: "2020-01-01",
      website: "https://techco.com",
    });
    expect(result!.skills).toHaveLength(2);
    expect(result!.skills[0].name).toBe("Python");
    expect(result!.skills[0].is_required).toBe(true);
    expect(result!.skills[1].name).toBe("Django");
    expect(result!.skills[1].is_required).toBe(false);
  });

  // ── Related ───────────────────────────────────────────────────────

  it("search.related returns empty for missing source job", async () => {
    const mockSingle = vi.fn().mockResolvedValue({
      data: null,
      error: { message: "not found" },
    });
    const mockEqStatus = vi.fn().mockReturnValue({ single: mockSingle });
    const mockEqId = vi.fn().mockReturnValue({ eq: mockEqStatus });

    mockSupabaseFrom.mockReturnValue({
      select: vi.fn().mockReturnValue({
        eq: mockEqId,
      }),
    });

    const result = await caller.search.related({ jobId: 99999 });
    expect(result.results).toEqual([]);
  });
});
