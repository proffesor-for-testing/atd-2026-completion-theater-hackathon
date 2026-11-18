import { request as httpRequest } from 'node:http';
import { test, expect, reserve, reserveBody, sessions, expectRejected } from '../support/fixtures.js';

// OWASP API Security Top 10 (2023) and Top 10 web basics, scoped to what this PRD exposes.
// Each test names the risk it covers. Out of scope, stated rather than claimed: API1/API5
// object- and function-level authorisation (the PRD has no users or roles) and API4 rate
// limiting (a limiter would break the mandated AC-04 concurrency probe).

const BASELINE_HEADERS = {
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'no-referrer',
  'cross-origin-opener-policy': 'same-origin',
  'cross-origin-resource-policy': 'same-origin',
};

test.describe('API8 security misconfiguration — headers', () => {
  test('JSON responses carry the baseline headers, no-store and a locked-down CSP', async ({ request }) => {
    for (const path of ['/sessions', '/reservations', '/reservations/unknown-id', '/nope']) {
      const headers = (await request.get(path)).headers();
      expect(headers, path).toMatchObject(BASELINE_HEADERS);
      expect(headers['cache-control'], path).toBe('no-store');
      expect(headers['content-security-policy'], path).toBe("default-src 'none'; frame-ancestors 'none'");
      expect(headers['content-type'], path).toContain('application/json');
    }
  });

  test('the page has a CSP that forbids inline script and framing', async ({ request }) => {
    const headers = (await request.get('/')).headers();
    expect(headers).toMatchObject(BASELINE_HEADERS);
    const csp = headers['content-security-policy'];
    expect(csp).toContain("script-src 'self'");
    expect(csp).not.toContain('unsafe-inline');
    expect(csp).not.toContain('unsafe-eval');
    expect(csp).toContain("frame-ancestors 'none'");
  });

  test('the Server header discloses no runtime or version', async ({ request }) => {
    const server = (await request.get('/sessions')).headers()['server'];
    expect(server).toBe('SeatDesk');
    expect(server).not.toMatch(/python|basehttp|\d/i);
  });

  test('no CORS grant is ever emitted, even to a cross-origin caller', async ({ request }) => {
    const response = await request.get('/sessions', { headers: { Origin: 'https://evil.example' } });
    expect(response.headers()['access-control-allow-origin']).toBeUndefined();
    const preflight = await request.fetch('/reservations', {
      method: 'OPTIONS',
      headers: { Origin: 'https://evil.example', 'Access-Control-Request-Method': 'POST' },
    });
    expect(preflight.status()).toBe(405);
    expect(preflight.headers()['access-control-allow-origin']).toBeUndefined();
  });
});

test.describe('CSRF and cross-origin writes', () => {
  test('a POST from another origin is refused before it touches state', async ({ request, app }) => {
    const response = await request.post('/reservations', {
      data: reserveBody('K1'), headers: { Origin: 'https://evil.example' },
    });
    await expectRejected(response, 403, 'CROSS_ORIGIN_FORBIDDEN');
    expect(app.rows()).toEqual([]);
  });

  test('a cross-origin cancel is refused and the seat stays taken', async ({ request }) => {
    const record = await (await reserve(request, 'K1')).json();
    await expectRejected(await request.post(`/reservations/${record.id}/cancel`, {
      data: {}, headers: { Origin: 'https://evil.example' },
    }), 403, 'CROSS_ORIGIN_FORBIDDEN');
    expect((await (await request.get(`/reservations/${record.id}`)).json()).status).toBe('active');
  });

  test('a rejected request does not desync the next request on the same connection', async ({ request }) => {
    // Regression: a 403 sent before reading the body left "{}" on the kept-alive socket,
    // which was then read as the start of the next request.
    for (let i = 0; i < 3; i++) {
      await expectRejected(await request.post('/reservations/unknown/cancel', {
        data: { padding: 'x'.repeat(50) }, headers: { Origin: 'https://evil.example' },
      }), 403, 'CROSS_ORIGIN_FORBIDDEN');
      expect((await request.get('/sessions')).status()).toBe(200);
    }
  });

  // Found by probing after the suite was green: Origin and Host both set to the attacker's
  // rebound name passed the Origin==Host check, and the write returned 201.
  test('DNS rebinding — a foreign Host is refused for reads and writes', async ({ app }) => {
    const send = (method: string, path: string, host: string, body?: string) =>
      new Promise<{ status: number; body: string }>((resolve, reject) => {
        const req = httpRequest(`${app.baseURL}${path}`, {
          method,
          headers: { Host: host, Origin: `http://${host}`, 'Content-Type': 'application/json',
            ...(body ? { 'Content-Length': String(Buffer.byteLength(body)) } : {}) },
        }, (res) => {
          let text = '';
          res.on('data', (c) => (text += c));
          res.on('end', () => resolve({ status: res.statusCode ?? 0, body: text }));
        });
        req.on('error', reject);
        req.end(body);
      });
    const rebound = `attacker.example:${app.port}`;
    const write = await send('POST', '/reservations', rebound, JSON.stringify(reserveBody('K1')));
    expect(write.status, 'a rebound write must be refused').toBe(403);
    expect(JSON.parse(write.body).error.code).toBe('HOST_FORBIDDEN');
    const read = await send('GET', '/reservations', rebound);
    expect(read.status, 'a rebound read must not leak the reservation list').toBe(403);
    expect(read.body).not.toContain('reservations');
    expect(app.rows(), 'nothing may be stored').toEqual([]);

    const local = await send('POST', '/reservations', `localhost:${app.port}`, JSON.stringify(reserveBody('K2')));
    expect(local.status, 'localhost is our own name and must work').toBe(201);
    expect(app.rows()).toEqual([expect.objectContaining({ request_key: 'K2' })]);
  });

  test('a same-origin POST is accepted', async ({ request, app }) => {
    const response = await request.post('/reservations', {
      data: reserveBody('K1'), headers: { Origin: app.baseURL },
    });
    expect(response.status(), 'the origin check must not block the app itself').toBe(201);
    const record = await response.json();
    expect(await (await request.get(`/reservations/${record.id}`)).json()).toEqual(record);
    expect(app.rows()).toEqual([expect.objectContaining({ id: record.id, status: 'active' })]);
  });

  for (const contentType of ['text/plain', 'application/x-www-form-urlencoded', 'multipart/form-data']) {
    test(`a body sent as ${contentType} (a form-postable type) is refused with 415`, async ({ request, app }) => {
      const response = await request.post('/reservations', {
        data: JSON.stringify(reserveBody('K1')), headers: { 'Content-Type': contentType },
      });
      await expectRejected(response, 415, 'UNSUPPORTED_MEDIA_TYPE');
      expect(app.rows()).toEqual([]);
    });
  }
});

test.describe('API3 mass assignment — the server owns id, status and timestamps', () => {
  for (const extra of [{ status: 'cancelled' }, { id: 'chosen-by-client' }, { capacity: 99 }, { createdAt: 'x' }]) {
    const field = Object.keys(extra)[0];
    test(`a client-supplied "${field}" is rejected`, async ({ request, app }) => {
      const response = await request.post('/reservations', { data: { ...reserveBody('K1'), ...extra } });
      await expectRejected(response, 400, 'UNKNOWN_FIELD');
      expect(app.rows()).toEqual([]);
    });
  }
});

test.describe('API4 unrestricted resource consumption', () => {
  test('a body over 16 KiB is refused with 413 and the server stays up', async ({ request, app }) => {
    const response = await request.post('/reservations', {
      data: reserveBody('K1', 'A'.repeat(20 * 1024)),
    });
    await expectRejected(response, 413, 'BODY_TOO_LARGE');
    expect(app.rows()).toEqual([]);
    expect((await request.get('/sessions')).status()).toBe(200);
  });

  test('field lengths are capped', async ({ request }) => {
    await expectRejected(await reserve(request, 'K1', 'x'.repeat(65)), 400, 'ALIAS_TOO_LONG');
    await expectRejected(await reserve(request, 'k'.repeat(129)), 400, 'REQUEST_KEY_TOO_LONG');
    expect((await reserve(request, 'k'.repeat(128), 'x'.repeat(64))).status()).toBe(201);
  });

  test('a chunked body without Content-Length is refused with 411', async ({ app }) => {
    const { status, body } = await new Promise<{ status: number; body: string }>((resolve, reject) => {
      const req = httpRequest(`${app.baseURL}/reservations`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'Transfer-Encoding': 'chunked' },
      }, (res) => {
        let text = '';
        res.on('data', (c) => (text += c));
        res.on('end', () => resolve({ status: res.statusCode ?? 0, body: text }));
      });
      req.on('error', reject);
      req.write(JSON.stringify(reserveBody('K1')));
      req.end();
    });
    expect(status).toBe(411);
    expect(JSON.parse(body).error.code).toBe('LENGTH_REQUIRED');
    expect(app.rows()).toEqual([]);
  });
});

test.describe('Injection', () => {
  test('SQL metacharacters in every field are stored literally and break nothing', async ({ request, app }) => {
    const alias = "Robert'); DROP TABLE reservations;--";
    const key = "' OR '1'='1";
    const created = await reserve(request, key, alias);
    expect(created.status()).toBe(201);
    const record = await created.json();
    expect(record).toMatchObject({ attendeeAlias: alias, requestKey: key });
    expect(app.rows()).toEqual([expect.objectContaining({ attendee_alias: alias, request_key: key })]);
    expect((await sessions(request))['CT-101'].activeCount).toBe(1);
    await expectRejected(await reserve(request, 'K2', 'Ada', "CT-101' OR '1'='1"), 404, 'SESSION_NOT_FOUND');
  });

  test('markup in an alias is returned as data, as JSON, never as HTML', async ({ request }) => {
    const alias = '<img src=x onerror=alert(1)>';
    const response = await reserve(request, 'K1', alias);
    expect(response.headers()['content-type']).toContain('application/json');
    expect((await response.json()).attendeeAlias).toBe(alias);
  });

  test('control characters are rejected', async ({ request }) => {
    await expectRejected(await reserve(request, 'K1', 'Ada\u0000'), 400, 'ALIAS_INVALID');
    await expectRejected(await reserve(request, 'K\n1'), 400, 'REQUEST_KEY_INVALID');
  });
});

test.describe('Path handling and error hygiene', () => {
  for (const path of ['/static/../app.py', '/%2e%2e/app.py', '/static/%2e%2e/store.py', '/app.py', '/.state/seats.db',
    '/static/', '/sessions.json']) {
    test(`no source or state is served for ${path}`, async ({ request }) => {
      const response = await request.get(path);
      expect(response.status()).toBe(404);
      const text = await response.text();
      expect(text).not.toContain('import ');
      expect(text).not.toContain('SQLite format');
      expect(JSON.parse(text).error.code).toBe('NOT_FOUND');
    });
  }

  test('unsupported methods get a JSON 405 with an Allow header', async ({ request }) => {
    for (const [method, path, allow] of [
      ['DELETE', '/reservations/x', 'GET, HEAD'], ['PUT', '/sessions', 'GET, HEAD'],
      ['PATCH', '/reservations', 'GET, HEAD, POST'],
    ]) {
      const response = await request.fetch(path, { method });
      expect(response.status(), `${method} ${path}`).toBe(405);
      expect(response.headers()['allow']).toBe(allow);
      expect((await response.json()).error.code).toBe('METHOD_NOT_ALLOWED');
    }
    expect((await request.get('/reservations/x/cancel')).status()).toBe(405);
  });

  test('errors carry no stack trace, file path or exception name', async ({ request }) => {
    const responses = [
      await request.post('/reservations', { data: Buffer.from('{"sessionId": '), headers: { 'Content-Type': 'application/json' } }),
      await request.post('/reservations', { data: { sessionId: { $ne: 1 }, attendeeAlias: 'A', requestKey: 'K' } }),
      await request.get('/reservations/%00'),
    ];
    for (const response of responses) {
      expect(response.status()).toBeGreaterThanOrEqual(400);
      expect(response.status()).toBeLessThan(500);
      const text = await response.text();
      expect(text).not.toMatch(/Traceback|File "|\.py|Error:|sqlite3|line \d+/);
    }
  });

  test('reservation IDs are random UUIDv4, not sequential', async ({ request }) => {
    const a = await (await reserve(request, 'K1')).json();
    const b = await (await reserve(request, 'K2', 'Bob')).json();
    for (const id of [a.id, b.id]) expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(a.id).not.toBe(b.id);
  });
});
