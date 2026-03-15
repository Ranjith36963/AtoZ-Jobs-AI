import { z } from "zod";
import { publicProcedure, router } from "../trpc";
import { createClient } from "@/lib/supabase/server";
import type { JobDetail } from "@/types";

interface JobWithJoins {
  id: number;
  title: string;
  company_name: string;
  description: string;
  description_plain: string | null;
  location_raw: string | null;
  location_city: string | null;
  location_region: string | null;
  location_postcode: string | null;
  location_type: string | null;
  salary_annual_min: number | null;
  salary_annual_max: number | null;
  salary_predicted_min: number | null;
  salary_predicted_max: number | null;
  salary_is_predicted: boolean | null;
  salary_raw: string | null;
  salary_currency: string | null;
  salary_period: string | null;
  salary_confidence: number | null;
  employment_type: string[] | null;
  seniority_level: string | null;
  category: string | null;
  visa_sponsorship: string | null;
  date_posted: string;
  date_expires: string | null;
  date_crawled: string | null;
  source_url: string;
  companies: {
    name: string;
    sic_codes: string[] | null;
    company_status: string | null;
    date_of_creation: string | null;
    website: string | null;
  } | null;
  job_skills: Array<{
    confidence: number | null;
    is_required: boolean | null;
    skills: {
      name: string;
      esco_uri: string | null;
      skill_type: string | null;
    } | null;
  }>;
}

export const jobRouter = router({
  byId: publicProcedure
    .input(z.object({ id: z.number() }))
    .query(async ({ input }): Promise<JobDetail | null> => {
      const supabase = await createClient();

      const { data: rawData, error } = await supabase
        .from("jobs")
        .select("*, companies(*), job_skills(*, skills(*))")
        .eq("id", input.id)
        .eq("status", "ready")
        .single();

      if (error || !rawData) {
        return null;
      }

      // Cast to our expected shape (supabase-js can't infer join types from hand-crafted DB types)
      const data = rawData as unknown as JobWithJoins;

      const company = data.companies
        ? {
            name: data.companies.name,
            sic_codes: data.companies.sic_codes ?? null,
            company_status: data.companies.company_status ?? null,
            date_of_creation: data.companies.date_of_creation ?? null,
            website: data.companies.website ?? null,
          }
        : null;

      const skills = (data.job_skills ?? []).map((js) => ({
        name: js.skills?.name ?? "",
        esco_uri: js.skills?.esco_uri ?? null,
        skill_type: js.skills?.skill_type ?? null,
        confidence: js.confidence ?? null,
        is_required: js.is_required ?? false,
      }));

      return {
        id: data.id,
        title: data.title,
        company_name: data.company_name,
        description: data.description,
        description_plain: data.description_plain,
        location_raw: data.location_raw,
        location_city: data.location_city,
        location_region: data.location_region,
        location_postcode: data.location_postcode,
        location_type: data.location_type,
        location_lat: null,
        location_lng: null,
        salary_annual_min: data.salary_annual_min,
        salary_annual_max: data.salary_annual_max,
        salary_predicted_min: data.salary_predicted_min,
        salary_predicted_max: data.salary_predicted_max,
        salary_is_predicted: data.salary_is_predicted ?? false,
        salary_raw: data.salary_raw,
        salary_currency: data.salary_currency ?? "GBP",
        salary_period: data.salary_period ?? "annual",
        salary_confidence: data.salary_confidence,
        employment_type: data.employment_type ?? [],
        seniority_level: data.seniority_level,
        category: data.category,
        visa_sponsorship: data.visa_sponsorship,
        date_posted: data.date_posted,
        date_expires: data.date_expires,
        date_crawled: data.date_crawled ?? "",
        source_url: data.source_url,
        rrf_score: 0,
        company,
        skills,
      };
    }),
});
