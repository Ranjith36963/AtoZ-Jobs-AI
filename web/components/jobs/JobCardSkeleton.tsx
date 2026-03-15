export function JobCardSkeleton() {
  return (
    <div
      aria-hidden="true"
      className="rounded-lg border border-gray-200 p-4 motion-safe:animate-pulse"
    >
      <div className="h-5 w-3/4 rounded bg-gray-200" />
      <div className="mt-2 h-4 w-1/3 rounded bg-gray-200" />
      <div className="mt-3 flex gap-2">
        <div className="h-6 w-20 rounded-full bg-gray-200" />
        <div className="h-6 w-24 rounded-full bg-gray-200" />
      </div>
      <div className="mt-3 flex gap-1.5">
        <div className="h-5 w-16 rounded bg-gray-200" />
        <div className="h-5 w-14 rounded bg-gray-200" />
        <div className="h-5 w-18 rounded bg-gray-200" />
      </div>
      <div className="mt-3 h-3 w-24 rounded bg-gray-200" />
    </div>
  );
}
