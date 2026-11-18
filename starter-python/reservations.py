"""Pure reservation logic: state in, state out. No I/O."""


def alias_is_blank(alias: str) -> bool:
    """Pure: true when the alias is empty or only whitespace."""
    return alias.strip() == ""


def new_reservation(reservation_id: str, session_id: str, alias: str, request_key: str) -> dict:
    """Pure: the stored record for a new active reservation."""
    return {
        "id": reservation_id,
        "sessionId": session_id,
        "attendeeAlias": alias.strip(),
        "requestKey": request_key,
        "status": "active",
    }


def add_reservation(state: dict, record: dict) -> dict:
    """Pure: state with one more reservation appended."""
    return {**state, "reservations": [*state["reservations"], record]}


def find_reservation(state: dict, reservation_id: str) -> dict | None:
    """Pure: the stored record with this ID, or None."""
    return next((r for r in state["reservations"] if r["id"] == reservation_id), None)


def cancel_reservation(state: dict, reservation_id: str) -> dict:
    """Pure: state with the reservation marked cancelled. Other records are unchanged."""
    return {**state, "reservations": [
        {**r, "status": "cancelled"} if r["id"] == reservation_id else r
        for r in state["reservations"]]}


def find_replay(state: dict, record: dict) -> dict | None:
    """Pure: the stored reservation with the same key, session and alias as record, or None."""
    return next((r for r in state["reservations"]
                 if r["requestKey"] == record["requestKey"]
                 and r["sessionId"] == record["sessionId"]
                 and r["attendeeAlias"] == record["attendeeAlias"]), None)


def find_key_conflict(state: dict, record: dict) -> dict | None:
    """Pure: a stored reservation with the same request key but a different session or alias, or None."""
    return next((r for r in state["reservations"]
                 if r["requestKey"] == record["requestKey"]
                 and (r["sessionId"] != record["sessionId"]
                      or r["attendeeAlias"] != record["attendeeAlias"])), None)


class CapacityFull(Exception):
    """Raised when a session has no remaining seats."""


def add_active_reservation(state: dict, record: dict) -> dict:
    """Pure: state with the reservation added, or CapacityFull if its session is full."""
    session = next(s for s in state["sessions"] if s["id"] == record["sessionId"])
    active = sum(1 for r in state["reservations"]
                 if r["sessionId"] == record["sessionId"] and r["status"] == "active")
    if active >= session["capacity"]:
        raise CapacityFull(f"No remaining seats in {record['sessionId']}")
    return add_reservation(state, record)
