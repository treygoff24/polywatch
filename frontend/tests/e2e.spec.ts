import { test, expect } from "@playwright/test";

test("homepage renders featured dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Polymarket anomaly radar")).toBeVisible();
  await expect(page.locator("text=Market Overview")).toBeVisible();
});

test("search navigates to market page", async ({ page }) => {
  await page.goto("/");
  const search = page.getByPlaceholder("Search Polymarket slugs…");
  await search.click();
  await search.type("honduras");
  const suggestion = page.getByTestId("market-search-result").first();
  await suggestion.waitFor();
  await suggestion.click();
  await expect(page).toHaveURL(/\/markets\//);
  await expect(page.locator("text=Outcome Snapshot")).toBeVisible();
});
