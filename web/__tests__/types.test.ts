import { describe, it, expect } from "vitest";
import type { Database } from "@/types/database";
import type { SearchResult, FacetCounts } from "@/types";

describe("Database types", () => {
  it("Database type includes all required tables", () => {
    // Type-level checks — if this compiles, the types are correct
    type Tables = keyof Database["public"]["Tables"];
    const tables: Tables[] = [
      "sources",
      "companies",
      "jobs",
      "skills",
      "job_skills",
      "esco_skills",
      "user_profiles",
      "ai_decision_audit_log",
    ];
    expect(tables).toHaveLength(8);
  });

  it("jobs table has all expected columns", () => {
    type JobRow = Database["public"]["Tables"]["jobs"]["Row"];
    // Verify key columns exist at type level
    const sampleJob: Partial<JobRow> = {
      id: 1,
      title: "Developer",
      company_name: "TechCo",
      salary_annual_min: 30000,
      salary_predicted_min: 32000,
      embedding: null,
      is_duplicate: false,
      category_raw: "IT",
      contract_type: "permanent",
    };
    expect(sampleJob.id).toBe(1);
  });

  it("ai_decision_audit_log has compliance columns", () => {
    type AuditRow =
      Database["public"]["Tables"]["ai_decision_audit_log"]["Row"];
    const sample: Partial<AuditRow> = {
      decision_type: "search_ranking",
      model_provider: "gemini",
      model_version: "gemini-embedding-001",
      input_hash: "abc123",
      output_summary: "returned 20 results",
      token_count: 50,
      cost_usd: 0.001,
      requires_review: false,
    };
    expect(sample.decision_type).toBe("search_ranking");
  });

  it("SearchResult type matches search_jobs_v2 output", () => {
    const result: SearchResult = {
      id: 1,
      title: "Python Developer",
      company_name: "TechCo",
      description_plain: "A great job",
      location_city: "London",
      location_region: "Greater London",
      location_type: "onsite",
      salary_annual_min: 40000,
      salary_annual_max: 60000,
      salary_predicted_min: null,
      salary_predicted_max: null,
      salary_is_predicted: false,
      employment_type: ["full-time"],
      seniority_level: "mid",
      category: "technology",
      date_posted: "2026-03-01T00:00:00Z",
      source_url: "https://example.com/job/1",
      rrf_score: 0.85,
    };
    expect(result.title).toBe("Python Developer");
  });

  it("FacetCounts has all 4 facet types", () => {
    const facets: FacetCounts = {
      categories: [{ value: "technology", count: 10 }],
      workTypes: [{ value: "remote", count: 5 }],
      seniorities: [{ value: "mid", count: 8 }],
      employmentTypes: [{ value: "full-time", count: 12 }],
    };
    expect(Object.keys(facets)).toHaveLength(4);
  });
});
