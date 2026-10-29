"""Transactional native-workflow jobs, dataset registration and frozen claims."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

OPERATIONS={'observability_export','generate','validate','plant_check','describe_process','make_challenge','plot','report','summarise','blind_analysis','new_plant','independent_evaluation'}
TERMINAL={'succeeded','failed','cancelled','interrupted'}


class JobConflict(ValueError):pass


def utc():return datetime.now(timezone.utc).isoformat()
def encode(value):return json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':'))


def process_identity(pid):
    """Linux boot/start identity; a reused PID must never confer job ownership."""
    if type(pid) is not int or pid<=0:return None
    try:
        fields=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        if fields[0] in {'Z','X'}:return None
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        return boot+':'+fields[19]  # /proc stat field22, after state(field3).
    except (OSError,IndexError):return None


def worker_is_live(pid,start):
    current=process_identity(pid)
    # Legacy live workers without a stored identity still reserve capacity, but
    # cannot be signalled by a replacement manager until ownership is established.
    return current is not None and (start is None or current==start)


class JobStore:
    def __init__(self,directory):
        self.directory=Path(directory).resolve();self.directory.mkdir(parents=True,exist_ok=True)
        self.directory.chmod(0o700);self.path=self.directory/'native.sqlite'
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, operation TEXT NOT NULL,
              parameters TEXT NOT NULL, state TEXT NOT NULL, phase TEXT NOT NULL,
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL, result TEXT, error TEXT,
              idempotency_key TEXT UNIQUE, fingerprint TEXT NOT NULL, worker TEXT,
              lease_until REAL, pid INTEGER, process_start TEXT);
            CREATE TABLE IF NOT EXISTS datasets(id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS submissions(dataset_id TEXT PRIMARY KEY,csv TEXT NOT NULL,
              sha256 TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS judgments(dataset_id TEXT NOT NULL,row_number INTEGER NOT NULL,
              payload TEXT NOT NULL,PRIMARY KEY(dataset_id,row_number));
            CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY,job_id TEXT,
              timestamp TEXT NOT NULL,operation TEXT NOT NULL,payload TEXT NOT NULL);
            CREATE TRIGGER IF NOT EXISTS immutable_submission_update BEFORE UPDATE ON submissions
              BEGIN SELECT RAISE(ABORT,'frozen submission');END;
            CREATE TRIGGER IF NOT EXISTS immutable_submission_delete BEFORE DELETE ON submissions
              BEGIN SELECT RAISE(ABORT,'frozen submission');END;
            CREATE TRIGGER IF NOT EXISTS immutable_judgment_update BEFORE UPDATE ON judgments
              BEGIN SELECT RAISE(ABORT,'immutable adjudication');END;
            CREATE TRIGGER IF NOT EXISTS immutable_judgment_delete BEFORE DELETE ON judgments
              BEGIN SELECT RAISE(ABORT,'immutable adjudication');END;
            CREATE TRIGGER IF NOT EXISTS immutable_event_update BEFORE UPDATE ON events
              BEGIN SELECT RAISE(ABORT,'append-only events');END;
            CREATE TRIGGER IF NOT EXISTS immutable_event_delete BEFORE DELETE ON events
              BEGIN SELECT RAISE(ABORT,'append-only events');END;
            ''')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row
        try:yield db;db.commit()
        except BaseException:db.rollback();raise
        finally:db.close()

    def _event(self,db,ident,operation,payload):
        db.execute('INSERT INTO events(job_id,timestamp,operation,payload) VALUES(?,?,?,?)',
                   (ident,utc(),operation,encode(payload)))

    def _job(self,row):
        if row is None:raise KeyError('Job unavailable')
        result=dict(row)
        for field in ('parameters','result','error'):
            result[field]=json.loads(result[field]) if result[field] is not None else None
        with self.connect() as db:
            failures=db.execute("SELECT payload FROM events WHERE job_id=? AND operation='log_capture_failed' ORDER BY sequence",(result['id'],)).fetchall()
        result['audit_failures']=[json.loads(r[0]) for r in failures]
        return result

    def create(self,operation,parameters,idempotency_key=None):
        if operation not in OPERATIONS:raise ValueError('Unknown native operation')
        if not isinstance(parameters,dict):raise ValueError('Parameters must be an object')
        payload=encode(parameters);fingerprint=hashlib.sha256((operation+payload).encode()).hexdigest()
        ident=str(uuid4());now=utc()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if idempotency_key:
                existing=db.execute('SELECT * FROM jobs WHERE idempotency_key=?',(idempotency_key,)).fetchone()
                if existing:
                    if existing['fingerprint']!=fingerprint:raise JobConflict('Idempotency key has different parameters')
                    return self._job(existing)
            db.execute('INSERT INTO jobs(id,operation,parameters,state,phase,created_at,updated_at,idempotency_key,fingerprint) VALUES(?,?,?,?,?,?,?,?,?)',
                       (ident,operation,payload,'queued','Queued',now,now,idempotency_key,fingerprint))
            self._event(db,ident,'queued',{'operation':operation,'fingerprint':fingerprint})
        return self.get(ident)

    def get(self,ident):
        with self.connect() as db:return self._job(db.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone())

    def list(self):
        with self.connect() as db:return [self._job(r) for r in db.execute('SELECT * FROM jobs ORDER BY created_at DESC')]

    def claim(self,worker):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM jobs WHERE state IN ('running','cancel_requested') LIMIT 1").fetchone():return None
            # A failed/cancelled worker may still be unwinding provider/native
            # contexts. Its verified live process continues to reserve capacity.
            workers=db.execute('SELECT pid,process_start FROM jobs WHERE pid IS NOT NULL AND process_start IS NOT NULL').fetchall()
            if any(worker_is_live(r['pid'],r['process_start']) for r in workers):return None
            row=db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created_at LIMIT 1").fetchone()
            if row is None:return None
            db.execute("UPDATE jobs SET state='running',phase='Starting native worker',worker=?,lease_until=?,updated_at=? WHERE id=?",(worker,time.time()+30,utc(),row['id']))
            self._event(db,row['id'],'claimed',{'worker':worker})
        return self.get(row['id'])

    def heartbeat(self,ident,phase=None,pid=None,process_start=None):
        with self.connect() as db:
            db.execute("UPDATE jobs SET phase=COALESCE(?,phase),pid=COALESCE(?,pid),process_start=COALESCE(?,process_start),lease_until=?,updated_at=? WHERE id=? AND state IN ('running','cancel_requested')",
                       (phase,pid,process_start,time.time()+30,utc(),ident))

    def _terminal(self,ident,state,result=None,error=None,dataset=None,submission=None,adjudication=None):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT state FROM jobs WHERE id=?',(ident,)).fetchone()
            if row is None:raise KeyError(ident)
            if row['state'] not in ('running','cancel_requested'):raise JobConflict('Job is not running')
            if row['state']=='cancel_requested' and state=='succeeded':raise JobConflict('Cancelled output cannot qualify')
            db.execute('UPDATE jobs SET state=?,phase=?,result=?,error=?,updated_at=?,lease_until=NULL WHERE id=?',
                       (state,state.title(),encode(result) if result is not None else None,encode(error) if error else None,utc(),ident))
            self._event(db,ident,state,{'error':error})
            if dataset is not None:
                if state!='succeeded':raise JobConflict('Partial output cannot qualify')
                db.execute('INSERT INTO datasets VALUES(?,?)',(dataset['id'],encode(dataset)))
            if submission is not None:
                if state!='succeeded':raise JobConflict('Partial output cannot freeze claims')
                dataset_id,csv=submission;digest=hashlib.sha256(csv.encode()).hexdigest()
                try:db.execute('INSERT INTO submissions VALUES(?,?,?,?)',(dataset_id,csv,digest,utc()))
                except sqlite3.IntegrityError as exc:raise JobConflict('Submission already frozen') from exc
                self._event(db,dataset_id,'submission_frozen',{'sha256':digest,'job_id':ident})
            if adjudication is not None:
                if state!='succeeded':raise JobConflict('Partial output cannot adjudicate')
                dataset_id,digest,judgments=adjudication
                frozen=db.execute('SELECT sha256 FROM submissions WHERE dataset_id=?',(dataset_id,)).fetchone()
                if frozen is None or frozen['sha256']!=digest:raise JobConflict('Frozen submission digest mismatch')
                try:
                    for value in judgments:
                        db.execute('INSERT INTO judgments VALUES(?,?,?)',(dataset_id,value['row'],encode(value)))
                        self._event(db,dataset_id,'adjudicated',dict(value,job_id=ident,submission_sha256=digest))
                except sqlite3.IntegrityError as exc:raise JobConflict('Judgment is already recorded') from exc
        return self.get(ident)

    def finish(self,ident,result,dataset=None,submission=None,adjudication=None):return self._terminal(ident,'succeeded',result=result,dataset=dataset,submission=submission,adjudication=adjudication)
    def fail(self,ident,code,message,result=None):return self._terminal(ident,'failed',result=result,error={'code':code,'message':message})
    def cancelled(self,ident):return self._terminal(ident,'cancelled')

    def record_log_failure(self,ident,message):
        """Preserve completed native results while retaining adverse audit facts."""
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT state FROM jobs WHERE id=?',(ident,)).fetchone()
            if row is None:raise KeyError(ident)
            error={'code':'LOG_CAPTURE_FAILED','message':str(message)}
            if row['state'] in ('running','cancel_requested'):
                db.execute("UPDATE jobs SET state='failed',phase='Private log capture failed',error=?,updated_at=?,lease_until=NULL WHERE id=?",(encode(error),utc(),ident))
                self._event(db,ident,'failed',{'error':error})
            self._event(db,ident,'log_capture_failed',dict(error,observed_job_state=row['state']))

    def request_cancel(self,ident):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT state FROM jobs WHERE id=?',(ident,)).fetchone()
            if row is None:raise KeyError(ident)
            if row['state'] in ('queued','running'):
                state='cancelled' if row['state']=='queued' else 'cancel_requested'
                db.execute('UPDATE jobs SET state=?,phase=?,updated_at=? WHERE id=?',(state,'Cancellation requested',utc(),ident))
                self._event(db,ident,state,{})
        return self.get(ident)

    def cancellation_targets(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute("SELECT id,pid,process_start FROM jobs WHERE state='cancel_requested'")]

    def recover(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            rows=db.execute("SELECT id,pid,process_start FROM jobs WHERE state IN ('running','cancel_requested') AND lease_until<?",(time.time(),)).fetchall()
            recovered=0
            for row in rows:
                if worker_is_live(row['pid'],row['process_start']):
                    db.execute("UPDATE jobs SET phase='Heartbeat expired; live worker still reserves capacity' WHERE id=?",(row['id'],))
                    continue
                db.execute("UPDATE jobs SET state='interrupted',phase='Worker lease expired',result=NULL,error=?,updated_at=? WHERE id=?",
                           (encode({'code':'WORKER_INTERRUPTED','message':'Worker heartbeat expired; partial artifacts are not qualified'}),utc(),row['id']))
                self._event(db,row['id'],'interrupted',{})
                recovered+=1
        return recovered

    def register_dataset(self,ident,payload,job_id=None):
        with self.connect() as db:
            if job_id:
                job=db.execute('SELECT state FROM jobs WHERE id=?',(job_id,)).fetchone()
                if not job or job['state']!='succeeded':raise JobConflict('Only completed native output can be registered')
            db.execute('INSERT INTO datasets VALUES(?,?)',(ident,encode(payload)))

    def dataset(self,ident):
        with self.connect() as db:row=db.execute('SELECT payload FROM datasets WHERE id=?',(ident,)).fetchone()
        if row is None:raise KeyError('Dataset unavailable')
        return json.loads(row['payload'])

    def datasets(self):
        with self.connect() as db:return [json.loads(r[0]) for r in db.execute('SELECT payload FROM datasets ORDER BY id')]

    def freeze_submission(self,dataset_id,csv):
        digest=hashlib.sha256(csv.encode()).hexdigest()
        with self.connect() as db:
            try:db.execute('INSERT INTO submissions VALUES(?,?,?,?)',(dataset_id,csv,digest,utc()))
            except sqlite3.IntegrityError as exc:raise JobConflict('Submission already frozen') from exc
            self._event(db,dataset_id,'submission_frozen',{'sha256':digest})
        return self.submission(dataset_id)

    def submission(self,dataset_id):
        with self.connect() as db:
            row=db.execute('SELECT * FROM submissions WHERE dataset_id=?',(dataset_id,)).fetchone()
            judgments=db.execute('SELECT payload FROM judgments WHERE dataset_id=? ORDER BY row_number',(dataset_id,)).fetchall()
        if row is None:raise KeyError('Submission unavailable')
        return dict(row,frozen=True,judgments=[json.loads(j[0]) for j in judgments])

    def adjudicate(self,dataset_id,judgments):
        self.submission(dataset_id)
        with self.connect() as db:
            try:
                for value in judgments:
                    db.execute('INSERT INTO judgments VALUES(?,?,?)',(dataset_id,value['row'],encode(value)))
                    self._event(db,dataset_id,'adjudicated',value)
            except sqlite3.IntegrityError as exc:raise JobConflict('Judgment is already recorded') from exc
        return self.submission(dataset_id)
