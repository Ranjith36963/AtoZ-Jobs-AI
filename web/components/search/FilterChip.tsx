interface FilterChipProps {
  label: string;
  onRemove: () => void;
}

export function FilterChip({ label, onRemove }: FilterChipProps) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-800">
      {label}
      <button
        onClick={onRemove}
        aria-label={`Remove ${label} filter`}
        className="ml-0.5 inline-flex h-4 w-4 items-center justify-center rounded-full text-blue-600 hover:bg-blue-200 hover:text-blue-800"
      >
        &times;
      </button>
    </span>
  );
}
