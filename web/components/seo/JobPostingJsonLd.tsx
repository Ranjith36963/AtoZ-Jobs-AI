import type { JobDetail } from "@/types";

interface JobPostingJsonLdProps {
  job: JobDetail;
}

export function JobPostingJsonLd({ job }: JobPostingJsonLdProps) {
  const jsonLd: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: job.title,
    description: job.description_plain ?? job.description,
    datePosted: job.date_posted,
    employmentType: job.employment_type.map((t) => t.toUpperCase()),
    directApply: false,
  };

  if (job.date_expires) {
    jsonLd.validThrough = job.date_expires;
  }

  if (job.company_name) {
    jsonLd.hiringOrganization = {
      "@type": "Organization",
      name: job.company_name,
      ...(job.company?.website ? { sameAs: job.company.website } : {}),
    };
  }

  if (job.location_city) {
    jsonLd.jobLocation = {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressLocality: job.location_city,
        ...(job.location_region
          ? { addressRegion: job.location_region }
          : {}),
        ...(job.location_postcode
          ? { postalCode: job.location_postcode }
          : {}),
        addressCountry: "GB",
      },
    };
  }

  if (job.salary_annual_min) {
    jsonLd.baseSalary = {
      "@type": "MonetaryAmount",
      currency: job.salary_currency || "GBP",
      value: {
        "@type": "QuantitativeValue",
        minValue: job.salary_annual_min,
        ...(job.salary_annual_max
          ? { maxValue: job.salary_annual_max }
          : {}),
        unitText: "YEAR",
      },
    };
  }

  if (job.skills.length > 0) {
    jsonLd.skills = job.skills.map((s) => s.name);
  }

  if (job.source_url) {
    jsonLd.url = job.source_url;
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
    />
  );
}
