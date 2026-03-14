"use client";

import { useState, useEffect, useRef } from "react";

interface MatchExplanationProps {
  query: string;
  job: {
    id: number;
    title: string;
    company_name: string;
    location_city: string | null;
  };
}

export function MatchExplanation({ query, job }: MatchExplanationProps) {
  if (!query) return null;
  return <MatchExplanationInner query={query} job={job} />;
}

function MatchExplanationInner({ query, job }: MatchExplanationProps) {
  const [explanation, setExplanation] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    async function fetchExplanation() {
      try {
        const response = await fetch("/api/explain", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, job }),
        });

        if (!response.ok) {
          throw new Error("Failed to get explanation");
        }

        const contentType = response.headers.get("content-type") ?? "";

        if (contentType.includes("application/json")) {
          // Fallback response (budget exhausted)
          const data = (await response.json()) as { explanation: string };
          setExplanation(data.explanation);
        } else if (response.body) {
          // Stream text response
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let text = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            text += decoder.decode(value, { stream: true });
            setExplanation(text);
          }
        }
      } catch {
        setError("Unable to generate explanation. Please try again.");
      } finally {
        setIsLoading(false);
      }
    }

    fetchExplanation();
  }, [query, job]);

  return (
    <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
      <div className="mb-2 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-blue-900">
          Why this matches your search
        </h3>
        <span className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
          AI-generated
        </span>
      </div>

      <div aria-live="polite" className="text-sm text-blue-800">
        {isLoading && !explanation && (
          <div className="space-y-2 motion-safe:animate-pulse">
            <div className="h-3 w-3/4 rounded bg-blue-200" />
            <div className="h-3 w-1/2 rounded bg-blue-200" />
          </div>
        )}
        {explanation && <p>{explanation}</p>}
        {error && <p className="text-red-600">{error}</p>}
      </div>
    </div>
  );
}
