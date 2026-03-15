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
    <article className="rounded-lg border border-gray-200 p-4 transition-shadow hover:shadow-md">
      <Link href={`/jobs/${result.id}`} className="block">
        <h3 className="text-lg font-semibold text-gray-900 hover:text-blue-600">
          {result.title}
        </h3>
        <p className="mt-1 text-sm text-gray-600">{result.company_name}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <SalaryBadge
            salaryAnnualMin={result.salary_annual_min}
            salaryAnnualMax={result.salary_annual_max}
            salaryPredictedMin={result.salary_predicted_min}
            salaryPredictedMax={result.salary_predicted_max}
            salaryIsPredicted={result.salary_is_predicted}
          />
          {result.location_city && (
            <span className="text-sm text-gray-500">
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
        <div className="mt-2 flex flex-wrap gap-1.5">
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
        </div>
        <p className="mt-2 text-xs text-gray-400">
          {relativeDate(result.date_posted)}
        </p>
      </Link>
    </article>
  );
}
