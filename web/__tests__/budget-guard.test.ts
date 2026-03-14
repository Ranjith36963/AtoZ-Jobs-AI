import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the admin client before importing the module under test
const mockFrom = vi.fn();
const mockSelect = vi.fn();
const mockEq = vi.fn();
const mockGte = vi.fn();

vi.mock("@/lib/supabase/admin", () => ({
  createAdminClient: () => ({
    from: mockFrom,
  }),
}));

import { isLLMBudgetExhausted } from "@/lib/llm/budget-guard";

describe("isLLMBudgetExhausted", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up the chain: from().select().eq().gte()
    mockFrom.mockReturnValue({ select: mockSelect });
    mockSelect.mockReturnValue({ eq: mockEq });
    mockEq.mockReturnValue({ gte: mockGte });
  });

  it("returns false when total cost is under the cap", async () => {
    mockGte.mockResolvedValue({
      data: [
        { cost_usd: 5.0 },
        { cost_usd: 10.0 },
        { cost_usd: 3.0 },
      ],
      error: null,
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(false);
    expect(mockFrom).toHaveBeenCalledWith("ai_decision_audit_log");
  });

  it("returns true when total cost equals the cap ($45)", async () => {
    mockGte.mockResolvedValue({
      data: [
        { cost_usd: 20.0 },
        { cost_usd: 25.0 },
      ],
      error: null,
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(true);
  });

  it("returns true when total cost exceeds the cap", async () => {
    mockGte.mockResolvedValue({
      data: [
        { cost_usd: 30.0 },
        { cost_usd: 20.0 },
      ],
      error: null,
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(true);
  });

  it("returns false when no audit log rows exist (empty data)", async () => {
    mockGte.mockResolvedValue({
      data: [],
      error: null,
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(false);
  });

  it("returns false when data is null (no rows)", async () => {
    mockGte.mockResolvedValue({
      data: null,
      error: null,
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(false);
  });

  it("returns true (fail-safe) when query errors", async () => {
    mockGte.mockResolvedValue({
      data: null,
      error: { message: "connection refused" },
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(true);
  });

  it("handles rows with null cost_usd gracefully", async () => {
    mockGte.mockResolvedValue({
      data: [
        { cost_usd: null },
        { cost_usd: 10.0 },
        { cost_usd: null },
      ],
      error: null,
    });

    const result = await isLLMBudgetExhausted();
    expect(result).toBe(false);
  });
});
