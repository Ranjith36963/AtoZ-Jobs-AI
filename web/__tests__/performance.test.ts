import { describe, it, expect, vi } from "vitest";

// Mock supabase server client
vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn().mockResolvedValue({
    rpc: vi.fn().mockResolvedValue({ error: null }),
    from: () => ({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({
              data: [{ id: 1 }, { id: 2 }, { id: 3 }],
            }),
          }),
        }),
      }),
    }),
  }),
}));

describe("ISR configuration", () => {
  it("homepage has revalidate = 3600 (1 hour)", async () => {
    const mod = await import("@/app/page");
    expect((mod as Record<string, unknown>).revalidate).toBe(3600);
  });

  it("job detail page has revalidate = 1800 (30 minutes)", async () => {
    const mod = await import("@/app/jobs/[id]/page");
    expect((mod as Record<string, unknown>).revalidate).toBe(1800);
  });

  it("job detail page exports generateStaticParams", async () => {
    const mod = await import("@/app/jobs/[id]/page");
    expect(typeof (mod as Record<string, unknown>).generateStaticParams).toBe(
      "function",
    );
  });

  it("generateStaticParams returns array of id params", async () => {
    const mod = await import("@/app/jobs/[id]/page");
    const params = await (
      mod as { generateStaticParams: () => Promise<Array<{ id: string }>> }
    ).generateStaticParams();
    expect(Array.isArray(params)).toBe(true);
    expect(params[0]).toHaveProperty("id");
    expect(typeof params[0].id).toBe("string");
  });

  it("search page is dynamic (no revalidate export)", async () => {
    const mod = await import("@/app/search/page");
    // Client-side pages are inherently dynamic — no revalidate export
    expect((mod as Record<string, unknown>).revalidate).toBeUndefined();
  });
});

describe("HNSW tuning", () => {
  it("exports tuning statements", async () => {
    const { HNSW_TUNING_STATEMENTS } = await import("@/lib/db/search");
    expect(HNSW_TUNING_STATEMENTS).toContain(
      "SET LOCAL hnsw.ef_search = 100",
    );
    expect(HNSW_TUNING_STATEMENTS).toContain(
      "SET LOCAL hnsw.iterative_scan = relaxed_order",
    );
  });

  it("applyHnswTuning calls rpc for each statement", async () => {
    const { createClient } = await import("@/lib/supabase/server");
    const { applyHnswTuning } = await import("@/lib/db/search");

    await applyHnswTuning();

    const client = await (
      createClient as unknown as () => Promise<{ rpc: ReturnType<typeof vi.fn> }>
    )();
    expect(client.rpc).toHaveBeenCalledWith("exec_sql", {
      sql: "SET LOCAL hnsw.ef_search = 100",
    });
    expect(client.rpc).toHaveBeenCalledWith("exec_sql", {
      sql: "SET LOCAL hnsw.iterative_scan = relaxed_order",
    });
  });
});

describe("Bundle optimization", () => {
  it("job detail page uses LazyMatchExplanation (dynamic wrapper)", async () => {
    const fs = await import("fs");
    // Page imports the lazy wrapper, not MatchExplanation directly
    const pageContent = fs.readFileSync("app/jobs/[id]/page.tsx", "utf-8");
    expect(pageContent).toContain("LazyMatchExplanation");
    expect(pageContent).not.toMatch(
      /^import \{[^}]*\bMatchExplanation\b[^}]*\} from "@\/components\/jobs\/MatchExplanation"/m,
    );

    // The lazy wrapper uses next/dynamic with ssr: false
    const wrapperContent = fs.readFileSync(
      "components/jobs/LazyMatchExplanation.tsx",
      "utf-8",
    );
    expect(wrapperContent).toContain("dynamic(");
    expect(wrapperContent).toContain("ssr: false");
  });

  it("FilterSidebar uses dynamic import for SalaryRangeSlider", async () => {
    const fs = await import("fs");
    const content = fs.readFileSync(
      "components/search/FilterSidebar.tsx",
      "utf-8",
    );
    expect(content).not.toMatch(
      /^import \{[^}]*SalaryRangeSlider[^}]*\} from/m,
    );
    expect(content).toContain("dynamic(");
  });
});

describe("Lighthouse CI config", () => {
  it("lighthouserc.js exists and has correct thresholds", async () => {
    const fs = await import("fs");
    const content = fs.readFileSync("lighthouserc.js", "utf-8");
    expect(content).toContain("categories:performance");
    expect(content).toContain("categories:accessibility");
    expect(content).toContain("0.9"); // performance threshold
    expect(content).toContain("0.95"); // accessibility threshold
  });
});
