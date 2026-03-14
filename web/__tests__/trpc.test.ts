import { describe, it, expect } from "vitest";
import { appRouter } from "@/server/routers";

describe("tRPC routers", () => {
  const caller = appRouter.createCaller({});

  it("facets.counts returns empty facet structure", async () => {
    const result = await caller.facets.counts();
    expect(result).toEqual({
      categories: [],
      workTypes: [],
      seniorities: [],
      employmentTypes: [],
    });
  });

  it("facets.salaryHistogram returns empty histogram", async () => {
    const result = await caller.facets.salaryHistogram();
    expect(result).toEqual({
      buckets: [],
      totalWithSalary: 0,
      totalWithout: 0,
    });
  });

  it("search.query returns empty results with correct shape", async () => {
    const result = await caller.search.query({ q: "developer" });
    expect(result).toEqual({
      results: [],
      total: 0,
      page: 1,
      pageSize: 20,
      latencyMs: 0,
    });
  });

  it("search.related returns empty results", async () => {
    const result = await caller.search.related({ jobId: 1 });
    expect(result).toEqual({ results: [] });
  });

  it("job.byId returns null for stub", async () => {
    const result = await caller.job.byId({ id: 1 });
    expect(result).toBeNull();
  });

  it("search.query validates input - rejects empty query", async () => {
    await expect(caller.search.query({ q: "" })).rejects.toThrow();
  });

  it("search.query validates input - rejects oversized query", async () => {
    await expect(
      caller.search.query({ q: "a".repeat(501) }),
    ).rejects.toThrow();
  });
});
