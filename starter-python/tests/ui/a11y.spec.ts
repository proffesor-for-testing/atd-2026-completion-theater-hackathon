import AxeBuilder from '@axe-core/playwright';
import { test, expect, reserve } from '../support/fixtures.js';

// axe checks only what it can automate — roughly a third of WCAG. A clean run here means
// "no automated violations found", not "accessible".
// `page as never`: @axe-core/playwright resolves its own playwright-core copy, so the Page types differ
// nominally. The runtime object is the same.
const WCAG = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

test('the populated page has no automated WCAG A/AA violations', async ({ page, request }) => {
  const ada = await (await reserve(request, 'K1', 'Ada')).json();
  await reserve(request, 'K2', 'Bob', 'CT-102');
  await request.post(`/reservations/${ada.id}/cancel`, { data: {} });
  await page.goto('/');
  await expect(page.locator('#reservation-rows tr')).toHaveCount(2);

  const results = await new AxeBuilder({ page: page as never }).withTags(WCAG).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(' | ')}`)).toEqual([]);
});

test('the page with a visible error and the open cancel dialog has no automated violations', async ({ page, request }) => {
  await reserve(request, 'K1', 'Ada');
  await page.goto('/');
  await page.getByRole('button', { name: 'Reserve seat' }).click(); // blank alias -> visible error
  await expect(page.getByRole('alert')).toBeVisible();
  await page.getByRole('button', { name: 'Cancel reservation for Ada in CT-101' }).click();
  await expect(page.getByRole('dialog')).toBeVisible();

  const results = await new AxeBuilder({ page: page as never }).withTags(WCAG).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(' | ')}`)).toEqual([]);
});
