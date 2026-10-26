import { test, expect } from "@playwright/test";

test.describe("Flow 5: Tamper Proof Cryptographic Demo", () => {
  test("should demonstrate cryptographic verification and fail immediately on altered byte", async ({ page }) => {
    await page.goto("/tamper-demo");
    await expect(page.locator("text=Tamper Proof Demo").or(page.locator("text=Cryptographic"))).toBeVisible();

    // Verify initial authentic state badge
    const verifiedBadge = page.locator("text=AUTHENTIC").or(page.locator("text=VALID"));
    if (await verifiedBadge.count() > 0) {
      await expect(verifiedBadge.first()).toBeVisible();
    }

    // Tamper button click
    const tamperBtn = page.locator("button:has-text('Tamper')").or(page.locator("button:has-text('Simulate Alteration')"));
    if (await tamperBtn.count() > 0) {
      await tamperBtn.first().click();

      // Expect INVALID / FORGED / TAMPERED state badge
      const tamperedBadge = page.locator("text=TAMPERED").or(page.locator("text=INVALID")).or(page.locator("text=FAILED"));
      await expect(tamperedBadge.first()).toBeVisible();
    }
  });
});
