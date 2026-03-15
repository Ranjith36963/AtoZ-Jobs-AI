import { JobCard } from "@/components/jobs/JobCard";
import { JobCardSkeleton } from "@/components/jobs/JobCardSkeleton";
import { Pagination } from "@/components/ui/Pagination";
import { AIDisclosure } from "@/components/ui/AIDisclosure";
import type { SearchResult } from "@/types";

interface SearchResultsGridProps {
  results: SearchResult[];
  total: number;
  isLoading: boolean;
  page: number;
  pageSize: number;
  error?: string;
}

export function SearchResultsGrid({
  results,
  total,
  isLoading,
  page,
  pageSize,
  error,
}: SearchResultsGridProps) {
  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-6 py-12 text-center">
        <svg className="mx-auto h-10 w-10 text-red-400" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
        </svg>
        <p className="mt-3 text-lg font-medium text-red-800">
          Something went wrong
        </p>
        <p className="mt-1 text-sm text-red-600">Please try again in a moment.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <JobCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white px-6 py-12 text-center">
        <svg className="mx-auto h-10 w-10 text-gray-300" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <p className="mt-3 text-lg font-medium text-gray-900">
          No jobs found
        </p>
        <p className="mt-1 text-sm text-gray-500">
          Try broadening your search or removing some filters.
        </p>
      </div>
    );
  }

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-600">
          Showing {start}&ndash;{end} of {total.toLocaleString("en-GB")} jobs
        </p>
        <AIDisclosure variant="inline" />
      </div>

      <div className="space-y-3">
        {results.map((result) => (
          <JobCard key={result.id} result={result} />
        ))}
      </div>

      <div className="mt-6">
        <Pagination currentPage={page} totalPages={totalPages} />
      </div>
    </div>
  );
}
