"""EKAS ORIGINAL local module API. Evaluator broker owns truth; RCA is isolated."""
import copy
import os
from pathlib import Path
from statistics import mean
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from .contracts.api import (RunRequest, AssessmentRequest, InvestigationRequest,
    SubmissionRequest, ActionRequest, VerifyRequest, CaseResponse, RunResponse,
    ScoreResponse, VerificationResponse, FinancialRequest, FinancialResponse,
    AssessmentResponse, GapsResponse, AssetsResponse, SignalsResponse,
    CaseEvidenceResponse, SubmissionResponse)
from .domain import assets, signals, profile_signals, catalog
from .observability.model import assess, sensor_gaps
from .simulator.engine import simulate
from .benchmark.evaluator import score
from .rca.verification import verify
from .sandbox import investigate_isolated, IsolationUnavailable
from .storage import Store, Conflict
from .intent import interpret, ClarificationRequired
from .rca.campaign import detect_windows
from .financial import estimate
from .simulator.upstream import verify_runtime


def observed_windows(evidence):
    """Evidence-only windows; no truth schedule is used to select investigations."""
    return [dict(start_s=start,end_s=min(end-1,evidence['context']['duration_s']-1),
                 label=f'Observed change window {i+1}')
            for i,(start,end) in enumerate(detect_windows(evidence))]


def evidence_window(evidence,start,end):
    duration=evidence['context']['duration_s']
    if not 0<=start<end<duration:
        raise HTTPException(422,detail={'code':'PERIOD_UNAVAILABLE','duration_s':duration})
    result={k:v for k,v in evidence.items() if k!='samples'}
    result['context']=dict(evidence['context'],analysis_start_s=start,analysis_end_s=end)
    result['samples']=[s for s in evidence['samples'] if start<=s['t']<=end]
    result['baseline_samples']=[s for s in evidence['samples'] if s['t']<min(7200,start)]
    result['baseline_quality']=[r for r in evidence.get('quality',[]) if r.get('t',-1)<min(7200,start)]
    for collection in ('events','quality'):
        if collection in evidence:
            result[collection]=[r for r in evidence[collection] if start<=r.get('t',-1)<=end]
    return result


def create_app(state_dir=None):
    verify_runtime(Path(__file__).resolve().parents[2])
    directory=Path(state_dir or os.environ.get('EKAS_STATE_DIR','work/runtime')).resolve()
    directory.mkdir(parents=True,exist_ok=True);directory.chmod(0o700)
    store=Store(directory/'module.sqlite');vault=Store(directory/'evaluator.sqlite')
    app=FastAPI(title='EKAS Press Intelligence',version='1.0.0',
        description='Synthetic press observability and governed evidence-only RCA. No real machine connection.')
    ui=Path(__file__).parent/'ui'
    if ui.exists():
        app.mount('/static',StaticFiles(directory=ui),name='static')

    @app.middleware('http')
    async def security_headers(request,call_next):
        response=await call_next(request)
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Cache-Control']='no-store'
        return response

    def get(kind,ident,private=False):
        try:return (vault if private else store).get(kind,ident)
        except KeyError:raise HTTPException(404,detail={'code':'RESOURCE_UNAVAILABLE','kind':kind,'id':ident})

    def save(kind,ident,payload):
        try:return store.create(kind,ident,payload)
        except Conflict as exc:raise HTTPException(409,detail={'code':'IMMUTABLE_RECORD','message':str(exc)})

    @app.get('/',include_in_schema=False)
    def home():return FileResponse(ui/'index.html')

    @app.get('/favicon.ico',include_in_schema=False)
    def favicon():return Response(status_code=204)

    @app.get('/v1/health')
    def health():return {'status':'ok','version':'1.0.0','data_source':'SYNTHETIC'}

    @app.get('/v1/assets',response_model=AssetsResponse)
    def list_assets():return {'assets':assets()}

    @app.get('/v1/signals',response_model=SignalsResponse)
    def list_signals():return {'signals':signals()}

    @app.post('/v1/observability/assess',response_model=AssessmentResponse,status_code=201)
    def assessment(request:AssessmentRequest):
        available=request.signals if request.signals is not None else profile_signals(request.profile)
        unknown=set(available)-{s['signal_id'] for s in signals()}
        if unknown:raise HTTPException(422,detail={'code':'SIGNAL_UNAVAILABLE','signals':sorted(unknown)})
        result=assess(available);ident=str(uuid4())
        result.update(assessment_id=ident,profile=request.profile,available_signals=available)
        save('assessment',ident,result)
        save('sensor_gap',ident,{'assessment_id':ident,'recommendations':sensor_gaps(available)})
        return result

    @app.get('/v1/sensor-gaps',response_model=GapsResponse)
    def gaps(profile:str=Query('sparse',pattern='^(sparse|enhanced)$')):
        return {'profile':profile,'recommendations':sensor_gaps(profile_signals(profile))}

    @app.post('/v1/benchmark/run',response_model=RunResponse,status_code=201)
    def run(request:RunRequest):
        ident=str(uuid4())
        generated=simulate(**request.model_dump())
        vault.create('truth',ident,generated.truth)
        vault.create('configuration',ident,request.model_dump())
        save('dataset',ident,generated.evidence)
        result=dict(run_id=ident,profile=request.profile,duration_s=request.duration_s,
                    hidden_truth_status='HIDDEN',windows=observed_windows(generated.evidence),
                    source='SYNTHETIC',sample_count=len(generated.evidence['samples']))
        save('run',ident,result)
        return result

    @app.get('/v1/datasets/{run_id}/samples')
    def samples(run_id:str,start_s:int=0,end_s:int|None=None,step:int=Query(10,ge=1,le=3600)):
        data=get('dataset',run_id)
        end=end_s if end_s is not None else data['context']['duration_s']-1
        selected=evidence_window(data,start_s,end)['samples']
        if len(selected[::step])>20000:raise HTTPException(422,detail={'code':'TOO_MANY_SAMPLES','message':'Increase step or shorten period'})
        return {'context':data['context'],'samples':selected[::step]}

    @app.post('/v1/rca/investigate',response_model=CaseResponse,status_code=201)
    def investigation(request:InvestigationRequest):
        data=get('dataset',request.run_id)
        # Scope is explicit in the API. Questions describe an objective, never a cause lookup.
        try:intent=interpret(request.question,request.asset_id,request.start_s,request.end_s)
        except ClarificationRequired as exc:
            raise HTTPException(422,detail={'code':'CLARIFICATION_REQUIRED','message':str(exc)})
        window=evidence_window(data,request.start_s,request.end_s)
        try:result=investigate_isolated(window,request.question)
        except IsolationUnavailable as exc:raise HTTPException(503,detail={'code':'DIAGNOSTIC_ISOLATION_UNAVAILABLE','message':str(exc)})
        if result.get('error'):raise HTTPException(422,detail=result)
        ident=str(uuid4())
        names={e['id']:ident+':'+e['id'] for e in result['evidence']}
        for e in result['evidence']:e['id']=names[e['id']]
        for group in ('hypotheses','alternatives'):
            for h in result[group]:
                h['supporting_evidence']=[names.get(ref,ref) for ref in h['supporting_evidence']]
        result.update(case_id=ident,run_id=request.run_id,asset_id=request.asset_id,question=request.question,intent=intent)
        save('case',ident,result)
        return result

    @app.get('/v1/rca/cases/{case_id}',response_model=CaseResponse)
    def case(case_id:str):return get('case',case_id)

    @app.get('/v1/rca/cases/{case_id}/evidence',response_model=CaseEvidenceResponse)
    def case_evidence(case_id:str):
        current=get('case',case_id);data=get('dataset',current['run_id'])
        p=current['period'];window=evidence_window(data,p['start_s'],p['end_s'])
        stride=max(1,len(window['samples'])//600)
        return {'evidence':current['evidence'],'samples':window['samples'][::stride],
                'events':[e for e in data['events'] if p['start_s']<=e['t']<=p['end_s']],
                'maintenance':data['maintenance'],'quality':data['quality'],
                'pfmea':data['pfmea'],'control_plan':data['control_plan']}

    @app.post('/v1/rca/cases/{case_id}/financial',response_model=FinancialResponse)
    def financial(case_id:str,request:FinancialRequest):
        current=get('case',case_id);data=get('dataset',current['run_id'])
        period=current['period'];rows=evidence_window(data,period['start_s'],period['end_s'])['samples']
        valid=[r for r in rows if isinstance(r.get('part_count'),(int,float))]
        if len(valid)<2 or len(valid)/len(rows)<.95:
            raise HTTPException(422,detail={'code':'FINANCIAL_EVIDENCE_UNAVAILABLE'})
        duration=valid[-1]['t']-valid[0]['t']
        capacity=current.get('kpis',{}).get('baseline_spm')
        if capacity is None:raise HTTPException(422,detail={'code':'BASELINE_UNAVAILABLE'})
        lost=max(0,capacity*duration/60-(valid[-1]['part_count']-valid[0]['part_count']))
        result=estimate({'lost_units':lost},{'contribution_per_unit':request.contribution_per_unit,
            'currency':request.currency,'provenance':{'assumption_source':request.assumption_source,
            'case_id':case_id,'period':period,'calculation':'baseline SPM × exposure / 60 − observed good count increase',
            'qualification':'Capacity opportunity, not realized demand or verified savings.'}})
        ident=str(uuid4());result['financial_id']=ident;save('financial',ident,result)
        current['financial_context']=result;store.update('case',case_id,current,'Financial assumptions and opportunity estimate')
        return result

    @app.post('/v1/benchmark/{run_id}/submit',response_model=SubmissionResponse,status_code=201)
    def submission(run_id:str,request:SubmissionRequest):
        data=get('dataset',run_id);truth=get('truth',run_id,private=True)
        claims=[c.model_dump(mode='json') for c in request.claims]
        for c in claims:
            if c['end_s']>=data['context']['duration_s']:raise HTTPException(422,detail={'code':'PERIOD_UNAVAILABLE'})
        # References originate only from persisted evidence, never client assertions.
        refs={}
        for entry in store_records_for_run(store,run_id):
            refs.update({f['id']:f for f in entry['evidence']})
        result=score(truth,claims,refs)
        try:store.freeze_benchmark(run_id,{'claims':claims,'immutable':True},result)
        except Conflict as exc:raise HTTPException(409,detail={'code':'IMMUTABLE_RECORD','message':str(exc)})
        return {'run_id':run_id,'submission':claims,'score':result,'hidden_truth_status':'SCORED'}

    @app.get('/v1/benchmark/{run_id}/score',response_model=ScoreResponse)
    def benchmark_score(run_id:str):
        get('run',run_id)
        try:return store.get('score',run_id)
        except KeyError:raise HTTPException(409,detail={'code':'NOT_SCORED'})

    @app.get('/v1/benchmark/{run_id}/truth')
    def reveal(run_id:str):
        benchmark_score(run_id)
        return {'run_id':run_id,'truth':get('truth',run_id,private=True),'qualification':'Synthetic evaluator truth; reveal permitted only after frozen submission and score.'}

    @app.post('/v1/rca/cases/{case_id}/actions',status_code=201)
    def action(case_id:str,request:ActionRequest):
        current=get('case',case_id);rid=current['run_id'];conf=get('configuration',rid,private=True)
        original=get('truth',rid,private=True)
        if request.target_event_class not in {c['event_class'] for c in catalog()}:
            raise HTTPException(422,detail={'code':'TARGET_UNAVAILABLE'})
        if request.repair_at_s>=conf['duration_s']-600:raise HTTPException(422,detail={'code':'INSUFFICIENT_POST_ACTION_EXPOSURE'})
        schedule=[]
        for item in original:
            end=item['end_s']
            if item['event_class']==request.target_event_class and item['start_s']<request.repair_at_s<end:
                end=request.repair_at_s
            schedule.append({'event_class':item['event_class'],'start_s':item['start_s'],'end_s':end})
        replay=simulate(**conf,events=schedule)
        aid=str(uuid4());vault.create('intervention',aid,replay.evidence)
        record=dict(request.model_dump(),action_id=aid,case_id=case_id,
                    status='APPLIED_SYNTHETIC_INTERVENTION',qualification='A replayed repair is not proof of improvement.')
        # Never expose whether selected target matched private truth.
        save('action',aid,record)
        current['diagnosis_state']='CORRECTIVE_ACTION';store.update('case',case_id,current,'Synthetic corrective action recorded')
        return record

    @app.post('/v1/rca/cases/{case_id}/verify',response_model=VerificationResponse)
    def verification(case_id:str,request:VerifyRequest):
        current=get('case',case_id);action=get('action',request.action_id)
        if action['case_id']!=case_id:raise HTTPException(422,detail={'code':'ACTION_SCOPE_MISMATCH'})
        if not request.before_end_s<action['repair_at_s']<=request.after_start_s:
            raise HTTPException(422,detail={'code':'WINDOWS_MUST_STRADDLE_ACTION'})
        before=evidence_window(get('dataset',current['run_id']),request.before_start_s,request.before_end_s)
        after=evidence_window(get('intervention',request.action_id,private=True),request.after_start_s,request.after_end_s)
        result=verify(before,after,dict(action,sustained_duration_s=request.sustained_duration_s))
        ident=str(uuid4());result.update(verification_id=ident,action_id=request.action_id)
        save('verification',ident,result)
        current['diagnosis_state']='SUSTAINED' if result['sustained'] else 'VERIFICATION'
        current['verification']=result;store.update('case',case_id,current,'Controlled verification result')
        return result

    return app


def store_records_for_run(store,run_id):
    with store._connect() as db:
        import json
        rows=db.execute("SELECT payload FROM resources WHERE kind='case'").fetchall()
    return [r for row in rows if (r:=json.loads(row[0])).get('run_id')==run_id]
