import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SkipLink } from "@/components/layout/SkipLink";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";

describe("SkipLink", () => {
  it("renders with correct href and text", () => {
    render(<SkipLink />);
    const link = screen.getByText("Skip to main content");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "#main-content");
  });

  it("has sr-only class for screen reader visibility", () => {
    render(<SkipLink />);
    const link = screen.getByText("Skip to main content");
    expect(link.className).toContain("sr-only");
    expect(link.className).toContain("focus:not-sr-only");
  });
});

describe("Header", () => {
  it("renders logo and navigation links", () => {
    render(<Header />);
    expect(screen.getByText("AtoZ Jobs")).toBeInTheDocument();
    expect(screen.getByText("Home")).toBeInTheDocument();
    expect(screen.getByText("Search")).toBeInTheDocument();
    expect(screen.getByText("Transparency")).toBeInTheDocument();
  });

  it("has main navigation landmark", () => {
    render(<Header />);
    const nav = screen.getByRole("navigation", { name: /main navigation/i });
    expect(nav).toBeInTheDocument();
  });
});

describe("Footer", () => {
  it("renders transparency and accessibility links", () => {
    render(<Footer />);
    expect(screen.getByText("Transparency")).toBeInTheDocument();
    expect(screen.getByText("Accessibility")).toBeInTheDocument();
  });

  it("shows AI ranking disclosure", () => {
    render(<Footer />);
    expect(screen.getByText(/Results ranked by AI/)).toBeInTheDocument();
  });
});
