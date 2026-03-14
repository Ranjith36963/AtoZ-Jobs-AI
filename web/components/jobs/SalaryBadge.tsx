"use client";

import { AIDisclosure } from "@/components/ui/AIDisclosure";

interface SalaryBadgeProps {
  salaryAnnualMin: number | null;
  salaryAnnualMax: number | null;
  salaryPredictedMin: number | null;
  salaryPredictedMax: number | null;
  salaryIsPredicted: boolean;
}

function formatSalary(value: number): string {
  if (value >= 1000) {
    return `£${Math.round(value / 1000)}k`;
  }
  return `£${value.toLocaleString("en-GB")}`;
}

function formatRange(min: number, max: number | null): string {
  if (max && max !== min) {
    return `${formatSalary(min)}\u2013${formatSalary(max)}`;
  }
  return formatSalary(min);
}

export function SalaryBadge({
  salaryAnnualMin,
  salaryAnnualMax,
  salaryPredictedMin,
  salaryPredictedMax,
  salaryIsPredicted,
}: SalaryBadgeProps) {
  // Green: real salary data
  if (salaryAnnualMin && !salaryIsPredicted) {
    return (
      <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-sm font-medium text-green-800">
        {formatRange(salaryAnnualMin, salaryAnnualMax)}
      </span>
    );
  }

  // Amber: predicted salary
  if (salaryPredictedMin && salaryIsPredicted) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span
          className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-sm font-medium text-amber-800"
          title="Salary estimated by AI model based on similar roles"
        >
          ~{formatRange(salaryPredictedMin, salaryPredictedMax)} (est.)
        </span>
        <AIDisclosure variant="inline" />
      </span>
    );
  }

  // Grey: no salary info
  return (
    <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-sm font-medium text-gray-600">
      Salary not disclosed
    </span>
  );
}
