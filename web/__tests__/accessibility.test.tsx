import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

// Test accessibility patterns across key components

describe("Accessibility", () => {
  describe("Skip link", () => {
    it("renders with correct href", async () => {
      const { SkipLink } = await import("@/components/layout/SkipLink");
      render(<SkipLink />);
      const link = screen.getByText(/skip to/i);
      expect(link).toHaveAttribute("href", "#main-content");
    });
  });

  describe("Layout", () => {
    it("header has navigation role", async () => {
      const { Header } = await import("@/components/layout/Header");
      render(<Header />);
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("footer has contentinfo role", async () => {
      const { Footer } = await import("@/components/layout/Footer");
      render(<Footer />);
      expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    });
  });

  describe("Touch targets", () => {
    it("ApplyButton meets 48px minimum touch target", async () => {
      const { ApplyButton } = await import("@/components/jobs/ApplyButton");
      render(
        <ApplyButton
          sourceUrl="https://example.com/apply"
          jobTitle="Test Job"
        />,
      );
      const link = screen.getByText("Apply for this job");
      expect(link.className).toContain("min-h-[48px]");
      expect(link.className).toContain("min-w-[48px]");
    });
  });

  describe("Reduced motion", () => {
    it("JobCardSkeleton uses motion-safe:animate-pulse", async () => {
      const { JobCardSkeleton } = await import(
        "@/components/jobs/JobCardSkeleton"
      );
      const { container } = render(<JobCardSkeleton />);
      const html = container.innerHTML;
      expect(html).toContain("motion-safe:animate-pulse");
    });
  });

  describe("Form labels", () => {
    it("SearchInput has accessible label for search input", async () => {
      const fs = await import("fs");
      const content = fs.readFileSync(
        "components/search/SearchInput.tsx",
        "utf-8",
      );
      // Must have a label element associated with the input
      expect(content).toContain("htmlFor");
      expect(content).toContain("aria-label");
    });
  });

  describe("ARIA live regions", () => {
    it("MatchExplanation has aria-live polite", async () => {
      const fs = await import("fs");
      const content = fs.readFileSync(
        "components/jobs/MatchExplanation.tsx",
        "utf-8",
      );
      expect(content).toContain('aria-live="polite"');
    });
  });

  describe("Transparency page", () => {
    it("all sections have proper aria-labelledby", async () => {
      const { TransparencyPage } = await import("@/app/transparency/page");
      const { container } = render(<TransparencyPage />);
      const sections = container.querySelectorAll("section[aria-labelledby]");
      expect(sections.length).toBe(8);

      // Each section should reference a heading id that exists
      for (const section of sections) {
        const labelledBy = section.getAttribute("aria-labelledby");
        expect(labelledBy).toBeTruthy();
        const heading = section.querySelector(`#${labelledBy}`);
        expect(heading).not.toBeNull();
      }
    });
  });
});
