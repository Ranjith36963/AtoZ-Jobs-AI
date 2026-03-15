import { createAdminClient } from "@/lib/supabase/admin";

const MONTHLY_SOFT_CAP_USD = 45;

interface AuditCostRow {
  cost_usd: number | null;
}

/**
 * Check if LLM budget for match explanations is exhausted for the current month.
 * Queries ai_decision_audit_log for the sum of cost_usd where decision_type = 'match_explanation'.
 * Returns true if the sum >= $45 (app soft cap).
 */
export async function isLLMBudgetExhausted(): Promise<boolean> {
  const supabase = createAdminClient();

  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();

  const result = await supabase
    .from("ai_decision_audit_log")
    .select("cost_usd")
    .eq("decision_type", "match_explanation")
    .gte("created_at", monthStart);

  const data = result.data as unknown as AuditCostRow[] | null;
  const error = result.error;

  if (error) {
    // If we can't check budget, fail safe — assume exhausted
    console.error("Budget guard query failed:", error.message);
    return true;
  }

  const totalCost = (data ?? []).reduce(
    (sum, row) => sum + (row.cost_usd ?? 0),
    0,
  );

  return totalCost >= MONTHLY_SOFT_CAP_USD;
}
