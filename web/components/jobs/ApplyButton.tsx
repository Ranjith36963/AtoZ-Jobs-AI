"use client";

interface ApplyButtonProps {
  sourceUrl: string;
  jobTitle: string;
}

export function ApplyButton({ sourceUrl, jobTitle }: ApplyButtonProps) {
  function handleClick() {
    // PostHog tracking (if available)
    if (typeof window !== "undefined" && "posthog" in window) {
      const ph = window.posthog as { capture: (event: string, props: Record<string, string>) => void };
      ph.capture("apply_click", { jobTitle });
    }
  }

  return (
    <a
      href={sourceUrl}
      target="_blank"
      rel="noopener noreferrer"
      onClick={handleClick}
      className="inline-flex min-h-[48px] min-w-[48px] items-center justify-center rounded-lg bg-blue-600 px-8 py-3 text-base font-semibold text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
    >
      Apply for this job
    </a>
  );
}
