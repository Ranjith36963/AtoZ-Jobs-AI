interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      className={`rounded bg-gray-200 motion-safe:animate-pulse ${className}`}
    />
  );
}
