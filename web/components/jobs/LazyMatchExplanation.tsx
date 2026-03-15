"use client";

import dynamic from "next/dynamic";

const MatchExplanation = dynamic(
  () =>
    import("@/components/jobs/MatchExplanation").then(
      (m) => m.MatchExplanation,
    ),
  { ssr: false },
);

interface LazyMatchExplanationProps {
  query: string;
  job: {
    id: number;
    title: string;
    company_name: string;
    location_city: string | null;
  };
}

export function LazyMatchExplanation(props: LazyMatchExplanationProps) {
  return <MatchExplanation {...props} />;
}
