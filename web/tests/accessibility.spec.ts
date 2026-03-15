import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:3000";

test.describe("Accessibility — axe-core scans", () => {
  test("homepage has no critical or serious violations", async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(critical).toEqual([]);
  });

  test("search page has no critical or serious violations", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/search`);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(critical).toEqual([]);
  });

  test("job detail page has no critical or serious violations", async ({
    page,
  }) => {
    // Use a known job ID or navigate from search
    await page.goto(`${BASE_URL}/jobs/1`);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(critical).toEqual([]);
  });

  test("transparency page has no critical or serious violations", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/transparency`);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === "critical" || v.impact === "serious",
    );
    expect(critical).toEqual([]);
  });
});
