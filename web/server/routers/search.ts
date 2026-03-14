import { z } from "zod";
import { publicProcedure, router } from "../trpc";

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

export const searchRouter = router({
  query: publicProcedure.input(searchInputSchema).query(async ({ input }) => {
    // Stub: will be implemented in Stage 2
    // Calls Modal /search endpoint → search_jobs_v2 → re-rank
    return {
      results: [] as Array<Record<string, unknown>>,
      total: 0,
      page: input.page,
      pageSize: input.pageSize,
      latencyMs: 0,
    };
  }),

  related: publicProcedure
    .input(
      z.object({
        jobId: z.number(),
        limit: z.number().min(1).max(10).default(5),
      }),
    )
    .query(async () => {
      // Stub: will be implemented in Stage 2
      // Direct Supabase: cosine similarity on embedding column
      return {
        results: [] as Array<Record<string, unknown>>,
      };
    }),
});
