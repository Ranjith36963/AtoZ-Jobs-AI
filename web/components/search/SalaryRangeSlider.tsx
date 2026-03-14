"use client";

import { useRouter, useSearchParams } from "next/navigation";

const MIN_SALARY = 0;
const MAX_SALARY = 200000;
const STEP = 5000;

function formatCurrency(value: number): string {
  return `£${value.toLocaleString("en-GB")}`;
}

export function SalaryRangeSlider() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const minValue = Number(searchParams.get("minSalary") ?? MIN_SALARY);
  const maxValue = Number(searchParams.get("maxSalary") ?? MAX_SALARY);

  function handleChange(type: "min" | "max", value: number) {
    const params = new URLSearchParams(searchParams.toString());
    if (type === "min") {
      params.set("minSalary", String(value));
    } else {
      params.set("maxSalary", String(value));
    }
    params.delete("page");
    router.push(`/search?${params.toString()}`);
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>{formatCurrency(minValue)}</span>
        <span>{formatCurrency(maxValue)}</span>
      </div>
      <div className="flex gap-2">
        <input
          type="range"
          role="slider"
          aria-label="Minimum salary"
          aria-valuemin={MIN_SALARY}
          aria-valuemax={MAX_SALARY}
          aria-valuenow={minValue}
          min={MIN_SALARY}
          max={MAX_SALARY}
          step={STEP}
          value={minValue}
          onChange={(e) => handleChange("min", Number(e.target.value))}
          className="w-full"
        />
        <input
          type="range"
          role="slider"
          aria-label="Maximum salary"
          aria-valuemin={MIN_SALARY}
          aria-valuemax={MAX_SALARY}
          aria-valuenow={maxValue}
          min={MIN_SALARY}
          max={MAX_SALARY}
          step={STEP}
          value={maxValue}
          onChange={(e) => handleChange("max", Number(e.target.value))}
          className="w-full"
        />
      </div>
    </div>
  );
}
