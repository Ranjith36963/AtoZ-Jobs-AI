import { createClient } from "@/lib/supabase/server";

/**
 * HNSW index tuning parameters for pgvector search.
 * ef_search=100 improves recall over the default 40.
 * iterative_scan=relaxed_order enables pgvector 0.8.0+ optimization.
 */
const HNSW_TUNING_STATEMENTS = [
  "SET LOCAL hnsw.ef_search = 100",
  "SET LOCAL hnsw.iterative_scan = relaxed_order",
] as const;

interface RpcClient {
  rpc: (fn: string, params: Record<string, string>) => Promise<{ error: unknown }>;
}

export async function applyHnswTuning(): Promise<void> {
  const supabase = await createClient();
  const client = supabase as unknown as RpcClient;
  for (const stmt of HNSW_TUNING_STATEMENTS) {
    try {
      await client.rpc("exec_sql", { sql: stmt });
    } catch {
      // Tuning is best-effort; search still works without it
    }
  }
}

export { HNSW_TUNING_STATEMENTS };
