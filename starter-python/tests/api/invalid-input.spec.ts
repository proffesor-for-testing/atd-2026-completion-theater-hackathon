import { test, expect, reserve, sessions, expectRejected } from '../support/fixtures.js';

type Probe = {
  name: string;
  send: (request: import('@playwright/test').APIRequestContext) => Promise<import('@playwright/test').APIResponse>;
  status: number;
  code: string;
};

// The five AC-08 cases, plus type and shape cases an auditor is likely to try next.
const probes: Probe[] = [
  { name: 'unknown session', status: 404, code: 'SESSION_NOT_FOUND',
    send: (r) => reserve(r, 'K1', 'Ada', 'UNKNOWN') },
  { name: 'blank alias', status: 400, code: 'ALIAS_REQUIRED', send: (r) => reserve(r, 'K2', '') },
  { name: 'whitespace-only alias', status: 400, code: 'ALIAS_REQUIRED', send: (r) => reserve(r, 'K3', '   \t ') },
  { name: 'missing request key', status: 400, code: 'REQUEST_KEY_REQUIRED',
    send: (r) => r.post('/reservations', { data: { sessionId: 'CT-101', attendeeAlias: 'Ada' } }) },
  { name: 'empty request key', status: 400, code: 'REQUEST_KEY_REQUIRED', send: (r) => reserve(r, '') },
  { name: 'malformed JSON', status: 400, code: 'MALFORMED_JSON',
    // A Buffer is sent byte-for-byte; a string would be JSON-encoded into the valid JSON "{broken".
    send: (r) => r.post('/reservations', { data: Buffer.from('{broken'), headers: { 'Content-Type': 'application/json' } }) },
  { name: 'empty body', status: 400, code: 'MALFORMED_JSON',
    send: (r) => r.post('/reservations', { headers: { 'Content-Type': 'application/json' } }) },
  { name: 'JSON array instead of object', status: 400, code: 'INVALID_BODY',
    send: (r) => r.post('/reservations', { data: [1, 2] }) },
  { name: 'numeric alias', status: 400, code: 'ALIAS_REQUIRED',
    send: (r) => r.post('/reservations', { data: { sessionId: 'CT-101', attendeeAlias: 42, requestKey: 'K4' } }) },
  { name: 'null session', status: 400, code: 'SESSION_REQUIRED',
    send: (r) => r.post('/reservations', { data: { sessionId: null, attendeeAlias: 'Ada', requestKey: 'K5' } }) },
  { name: 'cancel an unknown reservation', status: 404, code: 'RESERVATION_NOT_FOUND',
    send: (r) => r.post('/reservations/not-a-real-id/cancel', { data: {} }) },
];

test.describe('AC-08 invalid input', () => {
  for (const probe of probes) {
    test(`${probe.name} is rejected with a clear error and no state change`, async ({ request, app }) => {
      // Start from a non-empty state so "no change" is meaningful, not just "still zero".
      expect((await reserve(request, 'existing', 'Zed', 'CT-102')).status()).toBe(201);
      const before = await sessions(request);
      const rowsBefore = app.rows();

      await expectRejected(await probe.send(request), probe.status, probe.code);

      expect(await sessions(request)).toEqual(before);
      expect(app.rows(), 'no hidden or cancelled row may be inserted').toEqual(rowsBefore);
      expect((await request.get('/sessions')).status(), 'process must stay available').toBe(200);
    });
  }
});
