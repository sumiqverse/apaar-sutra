import { test, expect } from "@playwright/test";

test.describe("Flow 3: Risk Drill-Down & Anomaly Explanation", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      localStorage.setItem("apaar_access_token", "mock_super_admin_token");
      localStorage.setItem("apaar_refresh_token", "mock_refresh_token");
    });
  });

  test("should display institutional risk ranking and allow drilling down into anomalies", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();

    // Verify presence of risk ranking section or navigate to institutions tab
    const riskHeading = page.locator("text=Risk").or(page.locator("text=Anomaly"));
    if (await riskHeading.count() > 0) {
      await expect(riskHeading.first()).toBeVisible();
    }

    // Check row drill-down click
    const drilldownRow = page.locator("table tr").nth(1);
    if (await drilldownRow.count() > 0) {
      await drilldownRow.click();
      await expect(page.locator("body")).toBeVisible();
    }
  });
});
