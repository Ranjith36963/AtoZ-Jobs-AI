import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { JobCard } from "@/components/jobs/JobCard";
import { SearchInput } from "@/components/search/SearchInput";
import { RadiusSelector } from "@/components/search/RadiusSelector";
import type { SearchResult } from "@/types";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("q=developer&radius=25"),
  useRouter: () => ({
    push: mockPush,
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

const sampleResult: SearchResult = {
  id: 42,
  title: "Python Developer",
  company_name: "TechCo Ltd",
  description_plain: "A great job",
  location_city: "London",
  location_region: "Greater London",
  location_type: "remote",
  salary_annual_min: 40000,
  salary_annual_max: 60000,
  salary_predicted_min: null,
  salary_predicted_max: null,
  salary_is_predicted: false,
  employment_type: ["full-time"],
  seniority_level: "mid",
  category: "technology",
  date_posted: new Date().toISOString(), // "Today"
  source_url: "https://example.com/job/42",
  rrf_score: 0.85,
};

describe("JobCard", () => {
  it("renders title, company, and salary badge", () => {
    render(<JobCard result={sampleResult} />);
    expect(screen.getByText("Python Developer")).toBeInTheDocument();
    expect(screen.getByText("TechCo Ltd")).toBeInTheDocument();
    expect(screen.getByText("£40k\u2013£60k")).toBeInTheDocument();
  });

  it("wraps in article element with link to /jobs/{id}", () => {
    render(<JobCard result={sampleResult} />);
    const article = screen.getByRole("article");
    expect(article).toBeInTheDocument();
    const link = article.querySelector("a");
    expect(link).toHaveAttribute("href", "/jobs/42");
  });

  it("shows relative date", () => {
    render(<JobCard result={sampleResult} />);
    expect(screen.getByText("Today")).toBeInTheDocument();
  });

  it("shows location and work type badges", () => {
    render(<JobCard result={sampleResult} />);
    expect(screen.getByText(/London/)).toBeInTheDocument();
    expect(screen.getByText("remote")).toBeInTheDocument();
  });

  it("shows category and seniority badges", () => {
    render(<JobCard result={sampleResult} />);
    expect(screen.getByText("technology")).toBeInTheDocument();
    expect(screen.getByText("mid")).toBeInTheDocument();
  });
});

describe("SearchInput", () => {
  it("renders input with correct aria label", () => {
    render(<SearchInput />);
    const input = screen.getByLabelText("Job search");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("type", "search");
  });

  it("initializes with q param from URL", () => {
    render(<SearchInput />);
    const input = screen.getByLabelText("Job search") as HTMLInputElement;
    expect(input.value).toBe("developer");
  });

  it("calls router.push on submit", () => {
    mockPush.mockClear();
    render(<SearchInput />);
    const input = screen.getByLabelText("Job search") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "react developer" } });
    fireEvent.submit(input.closest("form")!);
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("q=react+developer"),
    );
  });

  it("has a search role on the form", () => {
    render(<SearchInput />);
    expect(screen.getByRole("search")).toBeInTheDocument();
  });
});

describe("RadiusSelector", () => {
  it("renders all 5 radius options", () => {
    render(<RadiusSelector />);
    const select = screen.getByLabelText("Search radius");
    const options = select.querySelectorAll("option");
    expect(options).toHaveLength(5);
    expect(options[0]).toHaveTextContent("5 miles");
    expect(options[4]).toHaveTextContent("100 miles");
  });

  it("defaults to 25 from URL params", () => {
    render(<RadiusSelector />);
    const select = screen.getByLabelText("Search radius") as HTMLSelectElement;
    expect(select.value).toBe("25");
  });

  it("calls router.push on change", () => {
    mockPush.mockClear();
    render(<RadiusSelector />);
    const select = screen.getByLabelText("Search radius");
    fireEvent.change(select, { target: { value: "50" } });
    expect(mockPush).toHaveBeenCalledWith(
      expect.stringContaining("radius=50"),
    );
  });
});
