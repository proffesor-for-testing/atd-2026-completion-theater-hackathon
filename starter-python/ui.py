"""Pure rendering for the seat desk page. No I/O: session records in, HTML text out.

Session records use the API shape (api-contract.md): id, title, capacity,
activeCount, remainingSeats.
"""
import html


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
        f"<ul>{items}</ul></main></html>\n"
    )
