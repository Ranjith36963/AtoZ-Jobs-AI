"use client";

import { useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SalaryRangeSlider } from "./SalaryRangeSlider";
import type { FacetCounts } from "@/types";

interface FilterSidebarProps {
  facets: FacetCounts;
}

const WORK_TYPES = ["remote", "hybrid", "onsite"] as const;
const EMPLOYMENT_TYPES = ["full-time", "part-time", "contract", "permanent"] as const;
const SENIORITIES = ["junior", "mid", "senior", "executive"] as const;
const DATE_OPTIONS = [
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
] as const;

export function FilterSidebar({ facets }: FilterSidebarProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [mobileOpen, setMobileOpen] = useState(false);

  const currentCategory = searchParams.get("category");
  const currentWorkType = searchParams.get("workType");
  const currentSeniority = searchParams.get("seniority");
  const currentDatePosted = searchParams.get("datePosted");

  const activeFilterCount = [
    currentCategory,
    currentWorkType,
    currentSeniority,
    currentDatePosted,
    searchParams.get("minSalary"),
    searchParams.get("maxSalary"),
  ].filter(Boolean).length;

  const updateFilter = useCallback(
    (key: string, value: string | null) => {
      const params = new URLSearchParams(searchParams.toString());
      if (value) {
        params.set(key, value);
      } else {
        params.delete(key);
      }
      params.delete("page");
      router.push(`/search?${params.toString()}`);
    },
    [searchParams, router],
  );

  const resetFilters = useCallback(() => {
    const params = new URLSearchParams();
    const q = searchParams.get("q");
    if (q) params.set("q", q);
    router.push(`/search?${params.toString()}`);
  }, [searchParams, router]);

  const filterContent = (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
        {activeFilterCount > 0 && (
          <button
            onClick={resetFilters}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            Reset all
          </button>
        )}
      </div>

      {/* Category */}
      <fieldset>
        <legend className="text-sm font-medium text-gray-700">Category</legend>
        <div className="mt-2 space-y-1">
          {facets.categories.slice(0, 10).map((cat) => (
            <label key={cat.value} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={currentCategory === cat.value}
                onChange={() =>
                  updateFilter(
                    "category",
                    currentCategory === cat.value ? null : cat.value,
                  )
                }
                className="rounded border-gray-300"
              />
              <span className="text-gray-700">{cat.value}</span>
              <span className="ml-auto text-xs text-gray-400">
                {cat.count}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Work Type */}
      <fieldset>
        <legend className="text-sm font-medium text-gray-700">Work Type</legend>
        <div className="mt-2 space-y-1">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="workType"
              checked={!currentWorkType}
              onChange={() => updateFilter("workType", null)}
              className="border-gray-300"
            />
            <span className="text-gray-700">Any</span>
          </label>
          {WORK_TYPES.map((wt) => (
            <label key={wt} className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="workType"
                checked={currentWorkType === wt}
                onChange={() => updateFilter("workType", wt)}
                className="border-gray-300"
              />
              <span className="capitalize text-gray-700">{wt}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Employment Type */}
      <fieldset>
        <legend className="text-sm font-medium text-gray-700">
          Employment Type
        </legend>
        <div className="mt-2 space-y-1">
          {EMPLOYMENT_TYPES.map((et) => (
            <label key={et} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="rounded border-gray-300"
              />
              <span className="capitalize text-gray-700">{et}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Seniority */}
      <fieldset>
        <legend className="text-sm font-medium text-gray-700">Seniority</legend>
        <div className="mt-2 space-y-1">
          {SENIORITIES.map((s) => (
            <label key={s} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={currentSeniority === s}
                onChange={() =>
                  updateFilter(
                    "seniority",
                    currentSeniority === s ? null : s,
                  )
                }
                className="rounded border-gray-300"
              />
              <span className="capitalize text-gray-700">{s}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Salary Range */}
      <fieldset>
        <legend className="text-sm font-medium text-gray-700">
          Salary Range
        </legend>
        <div className="mt-2">
          <SalaryRangeSlider />
        </div>
      </fieldset>

      {/* Date Posted */}
      <fieldset>
        <legend className="text-sm font-medium text-gray-700">
          Date Posted
        </legend>
        <div className="mt-2 space-y-1">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="datePosted"
              checked={!currentDatePosted}
              onChange={() => updateFilter("datePosted", null)}
              className="border-gray-300"
            />
            <span className="text-gray-700">Any time</span>
          </label>
          {DATE_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2 text-sm">
              <input
                type="radio"
                name="datePosted"
                checked={currentDatePosted === opt.value}
                onChange={() => updateFilter("datePosted", opt.value)}
                className="border-gray-300"
              />
              <span className="text-gray-700">{opt.label}</span>
            </label>
          ))}
        </div>
      </fieldset>
    </div>
  );

  return (
    <>
      {/* Mobile filter button */}
      <div className="lg:hidden">
        <button
          onClick={() => setMobileOpen(true)}
          className="flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700"
        >
          Filters
          {activeFilterCount > 0 && (
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-xs text-white">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* Desktop sidebar */}
      <aside className="hidden lg:block" aria-label="Search filters">
        {filterContent}
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-50 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Search filters"
        >
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 w-full max-w-sm overflow-y-auto bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Filters</h2>
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close filters"
                className="rounded-md p-2 text-gray-400 hover:text-gray-600"
              >
                &times;
              </button>
            </div>
            {filterContent}
            <div className="mt-6">
              <button
                onClick={() => setMobileOpen(false)}
                className="w-full rounded-lg bg-blue-600 py-2.5 text-sm font-medium text-white hover:bg-blue-700"
              >
                Apply filters
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
