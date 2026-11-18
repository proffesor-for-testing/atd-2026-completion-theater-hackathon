// Session Seat Desk UI. Every value shown comes from an API response; user text is only
// ever written with textContent (never innerHTML), so aliases cannot inject markup.
'use strict';

const $ = (id) => document.getElementById(id);
const els = {
  sessionList: $('session-list'),
  sessionsLoading: $('sessions-loading'),
  lastSync: $('last-sync'),
  refresh: $('refresh'),
  form: $('reserve-form'),
  session: $('session-select'),
  alias: $('alias-input'),
  key: $('key-input'),
  newKey: $('new-key'),
  reserveButton: $('reserve-button'),
  lookupForm: $('lookup-form'),
  lookupInput: $('lookup-input'),
  lookupResult: $('lookup-result'),
  status: $('status'),
  alert: $('alert'),
  filterSession: $('filter-session'),
  filterStatus: $('filter-status'),
  table: $('reservation-table'),
  rows: $('reservation-rows'),
  empty: $('empty-reservations'),
  dialog: $('cancel-dialog'),
  dialogText: $('cancel-text'),
};

let sessionsById = new Map();

function el(tag, attrs = {}, text) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, value);
  if (text !== undefined) node.textContent = text;
  return node;
}

function newRequestKey() {
  if (globalThis.crypto && crypto.randomUUID) return 'ui-' + crypto.randomUUID();
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return 'ui-' + Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
}

function say(message) {
  els.alert.textContent = '';
  els.status.textContent = message;
}

function warn(message) {
  els.status.textContent = '';
  els.alert.textContent = message;
}

function clearInvalid() {
  for (const input of [els.alias, els.key, els.session]) input.removeAttribute('aria-invalid');
}

function markInvalid(field) {
  const input = { attendeeAlias: els.alias, requestKey: els.key, sessionId: els.session }[field];
  if (input) {
    input.setAttribute('aria-invalid', 'true');
    input.focus();
  }
}

async function api(method, path, body) {
  const init = { method, headers: { Accept: 'application/json' } };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch {
    return { ok: false, status: 0, data: { error: { message: 'Could not reach the server. Is it running?' } } };
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = { error: { message: 'The server sent an unreadable response (HTTP ' + response.status + ').' } };
  }
  return { ok: response.ok, status: response.status, data };
}

function errorMessage(data) {
  const error = data && data.error;
  if (!error) return 'Unexpected response from the server.';
  return typeof error === 'string' ? error : error.message || error.code || 'Request rejected.';
}

// -- sessions ------------------------------------------------------------------

function renderSessions(sessions) {
  els.sessionsLoading.hidden = true;
  els.sessionList.replaceChildren();
  for (const s of sessions) {
    const headingId = 'session-' + s.id;
    const card = el('li', { class: 'session-card', 'aria-labelledby': headingId, 'data-session-id': s.id });
    const title = el('h3', { id: headingId }, s.title);
    if (s.remainingSeats === 0) title.append(el('span', { class: 'full-badge' }, 'Full'));
    card.append(title, el('span', { class: 'session-id' }, s.id));

    const seats = el('div', { class: 'seats', 'aria-hidden': 'true' });
    for (let i = 0; i < s.capacity; i++) seats.append(el('span', { class: i < s.activeCount ? 'seat taken' : 'seat' }));
    card.append(seats);

    const stats = el('p', { class: 'session-stats' });
    const remaining = el('span', { 'data-stat': 'remaining' });
    remaining.append('Remaining seats: ', el('strong', {}, String(s.remainingSeats)));
    const active = el('span', { 'data-stat': 'active' });
    active.append('Active: ', el('strong', {}, String(s.activeCount)));
    const capacity = el('span', { 'data-stat': 'capacity' });
    capacity.append('Capacity: ', el('strong', {}, String(s.capacity)));
    stats.append(remaining, active, capacity);
    card.append(stats);
    els.sessionList.append(card);
  }
}

function renderSessionOptions(sessions) {
  const selected = els.session.value;
  els.session.replaceChildren();
  for (const s of sessions) {
    const suffix = s.remainingSeats === 0 ? ' (full)' : ' (' + s.remainingSeats + ' left)';
    els.session.append(el('option', { value: s.id }, s.id + ' — ' + s.title + suffix));
  }
  if (selected && sessionsById.has(selected)) els.session.value = selected;

  const filterSelected = els.filterSession.value;
  els.filterSession.replaceChildren(el('option', { value: '' }, 'All sessions'));
  for (const s of sessions) els.filterSession.append(el('option', { value: s.id }, s.id));
  els.filterSession.value = filterSelected;
}

// -- reservations -------------------------------------------------------------

function renderReservations(reservations) {
  els.rows.replaceChildren();
  els.table.hidden = reservations.length === 0;
  els.empty.hidden = reservations.length > 0;
  els.empty.textContent = els.filterSession.value || els.filterStatus.value
    ? 'No reservations match this filter.' : 'No reservations yet.';
  for (const r of reservations) {
    const row = el('tr', { 'data-reservation-id': r.id });
    row.append(
      el('td', {}, r.attendeeAlias),
      el('td', {}, r.sessionId),
    );
    const statusCell = el('td');
    statusCell.append(el('span', { class: 'badge ' + r.status }, r.status === 'active' ? 'Active' : 'Cancelled'));
    const keyCell = el('td');
    keyCell.append(el('code', {}, r.requestKey));
    const idCell = el('td');
    idCell.append(el('code', {}, r.id));
    const actionCell = el('td');
    if (r.status === 'active') {
      const button = el('button', {
        type: 'button', class: 'ghost small',
        'aria-label': 'Cancel reservation for ' + r.attendeeAlias + ' in ' + r.sessionId,
      }, 'Cancel');
      button.addEventListener('click', () => confirmCancel(r));
      actionCell.append(button);
    }
    row.append(statusCell, keyCell, idCell, actionCell);
    els.rows.append(row);
  }
}

async function refresh() {
  const query = new URLSearchParams();
  if (els.filterSession.value) query.set('sessionId', els.filterSession.value);
  if (els.filterStatus.value) query.set('status', els.filterStatus.value);
  const qs = query.toString();
  const [sessions, reservations] = await Promise.all([
    api('GET', '/sessions'),
    api('GET', '/reservations' + (qs ? '?' + qs : '')),
  ]);
  if (!sessions.ok) {
    warn('Could not load sessions: ' + errorMessage(sessions.data));
    return false;
  }
  sessionsById = new Map(sessions.data.sessions.map((s) => [s.id, s]));
  renderSessions(sessions.data.sessions);
  renderSessionOptions(sessions.data.sessions);
  if (reservations.ok) renderReservations(reservations.data.reservations);
  else warn('Could not load reservations: ' + errorMessage(reservations.data));
  // A visible lookup result is server state too: re-read it, or it goes stale after a cancel.
  if (lookedUpId && !els.lookupResult.hidden) {
    const again = await api('GET', '/reservations/' + encodeURIComponent(lookedUpId));
    if (again.ok) renderLookup(again.data);
  }
  els.lastSync.textContent = 'Last read from the server at ' + new Date().toLocaleTimeString() + '.';
  return true;
}

// -- actions -------------------------------------------------------------------

async function reserve(event) {
  event.preventDefault();
  clearInvalid();
  const alias = els.alias.value.trim();
  const key = els.key.value;
  if (!alias) {
    warn('Enter an attendee alias. A blank alias cannot be reserved.');
    markInvalid('attendeeAlias');
    return;
  }
  if (!key) {
    warn('A request key is required. Press "New key" to generate one.');
    markInvalid('requestKey');
    return;
  }
  els.reserveButton.disabled = true;
  els.reserveButton.textContent = 'Reserving…';
  try {
    const result = await api('POST', '/reservations', {
      sessionId: els.session.value, attendeeAlias: els.alias.value, requestKey: key,
    });
    if (result.ok) {
      const r = result.data;
      if (result.status === 201) {
        say('Reserved a seat in ' + r.sessionId + ' for ' + r.attendeeAlias + '. Reservation ID ' + r.id + '.');
      } else {
        say('This request key was already used: returned the existing reservation for ' + r.attendeeAlias
          + ' in ' + r.sessionId + ' (status: ' + r.status + '). No new seat was taken.');
      }
      els.alias.value = '';
      els.key.value = newRequestKey();
    } else {
      warn(errorMessage(result.data));
      markInvalid(result.data && result.data.error && result.data.error.field);
    }
  } finally {
    els.reserveButton.disabled = false;
    els.reserveButton.textContent = 'Reserve seat';
    await refresh();
  }
}

// The cancel runs from the dialog form's submit event, not the dialog's close event:
// exploratory testing found Chrome delivering no `close` event after the first cancel on a
// page, so every later confirm closed the dialog and silently cancelled nothing.
let pendingCancel = null;

function confirmCancel(reservation) {
  pendingCancel = reservation;
  els.dialogText.textContent = 'Cancel the seat for ' + reservation.attendeeAlias + ' in '
    + reservation.sessionId + '?';
  els.dialog.showModal();
}

els.dialog.querySelector('form').addEventListener('submit', async (event) => {
  const reservation = pendingCancel;
  pendingCancel = null;
  if (!reservation || !event.submitter || event.submitter.value !== 'confirm') return;
  const result = await api('POST', '/reservations/' + encodeURIComponent(reservation.id) + '/cancel', {});
  if (result.ok) {
    say('Cancelled the reservation for ' + result.data.attendeeAlias + ' in ' + result.data.sessionId
      + '. The seat is free again.');
  } else {
    warn('Could not cancel: ' + errorMessage(result.data));
  }
  await refresh();
  // The row's Cancel button is gone after re-rendering; keep keyboard users anchored.
  $('reservations-heading').focus();
});
els.dialog.addEventListener('cancel', () => { pendingCancel = null; });

async function lookup(event) {
  event.preventDefault();
  const id = els.lookupInput.value.trim();
  els.lookupResult.hidden = true;
  if (!id) {
    warn('Enter a reservation ID to look up.');
    els.lookupInput.setAttribute('aria-invalid', 'true');
    els.lookupInput.focus();
    return;
  }
  els.lookupInput.removeAttribute('aria-invalid');
  const result = await api('GET', '/reservations/' + encodeURIComponent(id));
  if (!result.ok) {
    warn('Lookup failed: ' + errorMessage(result.data));
    return;
  }
  lookedUpId = result.data.id;
  renderLookup(result.data);
  say('Found reservation ' + result.data.id + ' (' + result.data.status + ').');
}

let lookedUpId = null;

function renderLookup(r) {
  els.lookupResult.replaceChildren();
  for (const [label, value] of [['ID', r.id], ['Session', r.sessionId], ['Alias', r.attendeeAlias],
    ['Request key', r.requestKey], ['Status', r.status], ['Created', r.createdAt],
    ['Cancelled', r.cancelledAt || '—']]) {
    els.lookupResult.append(el('dt', {}, label), el('dd', {}, value));
  }
  els.lookupResult.hidden = false;
}

// -- wiring ------------------------------------------------------------------

els.key.value = newRequestKey();
els.form.addEventListener('submit', reserve);
els.lookupForm.addEventListener('submit', lookup);
els.newKey.addEventListener('click', () => { els.key.value = newRequestKey(); els.key.removeAttribute('aria-invalid'); });
els.refresh.addEventListener('click', async () => { if (await refresh()) say('Refreshed from the server.'); });
els.filterSession.addEventListener('change', refresh);
els.filterStatus.addEventListener('change', refresh);
refresh();
