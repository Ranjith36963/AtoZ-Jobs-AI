import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
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
    <main id="main-content" className="flex-1 bg-gray-50">
      {/* Breadcrumb */}
      <div className="border-b border-gray-200 bg-white px-4">
        <nav className="mx-auto max-w-4xl py-3 text-sm text-gray-500" aria-label="Breadcrumb">
          <ol className="flex items-center gap-1.5">
            <li><Link href="/" className="hover:text-gray-700">Home</Link></li>
            <li aria-hidden="true">/</li>
            <li><Link href="/search" className="hover:text-gray-700">Search</Link></li>
            <li aria-hidden="true">/</li>
            <li className="truncate text-gray-900">{job.title}</li>
          </ol>
        </nav>
      </div>

      <div className="mx-auto max-w-4xl px-4 py-8">
        {/* Job header card */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          <header>
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">{job.title}</h1>
            <p className="mt-1.5 text-lg font-medium text-gray-600">{job.company_name}</p>
          </header>

          {/* Salary */}
          <div className="mt-4">
            <SalaryBadge
              salaryAnnualMin={job.salary_annual_min}
              salaryAnnualMax={job.salary_annual_max}
              salaryPredictedMin={job.salary_predicted_min}
              salaryPredictedMax={job.salary_predicted_max}
              salaryIsPredicted={job.salary_is_predicted}
            />
          </div>

          {/* Location */}
          {(job.location_city || job.location_region) && (
            <div className="mt-3 flex items-center gap-1.5 text-sm text-gray-600">
              <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
              </svg>
              {[job.location_city, job.location_region, job.location_postcode]
                .filter(Boolean)
                .join(", ")}
            </div>
          )}

          {/* Tags */}
          <div className="mt-4 flex flex-wrap gap-2">
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

          {/* Apply button - prominent position */}
          <div className="mt-6">
            <ApplyButton sourceUrl={job.source_url} jobTitle={job.title} />
          </div>
        </div>

        {/* Company Info */}
        <div className="mt-6">
          <CompanyInfo company={job.company} />
        </div>

        {/* Match Explanation */}
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

        {/* Description */}
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
          <h2 className="text-xl font-semibold text-gray-900">
            Job Description
          </h2>
          {job.description ? (
            <div
              className="prose mt-4 max-w-none text-gray-700"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(job.description),
              }}
            />
          ) : (
            <div className="prose mt-4 max-w-none text-gray-700">
              {job.description_plain}
            </div>
          )}
        </div>

        {/* Skills */}
        {job.skills.length > 0 && (
          <div className="mt-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
            <h2 className="text-xl font-semibold text-gray-900">
              Required Skills
            </h2>
            <div className="mt-4">
              <SkillsPills skills={job.skills} maxVisible={20} />
            </div>
          </div>
        )}

        {/* Related Jobs */}
        <div className="mt-6">
          <RelatedJobs jobId={job.id} />
        </div>

        {/* JSON-LD structured data */}
        <JobPostingJsonLd job={job} />

        {/* Meta info */}
        <div className="mt-8 text-center text-xs text-gray-400">
          <p>Posted: {new Date(job.date_posted).toLocaleDateString("en-GB")}</p>
          {job.date_expires && (
            <p>
              Expires:{" "}
              {new Date(job.date_expires).toLocaleDateString("en-GB")}
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
