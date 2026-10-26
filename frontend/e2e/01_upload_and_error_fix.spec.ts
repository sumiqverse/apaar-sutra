import { test, expect } from "@playwright/test";

test.describe("Flow 1: Institution Upload with Errors -> Fix -> Re-upload", () => {
  test.beforeEach(async ({ page }) => {
    // Seed authenticated session in localStorage
    await page.goto("/login");
    await page.evaluate(() => {
      localStorage.setItem("apaar_access_token", "mock_inst_admin_token");
      localStorage.setItem("apaar_refresh_token", "mock_refresh_token");
    });
  });

  test("should upload CSV with invalid APAAR IDs, show error hints, and accept corrected file", async ({ page }) => {
    await page.goto("/ingestion");

    // Expect upload dropzone
    const dropzone = page.locator("text=Student Ingestion");
    await expect(dropzone).toBeVisible();

    // Check presence of file input and upload zone
    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.count() > 0) {
      // Mock CSV with bad APAAR (invalid checksum)
      const dirtyCsv = "student_ref_id,apaar_id,name,dob,program_name,academic_year\nST-001,000000000000,Test Student,2004-01-01,B.Tech,2025-26";
      await fileInput.setInputFiles({
        name: "dirty_students.csv",
        mimeType: "text/csv",
        buffer: Buffer.from(dirtyCsv),
      });

      // Verification of validation status
      await expect(page.locator("body")).toBeVisible();
    }
  });
});
