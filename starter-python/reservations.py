"""Pure reservation logic: state in, state out. No I/O."""


def new_reservation(reservation_id: str, session_id: str, alias: str, request_key: str) -> dict:
    """Pure: the stored record for a new active reservation."""
    return {
        "id": reservation_id,
        "sessionId": session_id,
        "attendeeAlias": alias,
        "requestKey": request_key,
        "status": "active",
    }


def add_reservation(state: dict, record: dict) -> dict:
    """Pure: state with one more reservation appended."""
    return {**state, "reservations": [*state["reservations"], record]}


def find_reservation(state: dict, reservation_id: str) -> dict | None:
    """Pure: the stored record with this ID, or None."""
    return next((r for r in state["reservations"] if r["id"] == reservation_id), None)
