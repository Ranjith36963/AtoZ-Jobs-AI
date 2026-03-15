import { notFound } from "next/navigation";
import type { Metadata } from "next";
import DOMPurify from "isomorphic-dompurify";
import { createServerCaller } from "@/lib/trpc/server";
import { SalaryBadge } from "@/components/jobs/SalaryBadge";
import { SkillsPills } from "@/components/jobs/SkillsPills";
import { CompanyInfo } from "@/components/jobs/CompanyInfo";
import { ApplyButton } from "@/components/jobs/ApplyButton";
import { LazyMatchExplanation } from "@/components/jobs/LazyMatchExplanation";
import { RelatedJobs } from "@/components/jobs/RelatedJobs";
import { JobPostingJsonLd } from "@/components/seo/JobPostingJsonLd";

export const revalidate = 1800; // ISR: 30 minutes

export async function generateStaticParams() {
  try {
    const { createClient } = await import("@/lib/supabase/server");
    const supabase = await createClient();
    const { data } = await supabase
      .from("jobs")
      .select("id")
      .eq("status", "ready")
      .order("date_posted", { ascending: false })
      .limit(100);

    return (data ?? []).map((row) => ({ id: String((row as { id: number }).id) }));
  } catch {
    return [];
  }
}

interface JobPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ q?: string }>;
}

export async function generateMetadata({
  params,
}: JobPageProps): Promise<Metadata> {
  const { id } = await params;
  const jobId = Number(id);
  if (isNaN(jobId)) return { title: "Job Not Found" };

  const caller = createServerCaller();
  const job = await caller.job.byId({ id: jobId });
  if (!job) return { title: "Job Not Found" };

  return {
    title: `${job.title} at ${job.company_name} | AtoZ Jobs`,
    description:
      job.description_plain?.slice(0, 160) ?? `${job.title} - Apply now`,
    openGraph: {
      title: `${job.title} at ${job.company_name}`,
      description:
        job.description_plain?.slice(0, 160) ?? `${job.title} - Apply now`,
      type: "website",
    },
  };
}

export default async function JobPage({ params, searchParams }: JobPageProps) {
  const { id } = await params;
  const { q } = await searchParams;
  const jobId = Number(id);
  if (isNaN(jobId)) notFound();

  const caller = createServerCaller();
  const job = await caller.job.byId({ id: jobId });
  if (!job) notFound();

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      {/* 1. Title + Company */}
      <header>
        <h1 className="text-3xl font-bold text-gray-900">{job.title}</h1>
        <p className="mt-1 text-lg text-gray-600">{job.company_name}</p>
      </header>

      {/* 2. Salary Badge */}
      <div className="mt-4">
        <SalaryBadge
          salaryAnnualMin={job.salary_annual_min}
          salaryAnnualMax={job.salary_annual_max}
          salaryPredictedMin={job.salary_predicted_min}
          salaryPredictedMax={job.salary_predicted_max}
          salaryIsPredicted={job.salary_is_predicted}
        />
      </div>

      {/* 3. Location */}
      {(job.location_city || job.location_region) && (
        <div className="mt-3 text-sm text-gray-600">
          {[job.location_city, job.location_region, job.location_postcode]
            .filter(Boolean)
            .join(", ")}
        </div>
      )}

      {/* 4. Employment type + seniority */}
      <div className="mt-3 flex flex-wrap gap-2">
        {job.employment_type.map((et) => (
          <span
            key={et}
            className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700"
          >
            {et}
          </span>
        ))}
        {job.seniority_level && (
          <span className="inline-flex items-center rounded-full bg-teal-50 px-2.5 py-0.5 text-xs font-medium text-teal-700">
            {job.seniority_level}
          </span>
        )}
      </div>

      {/* 5. Company Info */}
      <div className="mt-6">
        <CompanyInfo company={job.company} />
      </div>

      {/* 6. Description (sanitized HTML via DOMPurify) */}
      <div className="mt-6">
        <h2 className="text-xl font-semibold text-gray-900">
          Job Description
        </h2>
        {job.description ? (
          <div
            className="prose mt-3 max-w-none text-gray-700"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(job.description),
            }}
          />
        ) : (
          <div className="prose mt-3 max-w-none text-gray-700">
            {job.description_plain}
          </div>
        )}
      </div>

      {/* 7. Skills */}
      {job.skills.length > 0 && (
        <div className="mt-6">
          <h2 className="text-xl font-semibold text-gray-900">
            Required Skills
          </h2>
          <div className="mt-3">
            <SkillsPills skills={job.skills} maxVisible={20} />
          </div>
        </div>
      )}

      {/* 8. Match Explanation (client component, loaded dynamically) */}
      {q && (
        <div className="mt-6">
          <LazyMatchExplanation
            query={q}
            job={{
              id: job.id,
              title: job.title,
              company_name: job.company_name,
              location_city: job.location_city,
            }}
          />
        </div>
      )}

      {/* 9. Related Jobs */}
      <div className="mt-6">
        <RelatedJobs jobId={job.id} />
      </div>

      {/* 10. Apply Button */}
      <div className="mt-8">
        <ApplyButton sourceUrl={job.source_url} jobTitle={job.title} />
      </div>

      {/* JSON-LD structured data */}
      <JobPostingJsonLd job={job} />

      {/* Meta info */}
      <div className="mt-8 border-t border-gray-200 pt-4 text-xs text-gray-400">
        <p>Posted: {new Date(job.date_posted).toLocaleDateString("en-GB")}</p>
        {job.date_expires && (
          <p>
            Expires:{" "}
            {new Date(job.date_expires).toLocaleDateString("en-GB")}
          </p>
        )}
      </div>
    </div>
  );
}

