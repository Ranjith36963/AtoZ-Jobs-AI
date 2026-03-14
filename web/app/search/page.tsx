"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { trpc } from "@/lib/trpc/client";
import { SearchInput } from "@/components/search/SearchInput";
import { RadiusSelector } from "@/components/search/RadiusSelector";
import { LocationAutocomplete } from "@/components/search/LocationAutocomplete";
import { FilterSidebar } from "@/components/search/FilterSidebar";
import { SearchResultsGrid } from "@/components/search/SearchResultsGrid";
import type { FacetCounts } from "@/types";

function SearchPageContent() {
  const searchParams = useSearchParams();

  const q = searchParams.get("q") ?? "";
  const lat = searchParams.get("lat") ? Number(searchParams.get("lat")) : undefined;
  const lng = searchParams.get("lng") ? Number(searchParams.get("lng")) : undefined;
  const radius = Number(searchParams.get("radius") ?? 25);
  const minSalary = searchParams.get("minSalary")
    ? Number(searchParams.get("minSalary"))
    : undefined;
  const maxSalary = searchParams.get("maxSalary")
    ? Number(searchParams.get("maxSalary"))
    : undefined;
  const workType = searchParams.get("workType") as
    | "remote"
    | "hybrid"
    | "onsite"
    | undefined;
  const category = searchParams.get("category") ?? undefined;
  const seniority = searchParams.get("seniority") ?? undefined;
  const datePosted = searchParams.get("datePosted") as
    | "24h"
    | "7d"
    | "30d"
    | undefined;
  const page = Number(searchParams.get("page") ?? 1);

  const searchQuery = trpc.search.query.useQuery(
    {
      q: q || "jobs",
      lat,
      lng,
      radius,
      minSalary,
      maxSalary,
      workType,
      category,
      seniority,
      datePosted,
      page,
    },
    { enabled: true },
  );

  const facetsQuery = trpc.facets.counts.useQuery();

  const emptyFacets: FacetCounts = {
    categories: [],
    workTypes: [],
    seniorities: [],
    employmentTypes: [],
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* Search bar */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex-1">
          <SearchInput />
        </div>
        <div className="flex gap-3">
          <LocationAutocomplete />
          <RadiusSelector />
        </div>
      </div>

      {/* Main content */}
      <div className="flex gap-8">
        {/* Sidebar */}
        <div className="w-full shrink-0 lg:w-1/4">
          <FilterSidebar facets={facetsQuery.data ?? emptyFacets} />
        </div>

        {/* Results */}
        <div className="min-w-0 flex-1">
          <SearchResultsGrid
            results={searchQuery.data?.results ?? []}
            total={searchQuery.data?.total ?? 0}
            isLoading={searchQuery.isLoading}
            page={page}
            pageSize={20}
            error={searchQuery.error?.message}
          />
        </div>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="py-12 text-center text-gray-500">Loading search...</div>
      }
    >
      <SearchPageContent />
    </Suspense>
  );
}
