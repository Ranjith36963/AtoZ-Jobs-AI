"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
}

export function Pagination({ currentPage, totalPages }: PaginationProps) {
  const searchParams = useSearchParams();

  if (totalPages <= 1) return null;

  function buildPageUrl(page: number): string {
    const params = new URLSearchParams(searchParams.toString());
    params.set("page", String(page));
    return `?${params.toString()}`;
  }

  // Show a window of pages around current page
  const windowSize = 2;
  const start = Math.max(1, currentPage - windowSize);
  const end = Math.min(totalPages, currentPage + windowSize);
  const pages: number[] = [];
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  return (
    <nav aria-label="Pagination" className="flex items-center justify-center gap-1">
      {currentPage > 1 && (
        <Link
          href={buildPageUrl(currentPage - 1)}
          className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          aria-label="Previous page"
        >
          Previous
        </Link>
      )}

      {start > 1 && (
        <>
          <Link
            href={buildPageUrl(1)}
            className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            1
          </Link>
          {start > 2 && (
            <span className="px-2 text-gray-400" aria-hidden="true">
              ...
            </span>
          )}
        </>
      )}

      {pages.map((page) => (
        <Link
          key={page}
          href={buildPageUrl(page)}
          aria-current={page === currentPage ? "page" : undefined}
          className={`rounded-md px-3 py-2 text-sm font-medium ${
            page === currentPage
              ? "bg-blue-600 text-white"
              : "text-gray-700 hover:bg-gray-100"
          }`}
        >
          {page}
        </Link>
      ))}

      {end < totalPages && (
        <>
          {end < totalPages - 1 && (
            <span className="px-2 text-gray-400" aria-hidden="true">
              ...
            </span>
          )}
          <Link
            href={buildPageUrl(totalPages)}
            className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            {totalPages}
          </Link>
        </>
      )}

      {currentPage < totalPages && (
        <Link
          href={buildPageUrl(currentPage + 1)}
          className="rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          aria-label="Next page"
        >
          Next
        </Link>
      )}
    </nav>
  );
}
