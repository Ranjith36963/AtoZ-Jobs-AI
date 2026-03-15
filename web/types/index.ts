export type { Database, Json } from "./database";

/** Result shape from search_jobs_v2() + cross-encoder re-ranking */
export interface SearchResult {
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
  salary_is_predicted: boolean;
  employment_type: string[];
  seniority_level: string | null;
  category: string | null;
  date_posted: string;
  source_url: string;
  rrf_score: number;
  rerank_score?: number;
  explanation?: string;
}

/** Full job detail shape — direct Supabase read + joins */
export interface JobDetail extends SearchResult {
  description: string;
  location_raw: string | null;
  location_postcode: string | null;
  location_lat: number | null;
  location_lng: number | null;
  salary_raw: string | null;
  salary_currency: string;
  salary_period: string;
  salary_confidence: number | null;
  visa_sponsorship: string | null;
  date_expires: string | null;
  date_crawled: string;
  company: {
    name: string;
    sic_codes: string[] | null;
    company_status: string | null;
    date_of_creation: string | null;
    website: string | null;
  } | null;
  skills: Array<{
    name: string;
    esco_uri: string | null;
    skill_type: string | null;
    confidence: number | null;
    is_required: boolean;
  }>;
}

/** Facet counts for the filter sidebar */
export interface FacetCounts {
  categories: Array<{ value: string; count: number }>;
  workTypes: Array<{ value: string; count: number }>;
  seniorities: Array<{ value: string; count: number }>;
  employmentTypes: Array<{ value: string; count: number }>;
}

/** Salary histogram bucket for the range slider */
export interface SalaryBucket {
  min: number | null;
  max: number | null;
  count: number;
}
