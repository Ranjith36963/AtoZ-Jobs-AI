import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CompanyInfo } from "@/components/jobs/CompanyInfo";
import { ApplyButton } from "@/components/jobs/ApplyButton";

describe("CompanyInfo", () => {
  it("renders SIC label, status, and website", () => {
    render(
      <CompanyInfo
        company={{
          name: "TechCo Ltd",
          sic_codes: ["62012"],
          company_status: "active",
          date_of_creation: "2020-01-01",
          website: "https://techco.com",
        }}
      />,
    );
    expect(screen.getByText("IT & Computing")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
    expect(screen.getByText("2020-01-01")).toBeInTheDocument();
    expect(screen.getByText("techco.com")).toBeInTheDocument();
  });

  it("renders nothing when company is null", () => {
    const { container } = render(<CompanyInfo company={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("handles company with minimal data", () => {
    render(
      <CompanyInfo
        company={{
          name: "Simple Corp",
          sic_codes: null,
          company_status: null,
          date_of_creation: null,
          website: null,
        }}
      />,
    );
    expect(screen.getByText("Company Details")).toBeInTheDocument();
    expect(screen.queryByText("Industry")).not.toBeInTheDocument();
  });
});

describe("ApplyButton", () => {
  it("opens in new tab with noopener", () => {
    render(
      <ApplyButton
        sourceUrl="https://example.com/apply"
        jobTitle="Python Developer"
      />,
    );
    const link = screen.getByText("Apply for this job");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("href", "https://example.com/apply");
  });

  it("has minimum 48px touch target", () => {
    render(
      <ApplyButton
        sourceUrl="https://example.com/apply"
        jobTitle="Python Developer"
      />,
    );
    const link = screen.getByText("Apply for this job");
    expect(link.className).toContain("min-h-[48px]");
    expect(link.className).toContain("min-w-[48px]");
  });
});
