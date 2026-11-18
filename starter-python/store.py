"""SQLite store for Session Seat Desk. Every PRD rule lives here.

Writes run inside BEGIN IMMEDIATE, which takes SQLite's write lock before the
capacity/idempotency checks are read, so two overlapping requests cannot both
see the last free seat. One connection per call: no state is cached in memory.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import uuid
from datetime import datetime, timezone

MARKER = 'session-seat-desk-disposable-fixture-v1'
ALIAS_MAX = 64
KEY_MAX = 128
SESSION_ID_MAX = 32
ALLOWED_FIELDS = {'sessionId', 'attendeeAlias', 'requestKey'}

SCHEMA = '''
    DROP TABLE IF EXISTS reservations;
    DROP TABLE IF EXISTS sessions;
    CREATE TABLE sessions (
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      capacity INTEGER NOT NULL CHECK (capacity >= 0));
    CREATE TABLE reservations (
      id TEXT PRIMARY KEY,
      session_id TEXT NOT NULL REFERENCES sessions(id),
      attendee_alias TEXT NOT NULL,
      request_key TEXT NOT NULL UNIQUE,
      status TEXT NOT NULL CHECK (status IN ('active','cancelled')),
      created_at TEXT NOT NULL,
      cancelled_at TEXT);
    CREATE INDEX reservations_by_session ON reservations(session_id, status);
'''


class StoreError(Exception):
    """A rejection the caller should see: HTTP status, stable code, readable message."""

    def __init__(self, status, code, message, field=None):
        super().__init__(message)
        self.status, self.code, self.message, self.field = status, code, message, field

    def body(self):
        error = {'code': self.code, 'message': self.message}
        if self.field:
            error['field'] = self.field
        return {'error': error}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


def _has_control_chars(text):
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in text)


def validate_reservation_request(body):
    """Return (sessionId, trimmedAlias, requestKey) or raise StoreError(400)."""
    if not isinstance(body, dict):
        raise StoreError(400, 'INVALID_BODY', 'Request body must be a JSON object.')
    unknown = sorted(set(body) - ALLOWED_FIELDS)
    if unknown:
        raise StoreError(400, 'UNKNOWN_FIELD',
                         'Unknown field(s): %s. Only sessionId, attendeeAlias and requestKey are accepted.'
                         % ', '.join(unknown), unknown[0])

    session_id = body.get('sessionId')
    if not isinstance(session_id, str) or not session_id:
        raise StoreError(400, 'SESSION_REQUIRED', 'sessionId must be a non-empty string.', 'sessionId')
    if len(session_id) > SESSION_ID_MAX:
        raise StoreError(400, 'SESSION_INVALID', 'sessionId is too long.', 'sessionId')

    alias = body.get('attendeeAlias')
    if not isinstance(alias, str):
        raise StoreError(400, 'ALIAS_REQUIRED', 'attendeeAlias must be a string.', 'attendeeAlias')
    alias = alias.strip()
    if not alias:
        raise StoreError(400, 'ALIAS_REQUIRED', 'Attendee alias cannot be blank.', 'attendeeAlias')
    if len(alias) > ALIAS_MAX:
        raise StoreError(400, 'ALIAS_TOO_LONG', 'Attendee alias must be at most %d characters.' % ALIAS_MAX,
                         'attendeeAlias')
    if _has_control_chars(alias):
        raise StoreError(400, 'ALIAS_INVALID', 'Attendee alias cannot contain control characters.',
                         'attendeeAlias')

    key = body.get('requestKey')
    if not isinstance(key, str) or not key:
        raise StoreError(400, 'REQUEST_KEY_REQUIRED', 'requestKey must be a non-empty string.', 'requestKey')
    if len(key) > KEY_MAX:
        raise StoreError(400, 'REQUEST_KEY_TOO_LONG', 'requestKey must be at most %d characters.' % KEY_MAX,
                         'requestKey')
    if _has_control_chars(key):
        raise StoreError(400, 'REQUEST_KEY_INVALID', 'requestKey cannot contain control characters.',
                         'requestKey')
    return session_id, alias, key


def _record(row):
    return {
        'id': row['id'],
        'sessionId': row['session_id'],
        'attendeeAlias': row['attendee_alias'],
        'requestKey': row['request_key'],
        'status': row['status'],
        'createdAt': row['created_at'],
        'cancelledAt': row['cancelled_at'],
    }


class Store:
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir).resolve()
        self.db_path = self.data_dir / 'seats.db'

    # -- lifecycle -------------------------------------------------------------

    def reset(self, seed_path):
        """Recreate and seed the fixture. Refuses a database it did not create."""
        marker = self.data_dir / '.fixture-owner'
        if self.db_path.exists() and (not marker.exists() or marker.read_text() != MARKER):
            raise RuntimeError('Refusing to reset an unmarked database. Choose a new DATA_DIR.')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(MARKER)
        seed = json.loads(Path(seed_path).read_text())
        with closing(self._connect()) as db:
            db.executescript(SCHEMA)
            db.execute('BEGIN')
            db.executemany('INSERT INTO sessions(id, title, capacity) VALUES (:id, :title, :capacity)', seed)
            db.execute('COMMIT')

    def is_initialised(self):
        if not self.db_path.exists():
            return False
        with closing(self._connect()) as db:
            names = {r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        return {'sessions', 'reservations'} <= names

    def _connect(self):
        db = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys = ON')
        db.execute('PRAGMA busy_timeout = 15000')
        return db

    # -- reads -----------------------------------------------------------------

    def sessions(self):
        with closing(self._connect()) as db:
            rows = db.execute('''
                SELECT s.id, s.title, s.capacity,
                       COUNT(r.id) AS active_count
                FROM sessions s
                LEFT JOIN reservations r ON r.session_id = s.id AND r.status = 'active'
                GROUP BY s.id ORDER BY s.id''').fetchall()
        return [{
            'id': r['id'], 'title': r['title'], 'capacity': r['capacity'],
            'activeCount': r['active_count'], 'remainingSeats': r['capacity'] - r['active_count'],
        } for r in rows]

    def get(self, reservation_id):
        with closing(self._connect()) as db:
            row = db.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
        if row is None:
            raise StoreError(404, 'RESERVATION_NOT_FOUND', 'No reservation with that ID.')
        return _record(row)

    def list(self, session_id=None, status=None):
        sql, args = 'SELECT * FROM reservations WHERE 1=1', []
        if session_id is not None:
            sql += ' AND session_id = ?'
            args.append(session_id)
        if status is not None:
            if status not in ('active', 'cancelled'):
                raise StoreError(400, 'STATUS_INVALID', 'status must be active or cancelled.', 'status')
            sql += ' AND status = ?'
            args.append(status)
        sql += ' ORDER BY created_at, id'
        with closing(self._connect()) as db:
            return [_record(r) for r in db.execute(sql, args).fetchall()]

    # -- writes ----------------------------------------------------------------

    def reserve(self, body):
        """Return (created: bool, record). Raises StoreError on any rejection."""
        session_id, alias, key = validate_reservation_request(body)
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                session = db.execute('SELECT id, capacity FROM sessions WHERE id = ?', (session_id,)).fetchone()
                if session is None:
                    raise StoreError(404, 'SESSION_NOT_FOUND', 'Unknown session %r.' % session_id, 'sessionId')

                existing = db.execute('SELECT * FROM reservations WHERE request_key = ?', (key,)).fetchone()
                if existing is not None:
                    if existing['session_id'] == session_id and existing['attendee_alias'] == alias:
                        db.execute('COMMIT')
                        return False, _record(existing)
                    raise StoreError(409, 'REQUEST_KEY_CONFLICT',
                                     'This request key was already used for a different session or alias.',
                                     'requestKey')

                active = db.execute("SELECT COUNT(*) FROM reservations WHERE session_id = ? AND status = 'active'",
                                    (session_id,)).fetchone()[0]
                if active >= session['capacity']:
                    raise StoreError(409, 'CAPACITY_FULL', 'No remaining seats in %s.' % session_id, 'sessionId')

                row_id = str(uuid.uuid4())
                db.execute('''INSERT INTO reservations
                              (id, session_id, attendee_alias, request_key, status, created_at)
                              VALUES (?, ?, ?, ?, 'active', ?)''', (row_id, session_id, alias, key, _now()))
                created = db.execute('SELECT * FROM reservations WHERE id = ?', (row_id,)).fetchone()
                db.execute('COMMIT')
                return True, _record(created)
            except BaseException:
                db.execute('ROLLBACK')
                raise

    def cancel(self, reservation_id):
        """Cancel once; repeat calls return the same cancelled record unchanged."""
        with closing(self._connect()) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                row = db.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
                if row is None:
                    raise StoreError(404, 'RESERVATION_NOT_FOUND', 'No reservation with that ID.')
                if row['status'] == 'active':
                    db.execute("UPDATE reservations SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
                               (_now(), reservation_id))
                    row = db.execute('SELECT * FROM reservations WHERE id = ?', (reservation_id,)).fetchone()
                db.execute('COMMIT')
                return _record(row)
            except BaseException:
                db.execute('ROLLBACK')
                raise
