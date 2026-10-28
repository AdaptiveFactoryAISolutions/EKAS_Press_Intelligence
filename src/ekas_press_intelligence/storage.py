"""EKAS ORIGINAL: durable JSON resources and append-only audit records."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS resources (
                    kind TEXT, id TEXT, payload TEXT NOT NULL,
                    PRIMARY KEY(kind,id));
                CREATE INDEX IF NOT EXISTS resources_by_run
                    ON resources(kind,json_extract(payload,'$.run_id'));
                CREATE TABLE IF NOT EXISTS audit (
                    sequence INTEGER PRIMARY KEY, kind TEXT, id TEXT,
                    operation TEXT, timestamp TEXT, reason TEXT, payload TEXT);
                CREATE TRIGGER IF NOT EXISTS immutable_submission
                BEFORE UPDATE ON resources WHEN OLD.kind IN ('submission','score')
                BEGIN SELECT RAISE(ABORT,'immutable benchmark record'); END;
                CREATE TRIGGER IF NOT EXISTS immutable_delete
                BEFORE DELETE ON resources WHEN OLD.kind IN ('submission','score')
                BEGIN SELECT RAISE(ABORT,'immutable benchmark record'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                BEGIN SELECT RAISE(ABORT,'append-only audit'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                BEGIN SELECT RAISE(ABORT,'append-only audit'); END;
            ''')
        self.path.chmod(0o600)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=30)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, kind, ident):
        with self._connect() as db:
            row = db.execute('SELECT payload FROM resources WHERE kind=? AND id=?',
                             (kind, ident)).fetchone()
        if row is None:
            raise KeyError(f'{kind} {ident} is unavailable')
        return json.loads(row[0])

    def _write(self, kind, ident, value, create, reason):
        payload = json.dumps(value, allow_nan=False, separators=(',', ':'))
        with self._connect() as db:
            try:
                if create:
                    db.execute('INSERT INTO resources VALUES (?,?,?)', (kind, ident, payload))
                else:
                    if kind in ('submission', 'score'):
                        raise Conflict('Scored benchmark records are immutable')
                    cur = db.execute('UPDATE resources SET payload=? WHERE kind=? AND id=?',
                                     (payload, kind, ident))
                    if cur.rowcount != 1:
                        raise KeyError(ident)
                db.execute('INSERT INTO audit(kind,id,operation,timestamp,reason,payload) VALUES (?,?,?,?,?,?)',
                           (kind, ident, 'CREATE' if create else 'UPDATE',
                            datetime.now(timezone.utc).isoformat(), reason, payload))
            except sqlite3.IntegrityError as exc:
                raise Conflict(f'{kind} {ident} already exists or is immutable') from exc
        return value

    def for_run(self, kind, run_id):
        """Read only the indexed run partition, including on existing databases."""
        with self._connect() as db:
            rows=db.execute("SELECT payload FROM resources WHERE kind=? AND json_extract(payload,'$.run_id')=?",
                            (kind,run_id)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def create(self, kind, ident, value):
        return self._write(kind, ident, value, True, 'create')

    def update(self, kind, ident, value, reason):
        return self._write(kind, ident, value, False, reason)

    def audit(self, kind, ident):
        with self._connect() as db:
            rows = db.execute('SELECT sequence,operation,timestamp,reason,payload FROM audit WHERE kind=? AND id=? ORDER BY sequence',
                              (kind, ident)).fetchall()
        return [dict(sequence=r[0], operation=r[1], timestamp=r[2], reason=r[3],
                     payload=json.loads(r[4])) for r in rows]

    def freeze_benchmark(self, ident, submission, score):
        """Freeze both immutable records or neither, including their audit trail."""
        with self._connect() as db:
            try:
                for kind,value in (('submission',submission),('score',score)):
                    payload=json.dumps(value,allow_nan=False)
                    db.execute('INSERT INTO resources VALUES (?,?,?)',(kind,ident,payload))
                    db.execute('INSERT INTO audit(kind,id,operation,timestamp,reason,payload) VALUES (?,?,?,?,?,?)',
                               (kind,ident,'CREATE',datetime.now(timezone.utc).isoformat(),'freeze and score',payload))
            except sqlite3.IntegrityError as exc:
                raise Conflict('Benchmark submission already frozen') from exc
