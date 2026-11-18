import { test, expect, reserve, sessions, expectRejected } from '../support/fixtures.js';

test.describe('AC-02 session readback', () => {
  test('fresh reset returns both seeded sessions with integer counts at zero', async ({ request }) => {
    const response = await request.get('/sessions');
    expect(response.status()).toBe(200);
    expect(response.headers()['content-type']).toContain('application/json');
    const body = await response.json();
    expect(body.sessions).toEqual([
      { id: 'CT-101', title: 'Catching Ghost Databases', capacity: 2, activeCount: 0, remainingSeats: 2 },
      { id: 'CT-102', title: 'Tests That Can Fail', capacity: 3, activeCount: 0, remainingSeats: 3 },
    ]);
  });
});

test.describe('AC-03 create and read (C, R)', () => {
  test('a reservation is created, read back by ID, stored, and takes one seat', async ({ request, app }) => {
    const created = await reserve(request, 'K1');
    expect(created.status()).toBe(201);
    const record = await created.json();
    expect(record).toMatchObject({ sessionId: 'CT-101', attendeeAlias: 'Ada', requestKey: 'K1', status: 'active' });
    expect(record.id).toMatch(/^[0-9a-f-]{36}$/);
    expect(created.headers()['location']).toBe(`/reservations/${record.id}`);

    const readBack = await request.get(`/reservations/${record.id}`);
    expect(readBack.status()).toBe(200);
    expect(await readBack.json()).toEqual(record);

    // Ghost Database check: the row is in the SQLite file, not just in a response.
    expect(app.rows()).toEqual([
      { id: record.id, session_id: 'CT-101', attendee_alias: 'Ada', request_key: 'K1', status: 'active' },
    ]);
    expect((await sessions(request))['CT-101']).toEqual({ capacity: 2, activeCount: 1, remainingSeats: 1 });
  });

  test('reading an unknown ID is a 404 with a JSON error', async ({ request }) => {
    await expectRejected(await request.get('/reservations/00000000-0000-4000-8000-000000000000'), 404,
      'RESERVATION_NOT_FOUND');
  });

  test('the list endpoint returns what was stored and filters by session and status', async ({ request }) => {
    const a = await (await reserve(request, 'K1', 'Ada', 'CT-101')).json();
    const b = await (await reserve(request, 'K2', 'Bob', 'CT-102')).json();
    await request.post(`/reservations/${b.id}/cancel`, { data: {} });

    const all = (await (await request.get('/reservations')).json()).reservations;
    expect(all.map((r: { id: string }) => r.id)).toEqual([a.id, b.id]);

    const ct102 = (await (await request.get('/reservations?sessionId=CT-102')).json()).reservations;
    expect(ct102).toHaveLength(1);
    expect(ct102[0]).toMatchObject({ id: b.id, status: 'cancelled' });

    const active = (await (await request.get('/reservations?status=active')).json()).reservations;
    expect(active.map((r: { id: string }) => r.id)).toEqual([a.id]);

    await expectRejected(await request.get('/reservations?status=bogus'), 400, 'STATUS_INVALID');
  });
});

test.describe('AC-05 idempotency', () => {
  test('replaying the same key with a padded alias returns the original without a second seat', async ({ request, app }) => {
    const first = await (await reserve(request, 'K1')).json();
    const before = await sessions(request);

    const replay = await reserve(request, 'K1', '  Ada  ');
    expect(replay.status()).toBe(200);
    expect(await replay.json()).toEqual(first);
    expect(await sessions(request)).toEqual(before);
    expect(app.rows()).toHaveLength(1);
  });

  test('reusing a key with another alias or another session conflicts and changes nothing', async ({ request, app }) => {
    await reserve(request, 'K1');
    const before = await sessions(request);
    await expectRejected(await reserve(request, 'K1', 'Bob'), 409, 'REQUEST_KEY_CONFLICT');
    await expectRejected(await reserve(request, 'K1', 'Ada', 'CT-102'), 409, 'REQUEST_KEY_CONFLICT');
    await expectRejected(await reserve(request, 'K1', 'ada'), 409, 'REQUEST_KEY_CONFLICT'); // case-sensitive
    expect(await sessions(request)).toEqual(before);
    expect(app.rows()).toHaveLength(1);
  });
});

test.describe('AC-06 cancellation (U/D: status change, never a hard delete)', () => {
  test('cancel releases one seat; repeating it and replaying the create change nothing', async ({ request, app }) => {
    const record = await (await reserve(request, 'K1')).json();
    expect((await sessions(request))['CT-101'].remainingSeats).toBe(1);

    const cancelled = await request.post(`/reservations/${record.id}/cancel`, { data: {} });
    expect(cancelled.status()).toBe(200);
    const cancelledRecord = await cancelled.json();
    expect(cancelledRecord).toMatchObject({ ...record, status: 'cancelled', cancelledAt: expect.any(String) });
    const after = await sessions(request);
    expect(after['CT-101']).toEqual({ capacity: 2, activeCount: 0, remainingSeats: 2 });

    const again = await request.post(`/reservations/${record.id}/cancel`, { data: {} });
    expect(again.status()).toBe(200);
    expect(await again.json()).toEqual(cancelledRecord);

    const replay = await reserve(request, 'K1');
    expect(replay.status()).toBe(200);
    expect(await replay.json()).toEqual(cancelledRecord);

    expect(await sessions(request)).toEqual(after);
    const stored = await request.get(`/reservations/${record.id}`);
    expect(await stored.json(), 'GET by ID must show the cancelled record').toEqual(cancelledRecord);
    expect(app.rows()).toEqual([expect.objectContaining({ id: record.id, status: 'cancelled' })]);
  });

  test('a new key books a new seat after a cancellation', async ({ request }) => {
    const first = await (await reserve(request, 'K1')).json();
    await request.post(`/reservations/${first.id}/cancel`, { data: {} });
    const second = await reserve(request, 'K2');
    expect(second.status()).toBe(201);
    const secondRecord = await second.json();
    expect(secondRecord.id, 'a new key must create a new reservation, not reuse the cancelled one').not.toBe(first.id);
    const stored = await (await request.get(`/reservations/${secondRecord.id}`)).json();
    expect(stored, 'the new reservation must be stored as active').toMatchObject({ requestKey: 'K2', status: 'active' });
    expect((await (await request.get(`/reservations/${first.id}`)).json()).status,
      'the cancelled reservation must stay cancelled').toBe('cancelled');
    expect((await sessions(request))['CT-101'].activeCount).toBe(1);
  });

  test('cancel requires an empty JSON object', async ({ request }) => {
    const record = await (await reserve(request, 'K1')).json();
    await expectRejected(await request.post(`/reservations/${record.id}/cancel`, { data: { status: 'active' } }),
      400, 'INVALID_BODY');
    expect((await (await request.get(`/reservations/${record.id}`)).json()).status).toBe('active');
  });
});
