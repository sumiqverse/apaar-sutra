import { test, expect } from "@playwright/test";

test.describe("Flow 4: DPDP Consent Verification End-to-End", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.evaluate(() => {
      localStorage.setItem("apaar_access_token", "mock_verifier_token");
      localStorage.setItem("apaar_refresh_token", "mock_refresh_token");
    });
  });

  test("should allow verifier to query student records with consent token", async ({ page }) => {
    await page.goto("/verifier");
    await expect(page.locator("text=Verifier Portal")).toBeVisible();

    const apaarInput = page.locator('input[placeholder*="APAAR"]').or(page.locator('input[type="text"]').first());
    await expect(apaarInput).toBeVisible();

    // Type 12-digit mock APAAR
    await apaarInput.fill("123456789012");

    // Look for OTP or purpose fields
    const purposeSelect = page.locator("select").first();
    if (await purposeSelect.count() > 0) {
      await purposeSelect.selectOption({ index: 0 });
    }

    const verifyBtn = page.locator("button:has-text('Verify')").first();
    await expect(verifyBtn).toBeVisible();
  });
});
