import { publicProcedure, router } from "../trpc";

export const facetsRouter = router({
  counts: publicProcedure.query(async () => {
    // Stub: will be implemented in Stage 2
    // Reads from mv_search_facets materialized view
    return {
      categories: [] as Array<{ value: string; count: number }>,
      workTypes: [] as Array<{ value: string; count: number }>,
      seniorities: [] as Array<{ value: string; count: number }>,
      employmentTypes: [] as Array<{ value: string; count: number }>,
    };
  }),

  salaryHistogram: publicProcedure.query(async () => {
    // Stub: will be implemented in Stage 2
    // Reads from mv_salary_histogram materialized view
    return {
      buckets: [] as Array<{ min: number | null; max: number | null; count: number }>,
      totalWithSalary: 0,
      totalWithout: 0,
    };
  }),
});
