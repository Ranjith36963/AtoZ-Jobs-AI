"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

export function HomeSearchBar() {
  const router = useRouter();
  const [value, setValue] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = value.trim();
      if (!trimmed) {
        router.push("/search");
        return;
      }
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    },
    [value, router],
  );

  return (
    <form onSubmit={handleSubmit} role="search" className="flex w-full overflow-hidden rounded-xl bg-white shadow-lg">
      <label htmlFor="home-search-input" className="sr-only">
        Search jobs
      </label>
      <input
        id="home-search-input"
        type="search"
        aria-label="Search jobs"
        placeholder="Job title, skill, or company..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="flex-1 border-0 px-5 py-4 text-base text-gray-900 placeholder:text-gray-400 focus:outline-none"
      />
      <button
        type="submit"
        className="bg-blue-600 px-6 py-4 text-base font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset sm:px-8"
      >
        Search
      </button>
    </form>
  );
}
