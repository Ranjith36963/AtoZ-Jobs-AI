import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock budget guard
const mockIsLLMBudgetExhausted = vi.fn();
vi.mock("@/lib/llm/budget-guard", () => ({
  isLLMBudgetExhausted: () => mockIsLLMBudgetExhausted(),
}));

// Mock admin client
vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: () => ({
    from: () => ({
      insert: vi.fn().mockResolvedValue({ error: null }),
    }),
  }),
}));

// Mock AI SDK
vi.mock("ai", () => ({
  streamText: vi.fn(() => ({
    toTextStreamResponse: () =>
      new Response("Streamed response", { status: 200 }),
  })),
}));

vi.mock("@ai-sdk/openai", () => ({
  createOpenAI: () => () => "mock-model",
}));

import { POST } from "@/app/api/explain/route";

describe("/api/explain route", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.OPENAI_API_KEY = "test-key";
  });

  it("returns 400 on missing fields", async () => {
    const request = new Request("http://localhost/api/explain", {
      method: "POST",
      body: JSON.stringify({ query: "developer" }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);
    expect(response.status).toBe(400);
    const data = await response.json();
    expect(data.error).toBe("Missing required fields");
  });

  it("returns 400 on invalid JSON", async () => {
    const request = new Request("http://localhost/api/explain", {
      method: "POST",
      body: "not json",
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);
    expect(response.status).toBe(400);
  });

  it("returns fallback when budget exhausted", async () => {
    mockIsLLMBudgetExhausted.mockResolvedValue(true);

    const request = new Request("http://localhost/api/explain", {
      method: "POST",
      body: JSON.stringify({
        query: "python developer",
        job: {
          id: 1,
          title: "Python Developer",
          company_name: "TechCo",
          location_city: "London",
        },
      }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);
    expect(response.status).toBe(200);
    const data = await response.json();
    expect(data.explanation).toContain("matches your search");
  });

  it("streams response when budget is available", async () => {
    mockIsLLMBudgetExhausted.mockResolvedValue(false);

    const request = new Request("http://localhost/api/explain", {
      method: "POST",
      body: JSON.stringify({
        query: "python developer",
        job: {
          id: 1,
          title: "Python Developer",
          company_name: "TechCo",
          location_city: "London",
        },
      }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);
    expect(response.status).toBe(200);
  });
});
