import Link from "next/link";
import { SalaryBadge } from "./SalaryBadge";
import type { SearchResult } from "@/types";

interface JobCardProps {
  result: SearchResult;
}

function relativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return `${Math.floor(diffDays / 30)} months ago`;
}

export function JobCard({ result }: JobCardProps) {
  return (
    <article className="group rounded-xl border border-gray-200 bg-white p-5 transition-all hover:border-blue-200 hover:shadow-md">
      <Link href={`/jobs/${result.id}`} className="block">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-lg font-semibold text-gray-900 group-hover:text-blue-600">
              {result.title}
            </h3>
            <p className="mt-0.5 text-sm font-medium text-gray-600">{result.company_name}</p>
          </div>
          <span className="shrink-0 text-xs text-gray-400">
            {relativeDate(result.date_posted)}
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SalaryBadge
            salaryAnnualMin={result.salary_annual_min}
            salaryAnnualMax={result.salary_annual_max}
            salaryPredictedMin={result.salary_predicted_min}
            salaryPredictedMax={result.salary_predicted_max}
            salaryIsPredicted={result.salary_is_predicted}
          />
          {result.location_city && (
            <span className="inline-flex items-center gap-1 text-sm text-gray-500">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
              </svg>
              {result.location_city}
              {result.location_region ? `, ${result.location_region}` : ""}
            </span>
          )}
          {result.location_type && (
            <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
              {result.location_type}
            </span>
          )}
        </div>

        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {result.category && (
            <span className="inline-flex items-center rounded-md bg-purple-50 px-2 py-0.5 text-xs font-medium text-purple-700">
              {result.category}
            </span>
          )}
          {result.seniority_level && (
            <span className="inline-flex items-center rounded-md bg-teal-50 px-2 py-0.5 text-xs font-medium text-teal-700">
              {result.seniority_level}
            </span>
          )}
          {result.employment_type?.map((et) => (
            <span
              key={et}
              className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"
            >
              {et}
            </span>
          ))}
        </div>

        {result.description_plain && (
          <p className="mt-3 line-clamp-2 text-sm text-gray-500">
            {result.description_plain}
          </p>
        )}
      </Link>
    </article>
  );
}
