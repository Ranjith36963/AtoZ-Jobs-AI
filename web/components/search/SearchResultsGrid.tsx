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
      <div className="py-12 text-center">
        <p className="text-lg text-red-600">
          Something went wrong. Please try again.
        </p>
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
      <div className="py-12 text-center">
        <p className="text-lg text-gray-600">
          No jobs match your search. Try broadening your filters.
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
