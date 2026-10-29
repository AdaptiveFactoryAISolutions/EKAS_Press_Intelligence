"""Native historian workflow API; construction, analysis and adjudication are distinct."""
from contextlib import asynccontextmanager
from io import StringIO
import json
import hashlib
import os
import ipaddress
import tempfile
from pathlib import Path
from typing import Literal
from uuid import UUID
import pandas as pd
from fastapi import FastAPI,HTTPException,Request,Query
from fastapi.responses import FileResponse,JSONResponse,Response
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt
from ekas_press_intelligence import __version__
from .bootstrap import activate
NATIVE_SOURCE=activate()
from .jobs import JobStore,JobConflict
from .worker import JobManager,REPO
from .data import dataset_info,query_samples,query_events,public_files,resolve_public_file
from .catalog import capabilities

PRIVATE_OPS={'observability_export','generate','validate','make_challenge','report','summarise','plant_check','new_plant','independent_evaluation'}
ADMIN_OPS={'observability_export','generate','validate','make_challenge','new_plant','plant_check'}
DATASET_OPS={'observability_export','validate','make_challenge','plot','report','summarise','blind_analysis','independent_evaluation'}


class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class JobRequest(Strict):
    operation:Literal['observability_export','generate','validate','plant_check','describe_process','make_challenge','plot','report','summarise','new_plant','blind_analysis','independent_evaluation']
    parameters:dict=Field(default_factory=dict)
    idempotency_key:str|None=Field(default=None,max_length=200)
class SubmissionRequest(Strict):csv:str=Field(max_length=4_000_000)
class Judgment(Strict):
    row:StrictInt=Field(ge=2)
    correct:StrictBool
    reason:str=Field(min_length=1,max_length=5000)
class AdjudicationRequest(Strict):judgments:list[Judgment]=Field(min_length=1,max_length=10000)


def forbidden(code,message,status=403):raise HTTPException(status,detail={'code':code,'message':message})


def redact(value):
    if isinstance(value,dict):
        return {k:redact(v) for k,v in value.items() if k not in {'private_path','public_path','private_directory','private_artifacts','dataset_dir','worker','lease_until','pid','process_start','fingerprint','idempotency_key','true_cause','cause_id','config'}}
    if isinstance(value,list):return [redact(v) for v in value]
    return value


def create_native_app(state_dir=None,start_worker=True,tokens=None,local_only=None):
    directory=Path(state_dir or os.environ.get('EKAS_NATIVE_STATE_DIR','work/native-service')).resolve()
    token_map=tokens if tokens is not None else json.loads(os.environ.get('EKAS_NATIVE_TOKENS','{}'))
    local=local_only if local_only is not None else os.environ.get('EKAS_NATIVE_LOCAL_ONLY','1')=='1'
    if not isinstance(token_map,dict) or any(not k or v not in ('analyst','evaluator','admin') for k,v in token_map.items()):raise ValueError('Invalid token/role configuration')
    if not local and not token_map:raise ValueError('Network deployment requires role-specific authentication tokens')
    store=JobStore(directory);manager=JobManager(directory)
    @asynccontextmanager
    async def lifespan(app):
        if start_worker:manager.start()
        try:yield
        finally:
            if start_worker:manager.close()
    app=FastAPI(title='EKAS Native Historian Platform',version=__version__,lifespan=lifespan)
    app.state.store=store
    app.state.manager=manager
    app.state.native_source=NATIVE_SOURCE

    @app.middleware('http')
    async def boundary(request:Request,call_next):
        host=request.url.hostname
        peer=request.client.host if request.client else None
        try:loopback_peer=ipaddress.ip_address(peer).is_loopback
        except (ValueError,TypeError):loopback_peer=False
        test_peer=host=='testserver' and peer=='testclient'
        if local and not (test_peer or (loopback_peer and host in ('127.0.0.1','localhost','::1'))):
            return JSONResponse({'detail':{'code':'LOCAL_HOST_REQUIRED','message':'Local deployment accepts only loopback hostnames'}},status_code=403)
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':{'code':'ORIGIN_FORBIDDEN','message':'Cross-origin access is disabled'}},status_code=403)
        credential=request.headers.get('authorization','')
        role=token_map.get(credential[7:]) if credential.startswith('Bearer ') else None
        if not token_map and not credential:role='admin' if local else None
        request.state.role=role
        if request.url.path.startswith('/v2/') and role is None:
            return JSONResponse({'detail':{'code':'AUTHENTICATION_REQUIRED','message':'Supply a valid role-specific bearer token'}},status_code=401)
        response=await call_next(request)
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        if request.url.path.startswith('/v2/'):response.headers['Cache-Control']='no-store'
        return response

    @app.exception_handler(KeyError)
    async def missing(request,exc):return JSONResponse({'detail':{'code':'NOT_FOUND','message':str(exc)}},status_code=404)
    @app.exception_handler(RequestValidationError)
    async def invalid_schema(request,exc):
        errors=[{'location':list(e['loc']),'message':e['msg'],'type':e['type']} for e in exc.errors()]
        return JSONResponse({'detail':{'code':'INVALID_REQUEST','message':'; '.join(e['message'] for e in errors),'errors':errors}},status_code=422)
    @app.exception_handler(JobConflict)
    async def conflict(request,exc):return JSONResponse({'detail':{'code':'IMMUTABLE_OR_CONFLICT','message':str(exc)}},status_code=409)
    @app.exception_handler(ValueError)
    async def invalid(request,exc):
        message=str(exc).replace(str(directory),'<state>').replace(str(REPO),'<repository>')
        return JSONResponse({'detail':{'code':message.split(':',1)[0] if ':' in message else 'INVALID_REQUEST','message':message}},status_code=422)

    def require(request,roles):
        if request.state.role not in roles:forbidden('ROLE_FORBIDDEN','This operation requires a separate authorized role')

    def record(ident):
        if ident=='historianrca':return {'id':ident,'label':'HistorianRCA · original 90-day TK-101 benchmark','source':'original','status':'PUBLISHED_REFERENCE',
                'scoring_status':'EXTERNAL_SCORING_REQUIRED','public_path':str(REPO/'vendor'/'HistorianRCA'),'private_path':None}
        return store.dataset(ident)

    def detail(ident):
        item=record(ident)
        info=item.get('metadata') or dataset_info(Path(item['public_path']))
        return dict(info,**{k:item[k] for k in ('id','label','source','status','scoring_status')})

    def privileged_job(job):
        p=job['parameters']
        return job['operation'] in PRIVATE_OPS or bool(p.get('episode')) or bool(p.get('shade_episodes')) or bool(job.get('result',{} ) and job['result'].get('evaluator_only'))

    def key_job_ready(job,request):
        # Admin is an engineering/source-authoring role, never a blind role.
        if job['operation']=='independent_evaluation':pass
        elif request.state.role!='evaluator' or job['operation'] not in {'report','summarise'}:return True
        dataset_id=job['parameters'].get('dataset_id')
        if dataset_id is None:
            source=job['parameters'].get('dataset_dir')
            dataset_id=next((d['id'] for d in store.datasets() if d.get('private_path')==source),None)
        if dataset_id is None:return False
        try:store.submission(dataset_id)
        except KeyError:return False
        return True

    def require_frozen_key_job(job,request):
        if not key_job_ready(job,request):
            forbidden('FROZEN_SUBMISSION_REQUIRED','Independent evaluator key access requires frozen analyst claims',409)

    def public_job(job,request):
        result=redact(job)
        if request.state.role=='analyst':
            result['parameters']={k:v for k,v in result['parameters'].items() if k not in ('config','cause_ids')}
        if job.get('error'):
            result['error']['message']=str(result['error']['message']).replace(str(directory),'<state>').replace(str(REPO),'<repository>')
        return result

    @app.get('/v2/health')
    def health(request:Request):return {'status':'ok','version':__version__,'role':request.state.role,'local_only':local}
    @app.get('/v2/capabilities')
    def native_capabilities(request:Request):
        if request.state.role=='analyst':
            return {'role':'analyst','operations':['describe_process','plot','blind_analysis'],'evidence_sources':['raw','grid'],'scoring':'frozen submissions; independent evaluation'}
        return dict(capabilities(REPO),role=request.state.role)
    @app.get('/v2/datasets')
    def datasets():return {'datasets':[redact(record('historianrca')),*[redact({k:v for k,v in d.items() if k!='metadata'}) for d in store.datasets()]]}
    @app.get('/v2/datasets/{ident}')
    def dataset(ident:str):return detail(ident)
    @app.get('/v2/datasets/{ident}/tags')
    def tags(ident:str):return {'tags':detail(ident)['tags']}
    @app.get('/v2/datasets/{ident}/samples')
    def samples(ident:str,tags:str,source:Literal['raw','grid']='grid',start:str|None=None,end:str|None=None,max_points:int=Query(2000,ge=1,le=10000)):
        return query_samples(Path(record(ident)['public_path']),tags.split(','),source,start,end,max_points)
    @app.get('/v2/datasets/{ident}/files')
    def files(ident:str):return {'files':public_files(Path(record(ident)['public_path']))}
    @app.get('/v2/datasets/{ident}/events')
    def events(ident:str,source:Literal['journal','status']='journal',start:str|None=None,end:str|None=None,max_points:int=Query(2000,ge=1,le=10000)):
        try:return query_events(Path(record(ident)['public_path']),source,start,end,max_points)
        except FileNotFoundError:forbidden('EVENT_SOURCE_UNAVAILABLE','This public dataset does not contain the selected measured event source',404)
    @app.get('/v2/datasets/{ident}/files/{name}')
    def file(ident:str,name:str):
        try:path=resolve_public_file(Path(record(ident)['public_path']),name)
        except (ValueError,FileNotFoundError):raise HTTPException(404,detail={'code':'PUBLIC_FILE_UNAVAILABLE','message':'File is not in the public dataset allowlist'})
        return FileResponse(path,filename=path.name)

    @app.post('/v2/jobs',status_code=201)
    def create_job(body:JobRequest,request:Request):
        operation=body.operation;p=dict(body.parameters)
        if operation=='blind_analysis' and p.get('qualification_probe'):require(request,{'admin'})
        if operation in ADMIN_OPS:require(request,{'admin'})
        if operation in PRIVATE_OPS or p.get('episode') or p.get('shade_episodes'):require(request,{'evaluator','admin'})
        if 'dataset_dir' in p:forbidden('PATH_INPUT_FORBIDDEN','Use a registered dataset_id, never a filesystem path',422)
        ident=p.pop('dataset_id',None)
        if ident is not None:
            data=record(ident)
            private=operation in {'validate','make_challenge','report','summarise','independent_evaluation'} or bool(p.get('episode')) or bool(p.get('shade_episodes'))
            path=data['private_path'] if private else data['public_path']
            if path is None:forbidden('EXTERNAL_SCORING_REQUIRED','Original published dataset has no local private generation configuration or key',409)
            p['dataset_dir']=path
        elif operation in DATASET_OPS:forbidden('DATASET_REQUIRED','Choose a registered dataset_id',422)
        if operation=='observability_export':
            if set(p)-{'dataset_dir','profile'} or p.get('profile') not in ('enhanced','sparse'):
                raise ValueError('INVALID_PARAMETERS: export requires profile enhanced or sparse and registered dataset_id')
        elif operation not in {'blind_analysis','independent_evaluation'}:
            from .engine import OPS,_config
            if set(p)-OPS[operation]:raise ValueError('INVALID_PARAMETERS: unknown operation option')
            if operation=='generate':_config(p)
        else:
            allowed={'dataset_dir','model','timeout_seconds','max_budget_usd'}
            if operation=='blind_analysis':allowed.add('qualification_probe')
            if set(p)-allowed:
                raise ValueError('INVALID_PARAMETERS: unknown analysis option')
            if operation=='independent_evaluation':
                try:frozen=store.submission(ident)
                except KeyError:forbidden('FROZEN_SUBMISSION_REQUIRED','Independent evaluation requires frozen claims',409)
                if frozen['judgments']:forbidden('IMMUTABLE_OR_CONFLICT','Existing immutable judgments require a separate review record',409)
        if ident is not None:p['dataset_id']=ident  # Trusted binding; stripped before native dispatch.
        require_frozen_key_job({'operation':operation,'parameters':p},request)
        return public_job(store.create(operation,p,body.idempotency_key),request)

    @app.get('/v2/jobs')
    def jobs(request:Request):return {'jobs':[public_job(j,request) for j in store.list() if (request.state.role!='analyst' or not privileged_job(j)) and key_job_ready(j,request)]}
    @app.get('/v2/jobs/{ident}')
    def job(ident:str,request:Request):
        current=store.get(ident)
        if privileged_job(current):require(request,{'evaluator','admin'})
        require_frozen_key_job(current,request)
        return public_job(current,request)
    @app.post('/v2/jobs/{ident}/cancel')
    def cancel(ident:str,request:Request):
        require(request,{'admin'})
        return public_job(store.request_cancel(ident),request)

    def job_artifacts(ident,request):
        current=store.get(ident)
        if privileged_job(current):require(request,{'admin','evaluator'})
        require_frozen_key_job(current,request)
        # Only the canonical identity read from the durable store enters a path.
        # A request ID is a lookup key, never a filesystem component.
        try:artifact_id=UUID(current['id'])
        except (ValueError,TypeError,AttributeError):forbidden('ARTIFACT_UNAVAILABLE','Job artifact identity is invalid',404)
        if str(artifact_id)!=current['id']:forbidden('ARTIFACT_UNAVAILABLE','Job artifact identity is not canonical',404)
        root=directory/'artifacts'/str(artifact_id)
        result=current.get('result') or {};allowed={}
        for name in ('plot.png','PROCESS_DESCRIPTION.md','FAULT_ANSWER_KEY.md'):
            if name!=result.get('artifact'):continue
            path=root/name
            if path.is_file() and not path.is_symlink():allowed[name]=path
        if current['operation']=='blind_analysis':
            analysis_files={'submission.csv','analysis_notes.md'}
            if request.state.role in ('admin','evaluator'):
                analysis_files|={'analysis_provenance.json','input_snapshot.json','evidence_queries.jsonl'}
            for name in sorted(analysis_files):
                if name not in result.get('artifacts',[]):continue
                path=root/name
                if path.is_file() and not path.is_symlink():allowed[name]=path
            if request.state.role in ('admin','evaluator'):
                # These bounded broker-owned audit records remain reviewable
                # after a failed invocation, even without a successful result.
                for name in ('input_snapshot.json','provider_status.json'):
                    path=root/name
                    if path.is_file() and not path.is_symlink():allowed[name]=path
        if current['operation']=='independent_evaluation' and request.state.role in ('admin','evaluator'):
            for name in ('evaluation_proposals.json','evaluation_provenance.json','provider_status.json'):
                if name not in result.get('artifacts',[]):continue
                path=root/name
                if path.is_file() and not path.is_symlink():allowed[name]=path
        # Failed native checks retain inspectable public data, explicitly unqualified.
        if (root/'public').is_dir():
            for value in public_files(root/'public'):allowed[value['name']]=resolve_public_file(root/'public',value['name'])
        if request.state.role in ('admin','evaluator'):
            for name in ('validation.json','engineering_validation.json'):
                for folder in (root/'private'/'metadata',root/'private'):
                    path=folder/name
                    if path.is_file() and not path.is_symlink():allowed[name]=path;break
        for name,path in allowed.items():
            if not path.resolve().is_relative_to(root.resolve()) or any(p.is_symlink() for p in (path,*path.parents)):
                forbidden('ARTIFACT_PATH_FORBIDDEN','Unsafe artifact path')
        return current,allowed

    @app.get('/v2/jobs/{ident}/files')
    def job_files(ident:str,request:Request):
        current,allowed=job_artifacts(ident,request)
        values=[]
        for name,path in sorted(allowed.items()):
            digest=hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
            values.append({'name':name,'size_bytes':path.stat().st_size,'sha256':digest.hexdigest()})
        return {'files':values,'job_state':current['state'],'qualified':current['state']=='succeeded' and (current.get('result') or {}).get('passed') is True}

    @app.get('/v2/jobs/{ident}/files/{name}')
    def job_file(ident:str,name:str,request:Request):
        _,allowed=job_artifacts(ident,request)
        if name not in allowed:forbidden('ARTIFACT_UNAVAILABLE','Artifact is not available to this role',404)
        path=allowed[name]
        return FileResponse(path,filename=path.name)

    def parse_submission(text):
        try:frame=pd.read_csv(StringIO(text),dtype=str).fillna('')
        except Exception as exc:raise ValueError('INVALID_SUBMISSION: malformed CSV') from exc
        required={'start_utc','end_utc','kind','root_cause','evidence_tags'}
        if not required<=set(frame.columns):raise ValueError('INVALID_SUBMISSION: native submission columns required')
        if 'cause_correct' in frame and frame['cause_correct'].str.strip().ne('').any():raise ValueError('SELF_ADJUDICATION_FORBIDDEN: analyst cannot set cause_correct')
        if 'cause_correct' in frame:frame=frame.drop(columns=['cause_correct'])
        return frame.to_csv(index=False)

    @app.post('/v2/datasets/{ident}/submissions',status_code=201)
    def freeze(ident:str,body:SubmissionRequest):
        record(ident)
        return store.freeze_submission(ident,parse_submission(body.csv))
    @app.get('/v2/datasets/{ident}/submission')
    def submission(ident:str):record(ident);return store.submission(ident)

    def native_score(ident):
        data=record(ident)
        if data['private_path'] is None or data['scoring_status']=='EXTERNAL_SCORING_REQUIRED':
            forbidden('EXTERNAL_SCORING_REQUIRED','The published HistorianRCA answer key is private; no official local score is available',409)
        current=store.submission(ident)
        from historiansim.challenge import load_scoring_key
        from historiansim.scoring import score_submission
        frame=pd.read_csv(StringIO(current['csv']),dtype=str).fillna('');frame['cause_correct']=''
        for judgment in current['judgments']:
            if 0<=judgment['row']-2<len(frame):frame.loc[judgment['row']-2,'cause_correct']='Y' if judgment['correct'] else 'N'
        folder=directory/'scoring';folder.mkdir(exist_ok=True)
        # Each evaluation owns a mode-0600 derived CSV. Concurrent requests must
        # never truncate or replace another evaluation's claims/judgments.
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.csv',dir=folder) as stream:
            frame.to_csv(stream,index=False);stream.flush()
            scored=score_submission(load_scoring_key(Path(data['private_path'])),Path(stream.name))
        scored['detail']=scored['detail'].to_dict('records')
        return scored

    @app.get('/v2/datasets/{ident}/score')
    def score(ident:str,request:Request):
        result=native_score(ident)
        return result if request.state.role in ('admin','evaluator') else redact(result)
    @app.post('/v2/datasets/{ident}/adjudicate')
    def adjudicate(ident:str,body:AdjudicationRequest,request:Request):
        require(request,{'admin','evaluator'})
        result=native_score(ident);matched={r['row'] for r in result['detail']}
        if any(j.row not in matched for j in body.judgments):raise ValueError('INVALID_JUDGMENT: row is not a matched native fault claim')
        store.adjudicate(ident,[j.model_dump() for j in body.judgments])
        return native_score(ident)

    ui=Path(__file__).resolve().parents[1]/'native_ui'
    if ui.exists():
        app.mount('/native',StaticFiles(directory=ui),name='native-assets')
        @app.get('/',openapi_extra={'security':[]})
        def index():return FileResponse(ui/'index.html')
    default_openapi=app.openapi
    def authenticated_openapi():
        schema=default_openapi()
        schema.setdefault('components',{}).setdefault('securitySchemes',{})['NativeRoleBearer']={
            'type':'http','scheme':'bearer',
            'description':'Separate administrator, analyst and evaluator role tokens configured on the server. Network mode always requires a token. Trusted loopback engineering mode may explicitly run without tokens; it grants administrator access and is not blind analysis.'}
        schema['security']=[{'NativeRoleBearer':[]}]
        return schema
    app.openapi=authenticated_openapi
    return app
