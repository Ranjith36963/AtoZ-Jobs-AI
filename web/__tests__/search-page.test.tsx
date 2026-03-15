import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SearchResultsGrid } from "@/components/search/SearchResultsGrid";
import type { SearchResult } from "@/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("q=developer&page=1"),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

const makeResult = (id: number): SearchResult => ({
  id,
  title: `Job ${id}`,
  company_name: `Company ${id}`,
  description_plain: `Description ${id}`,
  location_city: "London",
  location_region: "Greater London",
  location_type: "remote",
  salary_annual_min: 30000 + id * 1000,
  salary_annual_max: 50000 + id * 1000,
  salary_predicted_min: null,
  salary_predicted_max: null,
  salary_is_predicted: false,
  employment_type: ["full-time"],
  seniority_level: "mid",
  category: "technology",
  date_posted: "2026-03-10T00:00:00Z",
  source_url: `https://example.com/job/${id}`,
  rrf_score: 0.85,
});

describe("SearchResultsGrid", () => {
  it("renders job cards from results array", () => {
    const results = [makeResult(1), makeResult(2), makeResult(3)];
    render(
      <SearchResultsGrid
        results={results}
        total={3}
        isLoading={false}
        page={1}
        pageSize={20}
      />,
    );
    expect(screen.getByText("Job 1")).toBeInTheDocument();
    expect(screen.getByText("Job 2")).toBeInTheDocument();
    expect(screen.getByText("Job 3")).toBeInTheDocument();
  });

  it("shows skeleton during loading", () => {
    const { container } = render(
      <SearchResultsGrid
        results={[]}
        total={0}
        isLoading={true}
        page={1}
        pageSize={20}
      />,
    );
    const skeletons = container.querySelectorAll("[aria-hidden='true']");
    expect(skeletons.length).toBe(6);
  });

  it("shows empty state message", () => {
    render(
      <SearchResultsGrid
        results={[]}
        total={0}
        isLoading={false}
        page={1}
        pageSize={20}
      />,
    );
    expect(
      screen.getByText("No jobs match your search. Try broadening your filters."),
    ).toBeInTheDocument();
  });

  it("shows result count", () => {
    const results = [makeResult(1), makeResult(2)];
    render(
      <SearchResultsGrid
        results={results}
        total={42}
        isLoading={false}
        page={1}
        pageSize={20}
      />,
    );
    expect(screen.getByText(/Showing 1.*20 of 42 jobs/)).toBeInTheDocument();
  });

  it("shows error state", () => {
    render(
      <SearchResultsGrid
        results={[]}
        total={0}
        isLoading={false}
        page={1}
        pageSize={20}
        error="Connection failed"
      />,
    );
    expect(
      screen.getByText("Something went wrong. Please try again."),
    ).toBeInTheDocument();
  });
});
