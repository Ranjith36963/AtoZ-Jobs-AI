import { z } from "zod";
import { createHash } from "crypto";
import { publicProcedure, router } from "../trpc";
import { createAdminClient } from "@/lib/supabase/admin";
import { createClient } from "@/lib/supabase/server";
import type { SearchResult } from "@/types";

const MODAL_SEARCH_URL = process.env.MODAL_SEARCH_URL ?? "";
const MODAL_SEARCH_TIMEOUT_MS = 10_000;

const searchInputSchema = z.object({
  q: z.string().min(1).max(500),
  lat: z.number().optional(),
  lng: z.number().optional(),
  radius: z.number().min(1).max(200).default(25),
  minSalary: z.number().optional(),
  maxSalary: z.number().optional(),
  workType: z.enum(["remote", "hybrid", "onsite"]).optional(),
  category: z.string().optional(),
  seniority: z.string().optional(),
  skills: z.array(z.string()).optional(),
  datePosted: z.enum(["24h", "7d", "30d"]).optional(),
  excludeDuplicates: z.boolean().default(true),
  page: z.number().min(1).default(1),
  pageSize: z.number().min(1).max(50).default(20),
});

interface ModalSearchResponse {
  results: Array<Record<string, unknown>>;
  total: number;
  latency_ms: number;
}

interface JobRow {
  id: number;
  title: string;
  company_name: string;
  description_plain: string | null;
  location_city: string | null;
  location_region: string | null;
  location_type: string | null;
  salary_annual_min: number | null;
  salary_annual_max: number | null;
  salary_predicted_min: number | null;
  salary_predicted_max: number | null;
  salary_is_predicted: boolean | null;
  employment_type: string[] | null;
  seniority_level: string | null;
  category: string | null;
  date_posted: string;
  source_url: string;
}

function mapToSearchResult(raw: Record<string, unknown>): SearchResult {
  return {
    id: raw.id as number,
    title: raw.title as string,
    company_name: raw.company_name as string,
    description_plain: (raw.description_plain as string | null) ?? null,
    location_city: (raw.location_city as string | null) ?? null,
    location_region: (raw.location_region as string | null) ?? null,
    location_type: (raw.location_type as string | null) ?? null,
    salary_annual_min: (raw.salary_annual_min as number | null) ?? null,
    salary_annual_max: (raw.salary_annual_max as number | null) ?? null,
    salary_predicted_min: (raw.salary_predicted_min as number | null) ?? null,
    salary_predicted_max: (raw.salary_predicted_max as number | null) ?? null,
    salary_is_predicted: (raw.salary_is_predicted as boolean) ?? false,
    employment_type: (raw.employment_type as string[]) ?? [],
    seniority_level: (raw.seniority_level as string | null) ?? null,
    category: (raw.category as string | null) ?? null,
    date_posted: raw.date_posted as string,
    source_url: raw.source_url as string,
    rrf_score: (raw.rrf_score as number) ?? 0,
    rerank_score: (raw.rerank_score as number) ?? undefined,
  };
}

function hashQuery(q: string): string {
  return createHash("sha256").update(q).digest("hex");
}

export const searchRouter = router({
  query: publicProcedure.input(searchInputSchema).query(async ({ input }) => {
    if (!MODAL_SEARCH_URL) {
      return {
        results: [] as SearchResult[],
        total: 0,
        page: input.page,
        pageSize: input.pageSize,
        latencyMs: 0,
      };
    }

    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      MODAL_SEARCH_TIMEOUT_MS,
    );

    try {
      const response = await fetch(MODAL_SEARCH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: input.q,
          user_id: null,
          filters: {
            search_lat: input.lat ?? null,
            search_lng: input.lng ?? null,
            radius_miles: input.radius,
            include_remote: true,
            min_salary: input.minSalary ?? null,
            max_salary: input.maxSalary ?? null,
            work_type_filter: input.workType ?? null,
            category_filter: input.category ?? null,
            seniority_filter: input.seniority ?? null,
            skill_filters: input.skills ?? null,
            exclude_duplicates: input.excludeDuplicates,
            date_posted_after: input.datePosted ?? null,
          },
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Modal search failed: ${response.status}`);
      }

      const data = (await response.json()) as ModalSearchResponse;

      // Strip embedding field, map to SearchResult[]
      const results = data.results.map((r) => {
        const { embedding: _, ...rest } = r;
        void _;
        return mapToSearchResult(rest);
      });

      // Paginate results (Modal returns all matches, we slice for page)
      const start = (input.page - 1) * input.pageSize;
      const paginatedResults = results.slice(start, start + input.pageSize);

      // Fire-and-forget: audit log
      logSearchAudit(input.q, data.total, paginatedResults[0]?.title).catch(
        () => {
          /* swallow audit errors */
        },
      );

      return {
        results: paginatedResults,
        total: data.total,
        page: input.page,
        pageSize: input.pageSize,
        latencyMs: data.latency_ms,
      };
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return {
          results: [] as SearchResult[],
          total: 0,
          page: input.page,
          pageSize: input.pageSize,
          latencyMs: MODAL_SEARCH_TIMEOUT_MS,
          error: "Search timed out. Please try again.",
        };
      }
      throw err;
    } finally {
      clearTimeout(timeout);
    }
  }),

  related: publicProcedure
    .input(
      z.object({
        jobId: z.number(),
        limit: z.number().min(1).max(10).default(5),
      }),
    )
    .query(async ({ input }) => {
      const supabase = await createClient();

      const { data: rawSourceJob } = await supabase
        .from("jobs")
        .select("category, company_name")
        .eq("id", input.jobId)
        .eq("status", "ready")
        .single();

      const sourceJob = rawSourceJob as unknown as { category: string | null; company_name: string } | null;

      if (!sourceJob) {
        return { results: [] as SearchResult[] };
      }

      const { data: rawData } = await supabase
        .from("jobs")
        .select(
          "id, title, company_name, description_plain, location_city, location_region, location_type, salary_annual_min, salary_annual_max, salary_predicted_min, salary_predicted_max, salary_is_predicted, employment_type, seniority_level, category, date_posted, source_url",
        )
        .eq("status", "ready")
        .eq("category", sourceJob.category ?? "")
        .neq("id", input.jobId)
        .order("date_posted", { ascending: false })
        .limit(input.limit);

      const data = (rawData ?? []) as unknown as JobRow[];

      const results: SearchResult[] = (data ?? []).map((row) => ({
        id: row.id,
        title: row.title,
        company_name: row.company_name,
        description_plain: row.description_plain,
        location_city: row.location_city,
        location_region: row.location_region,
        location_type: row.location_type,
        salary_annual_min: row.salary_annual_min,
        salary_annual_max: row.salary_annual_max,
        salary_predicted_min: row.salary_predicted_min,
        salary_predicted_max: row.salary_predicted_max,
        salary_is_predicted: row.salary_is_predicted ?? false,
        employment_type: row.employment_type ?? [],
        seniority_level: row.seniority_level,
        category: row.category,
        date_posted: row.date_posted,
        source_url: row.source_url,
        rrf_score: 0,
      }));

      return { results };
    }),
});

async function logSearchAudit(
  query: string,
  total: number,
  topTitle?: string,
): Promise<void> {
  try {
    const admin = createAdminClient();
    // Use rpc-style insert to avoid strict type inference issues with hand-crafted DB types
    const insertData = {
      decision_type: "search_ranking",
      model_provider: "gemini+cross_encoder",
      model_version: "embedding-001+ms-marco-MiniLM-L-6-v2",
      input_hash: hashQuery(query),
      input_summary: `query: ${query}`,
      output_summary: `returned ${total} results${topTitle ? `, top: ${topTitle}` : ""}`,
      cost_usd: 0.0001,
    };
    await (admin.from("ai_decision_audit_log") as unknown as { insert: (data: typeof insertData) => Promise<{ error: unknown }> }).insert(insertData);
  } catch {
    // Audit logging should never break search
  }
}
