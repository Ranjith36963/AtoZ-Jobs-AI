"use client";

import { useRouter, useSearchParams } from "next/navigation";

const RADIUS_OPTIONS = [5, 10, 25, 50, 100] as const;

export function RadiusSelector() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentRadius = Number(searchParams.get("radius") ?? 25);

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("radius", e.target.value);
    router.push(`/search?${params.toString()}`);
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="radius-select" className="text-sm text-gray-600">
        Within
      </label>
      <select
        id="radius-select"
        aria-label="Search radius"
        value={currentRadius}
        onChange={handleChange}
        className="rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {RADIUS_OPTIONS.map((radius) => (
          <option key={radius} value={radius}>
            {radius} miles
          </option>
        ))}
      </select>
    </div>
  );
}
