import { test, expect, reserve, sessions, expectRejected } from '../support/fixtures.js';

test.describe('AC-04 capacity', () => {
  test('a third request for a two-seat session is rejected and creates nothing', async ({ request, app }) => {
    expect((await reserve(request, 'K1')).status()).toBe(201);
    expect((await reserve(request, 'K2', 'Bob')).status()).toBe(201);
    const before = await sessions(request);

    await expectRejected(await reserve(request, 'K3', 'Cy'), 409, 'CAPACITY_FULL');

    expect(await sessions(request)).toEqual(before);
    expect(before['CT-101']).toEqual({ capacity: 2, activeCount: 2, remainingSeats: 0 });
    expect(app.rows().map((r) => r.request_key)).toEqual(['K1', 'K2']);
  });

  // Each batch is its own test, so each gets its own fresh process and fixture directory.
  // Ten bounded batches are evidence for these trials, not a proof of race freedom.
  for (let batch = 1; batch <= 10; batch++) {
    test(`ten simultaneous requests for the last seat admit exactly one — batch ${batch}`, async ({ request, app }) => {
      expect((await reserve(request, 'seed')).status()).toBe(201);

      const responses = await Promise.all(
        Array.from({ length: 10 }, (_, j) => reserve(request, `race-${j}`, `Alias-${j}`)),
      );
      const statuses = responses.map((r) => r.status());
      expect(statuses.filter((s) => s === 201), statuses.join(',')).toHaveLength(1);
      for (const response of responses.filter((r) => r.status() !== 201)) {
        await expectRejected(response, 409, 'CAPACITY_FULL');
      }

      expect((await sessions(request))['CT-101']).toEqual({ capacity: 2, activeCount: 2, remainingSeats: 0 });
      expect(app.rows().filter((r) => r.session_id === 'CT-101' && r.status === 'active')).toHaveLength(2);
    });
  }
});
