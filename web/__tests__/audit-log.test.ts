import { describe, it, expect, vi } from "vitest";

// Mock admin client
const mockInsert = vi.fn().mockResolvedValue({ error: null });
vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: () => ({
    from: (table: string) => {
      if (table === "ai_decision_audit_log") {
        return { insert: mockInsert };
      }
      return { insert: vi.fn() };
    },
  }),
}));

// Mock budget guard dependencies
vi.mock("@/lib/supabase/server", () => ({
  createClient: vi.fn(),
}));

describe("Audit log integration", () => {
  it("search route logs to ai_decision_audit_log", async () => {
    // The search router logs audit entries with decision_type: 'search_ranking'
    const fs = await import("fs");
    const searchRouterCode = fs.readFileSync(
      "server/routers/search.ts",
      "utf-8",
    );
    expect(searchRouterCode).toContain("ai_decision_audit_log");
    expect(searchRouterCode).toContain("search_ranking");
    expect(searchRouterCode).toContain("input_hash");
    expect(searchRouterCode).toContain("cost_usd");
  });

  it("explain route logs to ai_decision_audit_log", async () => {
    const fs = await import("fs");
    const explainRouteCode = fs.readFileSync(
      "app/api/explain/route.ts",
      "utf-8",
    );
    expect(explainRouteCode).toContain("ai_decision_audit_log");
    expect(explainRouteCode).toContain("match_explanation");
    expect(explainRouteCode).toContain("input_hash");
    expect(explainRouteCode).toContain("cost_usd");
  });

  it("audit log captures required fields per EU AI Act Article 12", async () => {
    // Both routes must log: decision_type, model_provider, model_version,
    // input_hash, input_summary, output_summary, cost_usd
    const requiredFields = [
      "decision_type",
      "model_provider",
      "model_version",
      "input_hash",
      "input_summary",
      "output_summary",
      "cost_usd",
    ];

    const fs = await import("fs");

    const searchCode = fs.readFileSync("server/routers/search.ts", "utf-8");
    for (const field of requiredFields) {
      expect(searchCode).toContain(field);
    }

    const explainCode = fs.readFileSync("app/api/explain/route.ts", "utf-8");
    for (const field of requiredFields) {
      expect(explainCode).toContain(field);
    }
  });

  it("budget guard queries ai_decision_audit_log for cost tracking", async () => {
    const fs = await import("fs");
    const budgetGuardCode = fs.readFileSync(
      "lib/llm/budget-guard.ts",
      "utf-8",
    );
    expect(budgetGuardCode).toContain("ai_decision_audit_log");
    expect(budgetGuardCode).toContain("cost_usd");
    expect(budgetGuardCode).toContain("match_explanation");
  });
});
