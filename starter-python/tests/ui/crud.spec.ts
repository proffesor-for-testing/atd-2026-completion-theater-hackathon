import type { Page } from '@playwright/test';
import { test, expect, reserve, sessions } from '../support/fixtures.js';

// UI and API must agree: every state-changing UI test asserts the UI, the captured network
// response, AND an independent readback (API and/or the SQLite file).

const card = (page: Page, title: string) =>
  page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: new RegExp(title) }) });

async function expectSeats(page: Page, title: string, remaining: number, active: number) {
  await expect(card(page, title).locator('[data-stat="remaining"]')).toHaveText(`Remaining seats: ${remaining}`);
  await expect(card(page, title).locator('[data-stat="active"]')).toHaveText(`Active: ${active}`);
}

const rowFor = (page: Page, alias: string) =>
  page.getByRole('row').filter({ has: page.getByRole('cell', { name: alias, exact: true }) });

test.describe('AC-01/AC-02 the page shows the server state', () => {
  test('both seeded sessions appear with counts that match GET /sessions', async ({ page, request }) => {
    await page.goto('/');
    await expect(page).toHaveTitle('Session Seat Desk');
    const api = await sessions(request);
    await expectSeats(page, 'Catching Ghost Databases', api['CT-101'].remainingSeats, api['CT-101'].activeCount);
    await expectSeats(page, 'Tests That Can Fail', api['CT-102'].remainingSeats, api['CT-102'].activeCount);
    await expect(card(page, 'Catching Ghost Databases').locator('[data-stat="capacity"]')).toHaveText('Capacity: 2');
    await expect(page.getByText('No reservations yet.')).toBeVisible();
  });

  test('the page loads with no console errors or CSP violations', async ({ page }) => {
    const problems: string[] = [];
    page.on('console', (m) => { if (m.type() === 'error') problems.push(m.text()); });
    page.on('pageerror', (e) => problems.push(e.message));
    await page.goto('/');
    await expectSeats(page, 'Catching Ghost Databases', 2, 0);
    expect(problems).toEqual([]);
  });
});

test.describe('Create (AC-03)', () => {
  test('reserving through the form confirms only after the API does, and the store agrees', async ({ page, request, app }) => {
    await page.goto('/');
    await page.getByLabel('Session', { exact: true }).selectOption('CT-101');
    await page.getByLabel('Attendee alias').fill('  Ada  ');
    const key = await page.getByLabel('Request key').inputValue();
    expect(key).toMatch(/^ui-/);

    const responsePromise = page.waitForResponse((r) => r.url().endsWith('/reservations') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Reserve seat' }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(201);
    const record = await response.json();
    expect(record).toMatchObject({ sessionId: 'CT-101', attendeeAlias: 'Ada', requestKey: key, status: 'active' });

    await expect(page.getByRole('status')).toContainText(`Reserved a seat in CT-101 for Ada. Reservation ID ${record.id}`);
    const row = rowFor(page, 'Ada');
    await expect(row).toContainText('CT-101');
    await expect(row).toContainText('Active');
    await expect(row).toContainText(record.id);
    await expectSeats(page, 'Catching Ghost Databases', 1, 1);

    // Independent readback: API by ID, then the SQLite file itself.
    expect(await (await request.get(`/reservations/${record.id}`)).json()).toEqual(record);
    expect(app.rows()).toEqual([expect.objectContaining({ id: record.id, attendee_alias: 'Ada', status: 'active' })]);

    // The form is ready for the next booking with a fresh key.
    await expect(page.getByLabel('Attendee alias')).toHaveValue('');
    await expect(page.getByLabel('Request key')).not.toHaveValue(key);
  });

  test('resubmitting a used key shows the original reservation and takes no seat', async ({ page, request, app }) => {
    const original = await (await reserve(request, 'K1')).json();
    await page.goto('/');
    await page.getByLabel('Attendee alias').fill('Ada');
    await page.getByLabel('Request key').fill('K1');
    const responsePromise = page.waitForResponse((r) => r.url().endsWith('/reservations') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Reserve seat' }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    expect((await response.json()).id).toBe(original.id);

    await expect(page.getByRole('status')).toContainText('already used');
    await expect(page.getByRole('status')).toContainText('No new seat was taken');
    await expect(page.locator('#reservation-rows tr')).toHaveCount(1);
    await expectSeats(page, 'Catching Ghost Databases', 1, 1);
    expect(app.rows()).toHaveLength(1);
  });
});

test.describe('Read', () => {
  test('looking up a reservation by ID shows the stored record', async ({ page, request }) => {
    const record = await (await reserve(request, 'K7', 'Grace', 'CT-102')).json();
    await page.goto('/');
    await page.getByLabel('Reservation ID').fill(record.id);
    await page.getByRole('button', { name: 'Look up' }).click();
    const result = page.locator('#lookup-result');
    await expect(result).toBeVisible();
    await expect(result).toContainText(record.id);
    await expect(result).toContainText('Grace');
    await expect(result).toContainText('CT-102');
    await expect(result).toContainText('active');
  });

  test('looking up an unknown ID shows a visible error', async ({ page }) => {
    await page.goto('/');
    await page.getByLabel('Reservation ID').fill('00000000-0000-4000-8000-000000000000');
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(page.getByRole('alert')).toContainText('No reservation with that ID');
    await expect(page.locator('#lookup-result')).toBeHidden();
  });

  test('filters narrow the list to what the server returns for that filter', async ({ page, request }) => {
    await reserve(request, 'K1', 'Ada', 'CT-101');
    const bob = await (await reserve(request, 'K2', 'Bob', 'CT-102')).json();
    await request.post(`/reservations/${bob.id}/cancel`, { data: {} });
    await page.goto('/');
    await expect(page.locator('#reservation-rows tr')).toHaveCount(2);

    await page.getByLabel('Filter by status').selectOption('cancelled');
    await expect(page.locator('#reservation-rows tr')).toHaveCount(1);
    await expect(rowFor(page, 'Bob')).toContainText('Cancelled');

    await page.getByLabel('Filter by status').selectOption('');
    await page.getByLabel('Filter by session').selectOption('CT-101');
    await expect(page.locator('#reservation-rows tr')).toHaveCount(1);
    await expect(rowFor(page, 'Ada')).toBeVisible();
  });
});

test.describe('Update / delete — cancellation (AC-06)', () => {
  test('cancelling through the dialog releases the seat in the UI, API and store', async ({ page, request, app }) => {
    const record = await (await reserve(request, 'K1')).json();
    await page.goto('/');
    await expectSeats(page, 'Catching Ghost Databases', 1, 1);

    await page.getByRole('button', { name: 'Cancel reservation for Ada in CT-101' }).click();
    const dialog = page.getByRole('dialog', { name: 'Cancel this reservation?' });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText('Cancel the seat for Ada in CT-101?');

    const responsePromise = page.waitForResponse((r) => r.url().endsWith(`/reservations/${record.id}/cancel`));
    await dialog.getByRole('button', { name: 'Cancel reservation' }).click();
    const response = await responsePromise;
    expect(response.status()).toBe(200);
    expect((await response.json()).status).toBe('cancelled');

    await expect(page.getByRole('status')).toContainText('Cancelled the reservation for Ada in CT-101');
    await expect(rowFor(page, 'Ada')).toContainText('Cancelled');
    await expect(rowFor(page, 'Ada').getByRole('button')).toHaveCount(0);
    await expectSeats(page, 'Catching Ghost Databases', 2, 0);

    expect((await (await request.get(`/reservations/${record.id}`)).json()).status).toBe('cancelled');
    expect(app.rows()).toEqual([expect.objectContaining({ id: record.id, status: 'cancelled' })]);
  });

  // Found by exploratory testing: after the first cancel on a page, every later confirm
  // closed the dialog and cancelled nothing (no request, no message, seat still taken).
  test('several cancellations in a row on one page each reach the server', async ({ page, request, app }) => {
    const ids = [];
    for (const [key, alias, session] of [['K1', 'Ada', 'CT-101'], ['K2', 'Bob', 'CT-102'], ['K3', 'Cy', 'CT-102']]) {
      ids.push((await (await reserve(request, key, alias, session)).json()).id);
    }
    await page.goto('/');
    for (const [alias, session] of [['Ada', 'CT-101'], ['Bob', 'CT-102'], ['Cy', 'CT-102']]) {
      await page.getByRole('button', { name: `Cancel reservation for ${alias} in ${session}` }).click();
      const responsePromise = page.waitForResponse((r) => r.url().endsWith('/cancel'));
      await page.getByRole('dialog').getByRole('button', { name: 'Cancel reservation' }).click();
      expect((await responsePromise).status(), `cancel for ${alias} must reach the server`).toBe(200);
      await expect(rowFor(page, alias)).toContainText('Cancelled');
      await expect(page.getByRole('heading', { name: 'Reservations' }), 'focus must not be lost to <body>').toBeFocused();
    }
    for (const id of ids) {
      expect((await (await request.get(`/reservations/${id}`)).json()).status).toBe('cancelled');
    }
    expect(app.rows().every((r) => r.status === 'cancelled')).toBe(true);
  });

  test('an open lookup result is updated when that reservation is cancelled', async ({ page, request }) => {
    const record = await (await reserve(request, 'K1')).json();
    await page.goto('/');
    await page.getByLabel('Reservation ID').fill(record.id);
    await page.getByRole('button', { name: 'Look up' }).click();
    await expect(page.locator('#lookup-result')).toContainText('active');

    await page.getByRole('button', { name: 'Cancel reservation for Ada in CT-101' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel reservation' }).click();
    await expect(rowFor(page, 'Ada')).toContainText('Cancelled');
    await expect(page.locator('#lookup-result'), 'lookup must not keep showing a stale status')
      .toContainText('cancelled');
    await expect(page.locator('#lookup-result')).not.toContainText(/\bactive\b/);
  });

  test('choosing "Keep reservation" sends nothing and keeps the seat', async ({ page, request }) => {
    const record = await (await reserve(request, 'K1')).json();
    await page.goto('/');
    const cancelCalls: string[] = [];
    page.on('request', (r) => { if (r.url().includes('/cancel')) cancelCalls.push(r.url()); });

    await page.getByRole('button', { name: 'Cancel reservation for Ada in CT-101' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Keep reservation' }).click();
    await expect(page.getByRole('dialog')).toBeHidden();

    expect(cancelCalls).toEqual([]);
    await expect(rowFor(page, 'Ada')).toContainText('Active');
    expect((await (await request.get(`/reservations/${record.id}`)).json()).status).toBe('active');
  });
});

test.describe('Rejections are visible and change nothing', () => {
  test('a blank alias is stopped in the browser with a visible, linked error and no request', async ({ page, app }) => {
    await page.goto('/');
    const posts: string[] = [];
    page.on('request', (r) => { if (r.method() === 'POST') posts.push(r.url()); });

    await page.getByLabel('Attendee alias').fill('    ');
    await page.getByRole('button', { name: 'Reserve seat' }).click();

    await expect(page.getByRole('alert')).toHaveText('Enter an attendee alias. A blank alias cannot be reserved.');
    await expect(page.getByLabel('Attendee alias')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.getByLabel('Attendee alias')).toBeFocused();
    expect(posts).toEqual([]);
    await expectSeats(page, 'Catching Ghost Databases', 2, 0);
    expect(app.rows()).toEqual([]);
  });

  test('a full session shows "(full)" and the server\'s capacity error is shown to the user', async ({ page, request, app }) => {
    await reserve(request, 'K1', 'Ada');
    await reserve(request, 'K2', 'Bob');
    await page.goto('/');
    await expect(card(page, 'Catching Ghost Databases')).toContainText('Full');
    await expect(page.getByLabel('Session', { exact: true }).locator('option[value="CT-101"]')).toHaveText(/\(full\)/);

    await page.getByLabel('Session', { exact: true }).selectOption('CT-101');
    await page.getByLabel('Attendee alias').fill('Cy');
    const responsePromise = page.waitForResponse((r) => r.url().endsWith('/reservations') && r.request().method() === 'POST');
    await page.getByRole('button', { name: 'Reserve seat' }).click();
    expect((await responsePromise).status()).toBe(409);

    await expect(page.getByRole('alert')).toHaveText('No remaining seats in CT-101.');
    await expect(rowFor(page, 'Cy')).toHaveCount(0);
    await expectSeats(page, 'Catching Ghost Databases', 0, 2);
    expect(app.rows()).toHaveLength(2);
  });

  test('an alias containing markup is displayed as text and never executed', async ({ page, request }) => {
    const alias = '<img src=x onerror="window.__xss=1">';
    await reserve(request, 'K1', alias);
    await page.goto('/');
    await expect(rowFor(page, alias)).toBeVisible();
    await expect(page.locator('#reservation-rows img')).toHaveCount(0);
    expect(await page.evaluate(() => (window as unknown as { __xss?: number }).__xss)).toBeUndefined();
  });
});

test.describe('AC-07 durable state through the UI', () => {
  test('after a real server restart a reload shows the same reservations and counts', async ({ page, request, app }) => {
    const ada = await (await reserve(request, 'K1', 'Ada')).json();
    const bob = await (await reserve(request, 'K2', 'Bob')).json();
    await request.post(`/reservations/${bob.id}/cancel`, { data: {} });
    await page.goto('/');
    await expectSeats(page, 'Catching Ghost Databases', 1, 1);

    const pid = app.pid;
    await app.restart();
    expect(app.pid).not.toBe(pid);
    await page.reload();

    await expect(rowFor(page, 'Ada')).toContainText(ada.id);
    await expect(rowFor(page, 'Ada')).toContainText('Active');
    await expect(rowFor(page, 'Bob')).toContainText(bob.id);
    await expect(rowFor(page, 'Bob')).toContainText('Cancelled');
    await expectSeats(page, 'Catching Ghost Databases', 1, 1);
  });
});

test.describe('Keyboard only', () => {
  test('a seat can be reserved and cancelled without a mouse', async ({ page, app }) => {
    await page.goto('/');
    await page.getByLabel('Session', { exact: true }).focus();
    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Attendee alias')).toBeFocused();
    await page.keyboard.type('Kay');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('status')).toContainText('Reserved a seat in CT-101 for Kay');

    const cancel = page.getByRole('button', { name: 'Cancel reservation for Kay in CT-101' });
    await cancel.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Keep reservation' })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('dialog').getByRole('button', { name: 'Cancel reservation' })).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(rowFor(page, 'Kay')).toContainText('Cancelled');
    expect(app.rows()).toEqual([expect.objectContaining({ attendee_alias: 'Kay', status: 'cancelled' })]);
  });
});
