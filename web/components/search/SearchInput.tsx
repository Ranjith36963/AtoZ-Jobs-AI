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
      <input
        id="search-input"
        type="search"
        aria-label="Job search"
        placeholder="Search jobs, skills, or companies..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <button
        type="submit"
        className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        Search
      </button>
    </form>
  );
}
