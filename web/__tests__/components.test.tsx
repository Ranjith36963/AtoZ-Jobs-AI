import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SalaryBadge } from "@/components/jobs/SalaryBadge";
import { SkillsPills } from "@/components/jobs/SkillsPills";
import { JobCardSkeleton } from "@/components/jobs/JobCardSkeleton";
import { Pagination } from "@/components/ui/Pagination";

// Mock next/navigation for Pagination
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams("q=developer"),
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

// Mock next/link
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

describe("SalaryBadge", () => {
  it("renders green badge for real salary", () => {
    render(
      <SalaryBadge
        salaryAnnualMin={30000}
        salaryAnnualMax={40000}
        salaryPredictedMin={null}
        salaryPredictedMax={null}
        salaryIsPredicted={false}
      />,
    );
    const badge = screen.getByText("£30k\u2013£40k");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-green-100");
  });

  it("renders amber badge for predicted salary with est. label", () => {
    render(
      <SalaryBadge
        salaryAnnualMin={null}
        salaryAnnualMax={null}
        salaryPredictedMin={35000}
        salaryPredictedMax={45000}
        salaryIsPredicted={true}
      />,
    );
    const badge = screen.getByText(/~£35k.*45k.*est\./);
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-amber-100");
    expect(badge.title).toContain("estimated by AI");
  });

  it("renders grey badge when no salary info", () => {
    render(
      <SalaryBadge
        salaryAnnualMin={null}
        salaryAnnualMax={null}
        salaryPredictedMin={null}
        salaryPredictedMax={null}
        salaryIsPredicted={false}
      />,
    );
    const badge = screen.getByText("Salary not disclosed");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain("bg-gray-100");
  });
});

describe("SkillsPills", () => {
  const manySkills = Array.from({ length: 8 }, (_, i) => ({
    name: `Skill ${i + 1}`,
    esco_uri: i === 0 ? "http://data.europa.eu/esco/skill/python" : null,
    skill_type: "knowledge",
    confidence: 0.9,
    is_required: i < 2,
  }));

  it("truncates at 5 and shows +N more", () => {
    render(<SkillsPills skills={manySkills} />);
    expect(screen.getByText("Skill 1")).toBeInTheDocument();
    expect(screen.getByText("Skill 5")).toBeInTheDocument();
    expect(screen.queryByText("Skill 6")).not.toBeInTheDocument();
    expect(screen.getByText("+3 more")).toBeInTheDocument();
  });

  it("renders ESCO link when URI present", () => {
    render(<SkillsPills skills={manySkills} />);
    // The <a> has role="listitem" which overrides implicit link role
    const items = screen.getAllByRole("listitem");
    const linkItem = items.find(
      (item) => item.tagName === "A",
    ) as HTMLAnchorElement;
    expect(linkItem).toBeDefined();
    expect(linkItem.href).toBe("http://data.europa.eu/esco/skill/python");
    expect(linkItem.target).toBe("_blank");
    expect(linkItem.rel).toBe("noopener noreferrer");
  });

  it("renders nothing for empty skills", () => {
    const { container } = render(<SkillsPills skills={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("highlights required skills with ring", () => {
    render(
      <SkillsPills
        skills={[
          {
            name: "Python",
            esco_uri: null,
            skill_type: null,
            confidence: null,
            is_required: true,
          },
        ]}
      />,
    );
    const pill = screen.getByText("Python");
    expect(pill.className).toContain("ring-1");
    expect(pill.className).toContain("bg-blue-100");
  });
});

describe("JobCardSkeleton", () => {
  it("renders with aria-hidden", () => {
    const { container } = render(<JobCardSkeleton />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.getAttribute("aria-hidden")).toBe("true");
  });

  it("uses motion-safe for animation", () => {
    const { container } = render(<JobCardSkeleton />);
    const skeleton = container.firstChild as HTMLElement;
    expect(skeleton.className).toContain("motion-safe:animate-pulse");
  });
});

describe("Pagination", () => {
  it("renders correct page numbers with active page", () => {
    render(<Pagination currentPage={3} totalPages={10} />);
    const activePage = screen.getByText("3");
    expect(activePage).toHaveAttribute("aria-current", "page");
    expect(activePage.className).toContain("bg-blue-600");
  });

  it("does not render when totalPages is 1", () => {
    const { container } = render(<Pagination currentPage={1} totalPages={1} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows Previous and Next links on middle page", () => {
    render(<Pagination currentPage={3} totalPages={10} />);
    expect(screen.getByText("Previous")).toBeInTheDocument();
    expect(screen.getByText("Next")).toBeInTheDocument();
  });

  it("preserves existing search params in page URLs", () => {
    render(<Pagination currentPage={2} totalPages={5} />);
    const page3Link = screen.getByText("3");
    expect(page3Link.getAttribute("href")).toContain("q=developer");
    expect(page3Link.getAttribute("href")).toContain("page=3");
  });
});
