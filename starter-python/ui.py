"""Pure rendering for the seat desk page. No I/O: session records in, HTML text out.

Session records use the API shape (api-contract.md): id, title, capacity,
activeCount, remainingSeats.
"""
import html

RESERVATION_SCRIPT = """
async function refreshCounts() {
  const response = await fetch('/sessions');
  const data = await response.json();
  const list = document.getElementById('seat-counts');
  list.replaceChildren(...data.sessions.map((s) => {
    const item = document.createElement('li');
    item.textContent = `${s.id} ${s.title}: ${s.remainingSeats} remaining of ${s.capacity}`;
    return item;
  }));
}
function showError(message) {
  document.getElementById('error-text').textContent = message;
  document.getElementById('error-message').hidden = false;
}
document.getElementById('dismiss-error').addEventListener('click', () => {
  document.getElementById('error-message').hidden = true;
});
async function reportFailure(response) {
  let message = `Request failed with status ${response.status}`;
  try {
    const data = await response.json();
    if (data.error && data.error.message) message = data.error.message;
  } catch (e) {
    // keep the generic message when the body is not JSON
  }
  showError(message);
}
const reservations = [];
function renderReservations() {
  const list = document.getElementById('reservation-list');
  list.replaceChildren(...reservations.map((r) => {
    const item = document.createElement('li');
    item.textContent = `${r.id} ${r.sessionId} ${r.attendeeAlias} ${r.status} `;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Cancel';
    button.addEventListener('click', async () => {
      const response = await fetch(`/reservations/${r.id}/cancel`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: '{}',
      });
      if (!response.ok) {
        await reportFailure(response);
      } else {
        Object.assign(r, await response.json());
        renderReservations();
      }
      await refreshCounts();
    });
    item.append(button);
    return item;
  }));
}
const form = document.getElementById('reservation-form');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const body = {
    sessionId: form.elements.sessionId.value,
    attendeeAlias: form.elements.attendeeAlias.value,
    requestKey: form.elements.requestKey.value,
  };
  const response = await fetch('/reservations', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    await reportFailure(response);
  } else {
    reservations.push(await response.json());
    renderReservations();
  }
  await refreshCounts();
});
refreshCounts();
"""


def reservation_form(sessions: list[dict]) -> str:
    options = "".join(
        '<option value="{id}">{id}</option>'.format(id=html.escape(s["id"]))
        for s in sessions
    )
    return (
        '<form id="reservation-form" method="post" action="/reservations">'
        '<p><label for="sessionId">Session</label> '
        f'<select id="sessionId" name="sessionId">{options}</select></p>'
        '<p><label for="attendeeAlias">Attendee alias</label> '
        '<input id="attendeeAlias" name="attendeeAlias" type="text"></p>'
        '<p><label for="requestKey">Request key</label> '
        '<input id="requestKey" name="requestKey" type="text"></p>'
        '<button type="submit">Reserve seat</button>'
        '</form>'
    )


def render_page(sessions: list[dict]) -> str:
    items = "".join(
        "<li><strong>{id}</strong> {title}: {remaining} remaining of {capacity}</li>".format(
            id=html.escape(session["id"]),
            title=html.escape(session["title"]),
            remaining=session["remainingSeats"],
            capacity=session["capacity"],
        )
        for session in sessions
    )
    return (
        '<!doctype html>\n'
        '<html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        "<title>Session Seat Desk</title>\n"
        '<link rel="stylesheet" href="/static/style.css">\n'
        "<main><h1>Session Seat Desk</h1>\n"
        '<div id="error-message" role="alert" hidden><span id="error-text"></span> '
        '<button type="button" id="dismiss-error">Dismiss</button></div>\n'
        "<h2>Sessions</h2>\n"
        f'<ul id="seat-counts">{items}</ul>'
        "<h2>Reserve a seat</h2>"
        f"{reservation_form(sessions)}"
        '<h2>Reservations</h2><ul id="reservation-list"></ul>'
        f"<script>{RESERVATION_SCRIPT}</script></main></html>\n"
    )
