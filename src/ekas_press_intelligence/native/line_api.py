"""Engineering-only guided setups with optimistic revisions and atomic run binding."""
from __future__ import annotations
import hashlib
import json
import math
from typing import Any
from uuid import UUID,uuid4
from fastapi import HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,StrictInt,ValidationError,field_validator
from ekas_press_intelligence.line_setup import LineSetup,fields,preset,preflight,native_config
from .jobs import JobConflict,utc,encode
from .line_source import model_digest


class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class ConfigRequest(Strict):config:dict[str,Any]
class StepRequest(ConfigRequest):step:StrictInt=Field(ge=1,le=8)
class DraftRequest(StepRequest):
    name:str=Field(min_length=1,max_length=80)
    @field_validator('name')
    @classmethod
    def clean_name(cls,value):
        if not value.strip():raise ValueError('Enter a setup name')
        return value.strip()
class DraftUpdate(DraftRequest):revision:StrictInt=Field(ge=1)
class RunRequest(Strict):
    revision:StrictInt=Field(ge=1)
    idempotency_key:str=Field(min_length=1,max_length=100)


def runtime_ready():
    from historiansim.plants import available_plants
    return 'stamping_line' in available_plants()


def errors(config):
    try:LineSetup.model_validate(config);return []
    except ValidationError as exc:
        result=[]
        for e in exc.errors():
            location=list(e['loc']);message=e['msg']
            if not location:
                candidate=message.removeprefix('Value error, ').split(':',1)[0]
                location=[candidate] if candidate in LineSetup.model_fields else []
            result.append({'location':['config',*location],'message':message})
        return result


def fail_errors(items):
    raise HTTPException(422,detail={'code':'INVALID_LINE_CONFIGURATION','message':'Correct the indicated settings before continuing.','errors':items})


def validate_shape(config):
    # Drafts may contain invalid field values so a user can save and recover,
    # but may never become arbitrary secret stores or nested payloads.
    if set(config)!=set(LineSetup.model_fields):
        raise ValueError('INVALID_LINE_DRAFT: use the complete current preset; unknown or missing fields')
    for key,value in config.items():
        if value is not None and (type(value) not in (str,int,float) or isinstance(value,str) and len(value)>100 or isinstance(value,float) and not math.isfinite(value)):
            raise ValueError('INVALID_LINE_DRAFT: '+key+' must contain a finite number or a listed choice')


def draft(row):
    if row is None:raise KeyError('Setup unavailable')
    item=dict(row);item['config']=json.loads(item['config']);return item


def check_bottleneck(checked):
    if checked['requires_bottleneck_acknowledgment']:
        fail_errors([{'location':['config','allow_bottleneck'],'message':'Washer or packing capacity is below press output. Restore normal capacity, or explicitly choose the deliberate bottleneck test in Step 6.'}])


def mount_line_routes(app,store,require):
    source_epoch=model_digest()
    def recoverable_draft(db,row):
        item=draft(row)
        previous=db.execute('SELECT r.job_id,r.revision,r.idempotency_key,j.state FROM line_runs r JOIN jobs j ON j.id=r.job_id WHERE r.draft_id=? AND r.revision=? ORDER BY r.created_at DESC LIMIT 1',
                            (item['id'],item['revision'])).fetchone()
        item['last_run']=None
        if previous:
            item['last_run']=dict(previous)
            prefix='line:'+item['id']+':'
            item['last_run']['idempotency_key']=item['last_run']['idempotency_key'].removeprefix(prefix)
        return item
    def require_source_epoch():
        if model_digest()!=source_epoch:
            raise HTTPException(409,detail={'code':'LINE_SOURCE_CHANGED','message':'Runtime source changed after this service started. Ask the installer to restart with the verified runtime, then review the setup again.'})
    with store.connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS line_drafts(id TEXT PRIMARY KEY,name TEXT NOT NULL,
          revision INTEGER NOT NULL,step INTEGER NOT NULL,config TEXT NOT NULL,
          schema_version INTEGER NOT NULL,updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS line_runs(idempotency_key TEXT PRIMARY KEY,draft_id TEXT NOT NULL,
          revision INTEGER NOT NULL,job_id TEXT NOT NULL,config_sha256 TEXT NOT NULL,
          config TEXT NOT NULL,created_at TEXT NOT NULL,model_sha256 TEXT NOT NULL DEFAULT '');
        CREATE TRIGGER IF NOT EXISTS immutable_line_run_update BEFORE UPDATE ON line_runs
          BEGIN SELECT RAISE(ABORT,'immutable line run');END;
        CREATE TRIGGER IF NOT EXISTS immutable_line_run_delete BEFORE DELETE ON line_runs
          BEGIN SELECT RAISE(ABORT,'immutable line run');END;
        ''')
        if 'model_sha256' not in {r['name'] for r in db.execute('PRAGMA table_info(line_runs)')}:
            db.execute("ALTER TABLE line_runs ADD COLUMN model_sha256 TEXT NOT NULL DEFAULT ''")

    @app.get('/v2/line/preset')
    def line_preset(request:Request):
        require(request,{'admin'})
        return dict(preset(),runtime_ready=runtime_ready())

    @app.post('/v2/line/check-step')
    def check_step(body:StepRequest,request:Request):
        require(request,{'admin'});validate_shape(body.config)
        steps={item['name']:item['step'] for item in fields()}
        found=[e for e in errors(body.config) if len(e['location'])<2 or steps.get(e['location'][1],0)<=body.step]
        if found:fail_errors(found)
        if body.step>=6:check_bottleneck(preflight(LineSetup.model_validate(body.config)))
        return {'passed':True,'step':body.step}

    @app.post('/v2/line/preflight')
    def line_preflight(body:ConfigRequest,request:Request):
        require(request,{'admin'});require_source_epoch();validate_shape(body.config)
        found=errors(body.config)
        if found:fail_errors(found)
        result=preflight(LineSetup.model_validate(body.config))
        check_bottleneck(result)
        result['model_sha256']=model_digest()
        result['runtime_ready']=runtime_ready()
        result['run_enabled']=result['runtime_ready']
        if not result['runtime_ready']:result['warnings'].append('The running service does not contain the stamping-line runtime. Ask the installer to start the verified line runtime.')
        return result

    @app.get('/v2/line/drafts')
    def list_drafts(request:Request):
        require(request,{'admin'})
        with store.connect() as db:
            db.execute('BEGIN')
            items=[recoverable_draft(db,r) for r in db.execute('SELECT * FROM line_drafts ORDER BY updated_at DESC').fetchall()]
        return {'drafts':items}

    @app.post('/v2/line/drafts',status_code=201)
    def create_draft(body:DraftRequest,request:Request):
        require(request,{'admin'});validate_shape(body.config)
        ident=str(uuid4())
        with store.connect() as db:
            db.execute('INSERT INTO line_drafts VALUES(?,?,?,?,?,?,?)',(ident,body.name,1,body.step,encode(body.config),1,utc()))
            result=draft(db.execute('SELECT * FROM line_drafts WHERE id=?',(ident,)).fetchone())
        return result

    @app.get('/v2/line/drafts/{ident}')
    def get_draft(ident:UUID,request:Request):
        require(request,{'admin'})
        with store.connect() as db:
            db.execute('BEGIN')
            return recoverable_draft(db,db.execute('SELECT * FROM line_drafts WHERE id=?',(str(ident),)).fetchone())

    @app.put('/v2/line/drafts/{ident}')
    def update_draft(ident:UUID,body:DraftUpdate,request:Request):
        require(request,{'admin'});validate_shape(body.config)
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=draft(db.execute('SELECT * FROM line_drafts WHERE id=?',(str(ident),)).fetchone())
            if current['schema_version']!=1:raise JobConflict('This setup requires an explicit schema migration; create a new preset setup')
            if current['revision']!=body.revision:raise JobConflict('Another tab saved a newer version. Reload that setup before editing again.')
            if current['name']==body.name and current['step']==body.step and encode(current['config'])==encode(body.config):
                return recoverable_draft(db,db.execute('SELECT * FROM line_drafts WHERE id=?',(str(ident),)).fetchone())
            db.execute('UPDATE line_drafts SET name=?,step=?,config=?,revision=revision+1,updated_at=? WHERE id=?',
                       (body.name,body.step,encode(body.config),utc(),str(ident)))
            return recoverable_draft(db,db.execute('SELECT * FROM line_drafts WHERE id=?',(str(ident),)).fetchone())

    @app.post('/v2/line/drafts/{ident}/run',status_code=201)
    def run_draft(ident:UUID,body:RunRequest,request:Request):
        require(request,{'admin'})
        ident=str(ident);key='line:'+ident+':'+body.idempotency_key
        with store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT * FROM line_runs WHERE idempotency_key=?',(key,)).fetchone()
            if previous:
                if previous['revision']!=body.revision:raise JobConflict('This run key belongs to another configuration revision')
                return store._job(db.execute('SELECT * FROM jobs WHERE id=?',(previous['job_id'],)).fetchone(),db)
            require_source_epoch()
            current=draft(db.execute('SELECT * FROM line_drafts WHERE id=?',(ident,)).fetchone())
            if current['schema_version']!=1 or current['revision']!=body.revision:raise JobConflict('Setup changed. Reload and check the latest revision before running.')
            found=errors(current['config'])
            if found:fail_errors(found)
            setup=LineSetup.model_validate(current['config']);checked=preflight(setup)
            check_bottleneck(checked)
            if not runtime_ready():raise HTTPException(409,detail={'code':'LINE_RUNTIME_UNAVAILABLE','message':'Ask the installer to start the verified stamping-line runtime. No job was created.'})
            cfg=native_config(setup)
            parameters={'config':cfg,'resample':1.,'validate':True,'practice':True}
            payload=encode(parameters);fingerprint=hashlib.sha256(('generate'+payload).encode()).hexdigest()
            job_id=str(uuid4());now=utc()
            db.execute('INSERT INTO jobs(id,operation,parameters,state,phase,created_at,updated_at,idempotency_key,fingerprint) VALUES(?,?,?,?,?,?,?,?,?)',
                       (job_id,'generate',payload,'queued','Queued',now,now,key,fingerprint))
            store._event(db,job_id,'queued',{'operation':'generate','fingerprint':fingerprint,'setup_id':ident,'setup_revision':body.revision,
                'setup_sha256':checked['config_sha256'],'scope':'synthetic_practice'})
            db.execute('INSERT INTO line_runs VALUES(?,?,?,?,?,?,?,?)',(key,ident,body.revision,job_id,checked['config_sha256'],encode(checked['config']),now,model_digest()))
            return store._job(db.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone(),db)
