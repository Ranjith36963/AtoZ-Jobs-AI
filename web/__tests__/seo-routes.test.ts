import { describe, it, expect, vi } from "vitest";

// Mock supabase server client for sitemap
vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn().mockResolvedValue({
    from: () => ({
      select: vi.fn().mockReturnValue({
        eq: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({
              data: [
                { id: 101, date_posted: "2026-03-10T00:00:00Z" },
                { id: 102, date_posted: "2026-03-09T00:00:00Z" },
              ],
            }),
          }),
        }),
      }),
    }),
  }),
}));

describe("sitemap.xml route", () => {
  it("returns valid XML with correct content type", async () => {
    const { GET } = await import("@/app/sitemap.xml/route");
    const response = await GET();

    expect(response.headers.get("Content-Type")).toBe("application/xml");
    const body = await response.text();
    expect(body).toContain('<?xml version="1.0"');
    expect(body).toContain("<urlset");
  });

  it("includes static pages", async () => {
    const { GET } = await import("@/app/sitemap.xml/route");
    const response = await GET();
    const body = await response.text();

    expect(body).toContain("/search");
    expect(body).toContain("/transparency");
  });

  it("includes job URLs from database", async () => {
    const { GET } = await import("@/app/sitemap.xml/route");
    const response = await GET();
    const body = await response.text();

    expect(body).toContain("/jobs/101");
    expect(body).toContain("/jobs/102");
  });

  it("sets cache headers", async () => {
    const { GET } = await import("@/app/sitemap.xml/route");
    const response = await GET();

    expect(response.headers.get("Cache-Control")).toContain("max-age=3600");
  });
});

describe("robots.txt route", () => {
  it("returns correct content type", async () => {
    const { GET } = await import("@/app/robots.txt/route");
    const response = GET();

    expect(response.headers.get("Content-Type")).toBe("text/plain");
  });

  it("allows crawling of public pages", async () => {
    const { GET } = await import("@/app/robots.txt/route");
    const response = GET();
    const body = await response.text();

    expect(body).toContain("Allow: /");
  });

  it("disallows crawling of API routes", async () => {
    const { GET } = await import("@/app/robots.txt/route");
    const response = GET();
    const body = await response.text();

    expect(body).toContain("Disallow: /api/");
  });

  it("includes sitemap reference", async () => {
    const { GET } = await import("@/app/robots.txt/route");
    const response = GET();
    const body = await response.text();

    expect(body).toContain("Sitemap:");
    expect(body).toContain("/sitemap.xml");
  });
});
