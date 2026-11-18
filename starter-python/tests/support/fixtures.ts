import { test as base, expect, type APIRequestContext, type APIResponse } from '@playwright/test';
import { AppServer } from './app-server.js';

export interface SessionCounts {
  capacity: number;
  activeCount: number;
  remainingSeats: number;
}

type Fixtures = { app: AppServer };

/**
 * `app` — a fresh process and a fresh, explicitly reset fixture directory for EVERY test.
 * `baseURL` points at it, so the built-in `page` and `request` fixtures talk to this
 * test's own server and nothing else. app.restart() keeps the port.
 */
export const test = base.extend<Fixtures>({
  app: async ({}, use, testInfo) => {
    const app = await AppServer.create();
    await assertFreshStore(app);
    await use(app);
    if (testInfo.status !== testInfo.expectedStatus) {
      await testInfo.attach('server.log', { body: app.log, contentType: 'text/plain' });
    }
    await app.dispose();
  },
  baseURL: async ({ app }, use) => {
    await use(app.baseURL);
  },
});

export { expect };

/**
 * Prep step: isolation is checked, not assumed. Before any test body runs, its store must hold
 * no reservations — through the API and in the SQLite file — and both sessions must read zero.
 * If a fixture ever starts sharing a server or a DATA_DIR, every test stops here with this
 * message instead of failing later as an unexplained race.
 */
async function assertFreshStore(app: AppServer) {
  const listed = await fetch(`${app.baseURL}/reservations`);
  const body = (await listed.json()) as { reservations: unknown[] };
  const counts = ((await (await fetch(`${app.baseURL}/sessions`)).json()) as {
    sessions: { id: string; activeCount: number }[];
  }).sessions.map((s) => `${s.id}:${s.activeCount}`);
  const stored = app.rows();
  if (listed.status !== 200 || body.reservations.length !== 0 || stored.length !== 0
      || counts.join(',') !== 'CT-101:0,CT-102:0') {
    throw new Error(
      `Test isolation broken: store at ${app.dataDir} is not fresh — API lists ${body.reservations.length}, ` +
      `SQLite holds ${stored.length}, sessions ${counts.join(',')}.`,
    );
  }
}

export const reserveBody = (requestKey: string, attendeeAlias = 'Ada', sessionId = 'CT-101') => ({
  sessionId, attendeeAlias, requestKey,
});

export async function sessions(request: APIRequestContext): Promise<Record<string, SessionCounts>> {
  const response = await request.get('/sessions');
  expect(response.status()).toBe(200);
  const body = await response.json();
  const out: Record<string, SessionCounts> = {};
  for (const s of body.sessions) {
    out[s.id] = { capacity: s.capacity, activeCount: s.activeCount, remainingSeats: s.remainingSeats };
  }
  return out;
}

export async function reserve(request: APIRequestContext, key: string, alias = 'Ada', session = 'CT-101') {
  return request.post('/reservations', { data: reserveBody(key, alias, session) });
}

/** A rejection is a 4xx with a non-empty JSON error — a 200 carrying an error is not one. */
export async function expectRejected(response: APIResponse, status: number, code: string) {
  expect(response.status(), await response.text()).toBe(status);
  const body = await response.json();
  expect(body.error.code).toBe(code);
  expect(typeof body.error.message).toBe('string');
  expect(body.error.message.length).toBeGreaterThan(0);
}
