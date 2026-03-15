"use client";

import Link from "next/link";
import { trpc } from "@/lib/trpc/client";
import { SalaryBadge } from "./SalaryBadge";

interface RelatedJobsProps {
  jobId: number;
}

export function RelatedJobs({ jobId }: RelatedJobsProps) {
  const { data, isLoading } = trpc.search.related.useQuery({
    jobId,
    limit: 5,
  });

  if (isLoading) {
    return (
      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-gray-900">Similar Jobs</h3>
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            aria-hidden="true"
            className="rounded-md border border-gray-100 p-3 motion-safe:animate-pulse"
          >
            <div className="h-4 w-2/3 rounded bg-gray-200" />
            <div className="mt-1.5 h-3 w-1/3 rounded bg-gray-200" />
          </div>
        ))}
      </div>
    );
  }

  if (!data || data.results.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-gray-900">Similar Jobs</h3>
      {data.results.map((job) => (
        <Link
          key={job.id}
          href={`/jobs/${job.id}`}
          className="block rounded-md border border-gray-100 p-3 transition-colors hover:bg-gray-50"
        >
          <p className="font-medium text-gray-900">{job.title}</p>
          <p className="mt-0.5 text-sm text-gray-500">{job.company_name}</p>
          <div className="mt-1">
            <SalaryBadge
              salaryAnnualMin={job.salary_annual_min}
              salaryAnnualMax={job.salary_annual_max}
              salaryPredictedMin={job.salary_predicted_min}
              salaryPredictedMax={job.salary_predicted_max}
              salaryIsPredicted={job.salary_is_predicted}
            />
          </div>
        </Link>
      ))}
    </div>
  );
}
