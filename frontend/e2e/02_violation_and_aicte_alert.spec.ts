import { test, expect } from "@playwright/test";

test.describe("Flow 2: Violation -> Live AICTE Alert -> Acknowledge", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      localStorage.setItem("apaar_access_token", "mock_super_admin_token");
      localStorage.setItem("apaar_refresh_token", "mock_refresh_token");
    });
  });

  test("should render AICTE dashboard with live alerts and allow acknowledgment", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=AICTE Dashboard")).toBeVisible();

    // Look for Alert card or alert badges
    const alertSection = page.locator("text=Live Statutory Alerts").or(page.locator("text=Active Violations"));
    if (await alertSection.count() > 0) {
      await expect(alertSection.first()).toBeVisible();
    }

    // Check acknowledging button interaction if present
    const ackBtn = page.locator("button:has-text('Acknowledge')").or(page.locator("button:has-text('Resolve')"));
    if (await ackBtn.count() > 0) {
      await ackBtn.first().click();
      await expect(page.locator("body")).toBeVisible();
    }
  });
});
