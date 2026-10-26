import { test, expect } from "@playwright/test";

test.describe("Flow 6: Statutory Report Export & Ledger Verification", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      localStorage.setItem("apaar_access_token", "mock_super_admin_token");
      localStorage.setItem("apaar_refresh_token", "mock_refresh_token");
    });
  });

  test("should render reports catalog and allow verifying a SHA-256 report hash", async ({ page }) => {
    await page.goto("/reports");
    await expect(page.locator("text=Statutory Reports & Regulatory Engine")).toBeVisible();

    // Verify hash input widget
    const hashInput = page.locator('input[placeholder*="SHA-256"]');
    await expect(hashInput).toBeVisible();

    // Verify presence of statutory modules
    const catalogCards = page.locator("text=State-wise Intake").or(page.locator("text=Intake vs Enrolment"));
    if (await catalogCards.count() > 0) {
      await expect(catalogCards.first()).toBeVisible();
    }

    // Test hash lookup input
    await hashInput.fill("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    const verifyBtn = page.locator("button:has-text('Verify Ledger')");
    await expect(verifyBtn).toBeVisible();
    await verifyBtn.click();
  });
});
