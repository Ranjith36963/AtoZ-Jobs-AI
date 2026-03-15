"use client";

import { useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export function SearchInput() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [value, setValue] = useState(searchParams.get("q") ?? "");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = value.trim();
      if (!trimmed) return;

      const params = new URLSearchParams(searchParams.toString());
      params.set("q", trimmed);
      params.delete("page"); // Reset page on new search
      router.push(`/search?${params.toString()}`);
    },
    [value, searchParams, router],
  );

  return (
    <form onSubmit={handleSubmit} role="search" className="flex w-full gap-2">
      <label htmlFor="search-input" className="sr-only">
        Job search
      </label>
      <div className="relative flex-1">
        <svg className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          id="search-input"
          type="search"
          aria-label="Job search"
          placeholder="Search jobs, skills, or companies..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="w-full rounded-lg border border-gray-300 py-2.5 pl-9 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
      <button
        type="submit"
        className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Search
      </button>
    </form>
  );
}
