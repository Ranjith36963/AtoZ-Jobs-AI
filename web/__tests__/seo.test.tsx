import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { JobPostingJsonLd } from "@/components/seo/JobPostingJsonLd";
import type { JobDetail } from "@/types";

const sampleJob: JobDetail = {
  id: 1,
  title: "Python Developer",
  company_name: "TechCo Ltd",
  description: "<p>Great job</p>",
  description_plain: "Great job",
  location_raw: "London",
  location_city: "London",
  location_region: "Greater London",
  location_postcode: "EC1A 1BB",
  location_type: "onsite",
  location_lat: 51.5,
  location_lng: -0.1,
  salary_annual_min: 40000,
  salary_annual_max: 60000,
  salary_predicted_min: null,
  salary_predicted_max: null,
  salary_is_predicted: false,
  salary_raw: "40000-60000",
  salary_currency: "GBP",
  salary_period: "annual",
  salary_confidence: null,
  employment_type: ["full-time"],
  seniority_level: "mid",
  category: "technology",
  visa_sponsorship: null,
  date_posted: "2026-03-01T00:00:00Z",
  date_expires: "2026-04-01T00:00:00Z",
  date_crawled: "2026-03-01",
  source_url: "https://example.com/job/1",
  rrf_score: 0.85,
  company: {
    name: "TechCo Ltd",
    sic_codes: ["62012"],
    company_status: "active",
    date_of_creation: "2020-01-01",
    website: "https://techco.com",
  },
  skills: [
    {
      name: "Python",
      esco_uri: "http://data.europa.eu/esco/skill/python",
      skill_type: "knowledge",
      confidence: 0.95,
      is_required: true,
    },
  ],
};

describe("JobPostingJsonLd", () => {
  it("output contains required schema.org fields", () => {
    const { container } = render(<JobPostingJsonLd job={sampleJob} />);
    const script = container.querySelector(
      'script[type="application/ld+json"]',
    );
    expect(script).not.toBeNull();

    const jsonLd = JSON.parse(script!.textContent ?? "{}");
    expect(jsonLd["@context"]).toBe("https://schema.org");
    expect(jsonLd["@type"]).toBe("JobPosting");
    expect(jsonLd.title).toBe("Python Developer");
    expect(jsonLd.datePosted).toBe("2026-03-01T00:00:00Z");
    expect(jsonLd.validThrough).toBe("2026-04-01T00:00:00Z");
    expect(jsonLd.employmentType).toEqual(["FULL-TIME"]);
    expect(jsonLd.directApply).toBe(false);
    expect(jsonLd.hiringOrganization.name).toBe("TechCo Ltd");
    expect(jsonLd.jobLocation.address.addressLocality).toBe("London");
    expect(jsonLd.baseSalary.value.minValue).toBe(40000);
    expect(jsonLd.skills).toEqual(["Python"]);
  });

  it("handles missing salary gracefully", () => {
    const jobNoSalary = {
      ...sampleJob,
      salary_annual_min: null,
      salary_annual_max: null,
    };
    const { container } = render(<JobPostingJsonLd job={jobNoSalary} />);
    const script = container.querySelector(
      'script[type="application/ld+json"]',
    );
    const jsonLd = JSON.parse(script!.textContent ?? "{}");
    expect(jsonLd.baseSalary).toBeUndefined();
  });

  it("includes company website as sameAs", () => {
    const { container } = render(<JobPostingJsonLd job={sampleJob} />);
    const script = container.querySelector(
      'script[type="application/ld+json"]',
    );
    const jsonLd = JSON.parse(script!.textContent ?? "{}");
    expect(jsonLd.hiringOrganization.sameAs).toBe("https://techco.com");
  });
});
