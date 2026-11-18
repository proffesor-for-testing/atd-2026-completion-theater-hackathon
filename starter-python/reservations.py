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
