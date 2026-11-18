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
const form = document.getElementById('reservation-form');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const body = {
    sessionId: form.elements.sessionId.value,
    attendeeAlias: form.elements.attendeeAlias.value,
    requestKey: form.elements.requestKey.value,
  };
  await fetch('/reservations', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
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
        "<main><h1>Session Seat Desk</h1>\n"
        "<h2>Sessions</h2>\n"
        f'<ul id="seat-counts">{items}</ul>'
        "<h2>Reserve a seat</h2>"
        f"{reservation_form(sessions)}"
        f"<script>{RESERVATION_SCRIPT}</script></main></html>\n"
    )
