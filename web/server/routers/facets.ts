import { publicProcedure, router } from "../trpc";
import { createClient } from "@/lib/supabase/server";
import type { FacetCounts, SalaryBucket } from "@/types";

interface FacetRow {
  facet_type: string;
  facet_value: string | null;
  job_count: number;
}

interface HistogramRow {
  bucket: number | null;
  bucket_min: number | null;
  bucket_max: number | null;
  job_count: number;
}

export const facetsRouter = router({
  counts: publicProcedure.query(async (): Promise<FacetCounts> => {
    const supabase = await createClient();

    const result = await supabase
      .from("mv_search_facets")
      .select("*");

    const data = result.data as unknown as FacetRow[] | null;
    const error = result.error;

    if (error || !data) {
      return {
        categories: [],
        workTypes: [],
        seniorities: [],
        employmentTypes: [],
      };
    }

    const facets: FacetCounts = {
      categories: [],
      workTypes: [],
      seniorities: [],
      employmentTypes: [],
    };

    for (const row of data) {
      const entry = { value: row.facet_value ?? "", count: row.job_count };
      switch (row.facet_type) {
        case "category":
          facets.categories.push(entry);
          break;
        case "work_type":
          facets.workTypes.push(entry);
          break;
        case "seniority":
          facets.seniorities.push(entry);
          break;
        case "employment_type":
          facets.employmentTypes.push(entry);
          break;
      }
    }

    // Sort each group by count descending
    facets.categories.sort((a, b) => b.count - a.count);
    facets.workTypes.sort((a, b) => b.count - a.count);
    facets.seniorities.sort((a, b) => b.count - a.count);
    facets.employmentTypes.sort((a, b) => b.count - a.count);

    return facets;
  }),

  salaryHistogram: publicProcedure.query(async () => {
    const supabase = await createClient();

    const result = await supabase
      .from("mv_salary_histogram")
      .select("*")
      .order("bucket", { ascending: true });

    const data = result.data as unknown as HistogramRow[] | null;
    const error = result.error;

    if (error || !data) {
      return {
        buckets: [] as SalaryBucket[],
        totalWithSalary: 0,
        totalWithout: 0,
      };
    }

    const buckets: SalaryBucket[] = data.map((row) => ({
      min: row.bucket_min,
      max: row.bucket_max,
      count: row.job_count,
    }));

    const totalWithSalary = buckets.reduce((sum, b) => sum + b.count, 0);

    return {
      buckets,
      totalWithSalary,
      totalWithout: 0,
    };
  }),
});
