"use client";

interface DatePostedFilterProps {
  value: string | null;
  onChange: (value: string | null) => void;
}

const DATE_OPTIONS = [
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
] as const;

export function DatePostedFilter({ value, onChange }: DatePostedFilterProps) {
  return (
    <fieldset>
      <legend className="text-sm font-medium text-gray-700">Date Posted</legend>
      <div className="mt-2 space-y-1">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="radio"
            name="datePosted"
            checked={!value}
            onChange={() => onChange(null)}
            className="border-gray-300"
          />
          <span className="text-gray-700">Any time</span>
        </label>
        {DATE_OPTIONS.map((opt) => (
          <label key={opt.value} className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              name="datePosted"
              checked={value === opt.value}
              onChange={() => onChange(opt.value)}
              className="border-gray-300"
            />
            <span className="text-gray-700">{opt.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
