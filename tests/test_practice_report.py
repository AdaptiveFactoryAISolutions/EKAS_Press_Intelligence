"""A report must explain saved evidence, including missing/poor-quality observations."""
from copy import deepcopy
import hashlib
import json
import pandas as pd
import pytest


@pytest.fixture
def evidence(tmp_path):
    folder=tmp_path/'public';folder.mkdir()
    rows=[]
    for tag,values in {
        'SIC-1500.PV':[8,8,8], 'TI-WASH':[60,59,60],
        'COUNT-STROKES':[0,468,476], 'COUNT-PRODUCED':[0,459,467],
        'COUNT-PACKED':[0,450,459], 'COUNT-WASHER':[0,6,6],
        'COUNT-DISCHARGE':[0,0,0], 'COUNT-PACK-QUEUE':[0,3,2],
        'COUNT-REJECTED':[0,0,0],
    }.items():
        for t,value in zip(['00:00:00','00:59:00','00:59:59'],values):
            rows.append(dict(tag=tag,timestamp=pd.Timestamp('2024-03-01T'+t+'Z'),value=value,quality=0))
    pd.DataFrame(rows).to_parquet(folder/'historian_10s.parquet')
    pd.DataFrame([{'tag':n,'description':n,'units':'test'} for n in {r['tag'] for r in rows}]).to_csv(folder/'tags.csv',index=False)
    # A misleading/truncated grid must not supply the report totals.
    pd.DataFrame({'timestamp':[pd.Timestamp('2024-03-01T00:59:00Z')],'COUNT-PACKED':[450]}).to_parquet(folder/'historian_60s.parquet')
    job={'id':'saved-run','operation':'generate','state':'succeeded','created_at':'2026-10-29T18:42:46Z',
         'updated_at':'2026-10-29T18:42:57Z','parameters':{'practice':True,'config':{
             'unit':'stamping_line','seed':7,'time':{'days':1/24,'start':'2024-03-01T00:00:00','timezone':'UTC'},
             'params':{'speed_spm':8,'washer_temperature_c':60,'stations':10,'packers':2,'packing_rate_per_min':6},
             'episodes':{'n_faults':0,'cause_ids':None}}},
         'result':{'dataset_id':'saved-run','qualification_status':'UNQUALIFIED_PRACTICE',
                   'engineering_acceptance':{'passed':True},'native_validation_passed':False,
                   'validation':[{'name':'noise_is_colored','passed':False,'severity':'error'}]}}
    binding={'config_sha256':'config-hash','model_sha256':'model-hash','revision':1,'draft_id':'draft'}
    return folder,job,binding


def report(evidence):
    from ekas_press_intelligence.native.practice_report import build_report
    folder,job,binding=evidence
    return build_report(job,binding,folder)


def test_primary_end_counts_and_provenance_not_grid(evidence):
    folder,_,_=evidence;before=(folder/'historian_10s.parquet').read_bytes()
    r=report(evidence)
    assert r['signals']['COUNT-PACKED']['last']['value']==459
    assert r['signals']['COUNT-PRODUCED']['last']['value']==467
    assert r['balance']['status']=='agrees' and r['balance']['in_line']==8
    assert r['balance']['produced_minus_packed']==8
    assert r['provenance']['primary_sha256']==hashlib.sha256(before).hexdigest()
    assert (folder/'historian_10s.parquet').read_bytes()==before
    assert r['validation']['native_status']=='findings'
    assert r['validation']['findings'][0]['name']=='noise_is_colored'
    assert r['language']['conformance']=='NOT_FULLY_REVIEWED'
    assert not any(x in json.dumps(r) for x in ('private_path','true_cause'))


@pytest.mark.parametrize('change',['missing','bad_final','noninteger','different_time','negative','null_final'])
def test_no_invented_balance_from_unusable_final_counter(evidence,change):
    folder,_,_=evidence;p=folder/'historian_10s.parquet';d=pd.read_parquet(p);d['value']=d['value'].astype(float)
    ix=d.index[d.tag=='COUNT-PACKED'][-1]
    if change=='missing':d=d[d.tag!='COUNT-PACKED']
    elif change=='bad_final':d.loc[ix,'quality']=2
    elif change=='null_final':d.loc[ix,'value']=float('nan')
    elif change=='noninteger':d.loc[ix,'value']=458.5
    elif change=='negative':d.loc[ix,'value']=-1
    else:d.loc[ix,'timestamp']=pd.Timestamp('2024-03-01T00:59:58Z')
    d.to_parquet(p);r=report(evidence)
    assert r['balance']['status']=='unavailable'
    assert r['balance']['in_line'] is None
    if change in ('bad_final','null_final'):assert r['signals']['COUNT-PACKED']['last'] is None


def test_changed_case_targets_and_unknown_checks_are_not_healthy_defaults(evidence):
    _,job,_=evidence
    job['parameters']['config']['params']['speed_spm']=6
    job['parameters']['config']['episodes']={'n_faults':1,'cause_ids':['LINE-FEED-SLIP']}
    job['result'].pop('validation');job['result'].pop('engineering_acceptance')
    job['result'].pop('native_validation_passed')
    r=report(evidence)
    assert r['setup']['speed_spm']==6 and r['setup']['fault_count']==1
    assert r['validation']['engineering_status']=='unavailable'
    assert r['validation']['native_status']=='unavailable'
    assert r['setup']['case']=='Fault practice'
    assert r['setup']['requested_cases']==['Feeder slipping']


def test_plot_memory_bounded_but_statistics_cover_all_records(evidence):
    folder,_,_=evidence
    d=pd.DataFrame({'tag':['TI-WASH']*10001,'timestamp':pd.date_range('2024-03-01',periods=10001,freq='s',tz='UTC'),
                    'value':[60.]*9999+[99.,61.],'quality':[0]*10001})
    d.to_parquet(folder/'historian_10s.parquet');r=report(evidence);s=r['signals']['TI-WASH']
    assert s['good_count']==10001 and s['maximum']==99 and s['last']['value']==61
    assert len(s['points'])<=960 and s['plot_reduced'] is True
    assert any(p['value']==99 for p in s['points'])


def test_report_refuses_symlinked_source(evidence,tmp_path):
    folder,_,_=evidence;p=folder/'historian_10s.parquet';target=tmp_path/'elsewhere.parquet';p.rename(target);p.symlink_to(target)
    with pytest.raises(ValueError,match='PUBLIC_FILE_FORBIDDEN'):report(evidence)


def test_rejected_parts_are_not_reported_as_parts_remaining(evidence):
    folder,_,_=evidence;p=folder/'historian_10s.parquet';frame=pd.read_parquet(p)
    frame.loc[frame.index[frame.tag=='COUNT-PACKED'][-1],'value']=454
    frame.loc[frame.index[frame.tag=='COUNT-REJECTED'][-1],'value']=5
    frame.to_parquet(p);r=report(evidence)
    assert r['balance']['status']=='agrees'
    assert r['balance']['in_line']==8 and r['balance']['rejected']==5
    assert r['balance']['produced_minus_packed']==13


def test_missing_rejection_count_cannot_confirm_balance(evidence):
    folder,_,_=evidence;p=folder/'historian_10s.parquet';frame=pd.read_parquet(p)
    frame[frame.tag!='COUNT-REJECTED'].to_parquet(p)
    assert report(evidence)['balance']['status']=='unavailable'


def test_fractional_second_readings_keep_actual_time_order(evidence):
    folder,_,_=evidence
    data=pd.DataFrame({'tag':['SIC-1500.PV']*3,'timestamp':pd.to_datetime(['2024-03-01T00:00:00Z','2024-03-01T00:00:00.500Z','2024-03-01T00:00:01Z'],format='ISO8601'),
                       'value':[8.,8.1,8.2],'quality':[0,0,0]})
    data.to_parquet(folder/'historian_10s.parquet');s=report(evidence)['signals']['SIC-1500.PV']
    assert s['first']['value']==8.
    assert [p['value'] for p in s['points']]==[8.,8.1,8.2]


@pytest.fixture
def api_run(tmp_path,evidence,monkeypatch):
    from fastapi.testclient import TestClient
    from ekas_press_intelligence.native.api import create_native_app
    app=create_native_app(tmp_path/'state',start_worker=False,tokens={'admin':'admin','reader':'analyst','judge':'evaluator'})
    # This is a report contract fixture, not a test of native generation.
    # Keep it usable in the stock-runtime core layer as well as the line layer.
    from ekas_press_intelligence.native import line_api
    monkeypatch.setattr(line_api,'runtime_ready',lambda:True)
    monkeypatch.setattr(line_api,'native_config',lambda _:deepcopy(evidence[1]['parameters']['config']))
    with TestClient(app) as c:
        c.headers['Authorization']='Bearer admin'
        config=c.get('/v2/line/preset').json()['config']
        d=c.post('/v2/line/drafts',json={'name':'Report example','config':config,'step':8}).json()
        j=c.post('/v2/line/drafts/'+d['id']+'/run',json={'revision':1,'idempotency_key':'report-test'}).json()
        assert 'id' in j,j
        store=app.state.store;store.claim('test-worker')
        folder,original,_=evidence;result=deepcopy(original['result']);result['dataset_id']=j['id']
        store.finish(j['id'],result,dataset={'id':j['id'],'job_id':j['id'],'public_path':str(folder),'private_path':None,'source':'generated','status':'UNVALIDATED'})
        yield c,store,j['id']


def test_endpoint_only_admin_completed_guided_generation(api_run):
    c,store,ident=api_run;path='/v2/jobs/'+ident+'/practice-report'
    assert c.get(path).status_code==200
    for role in ('reader','judge'):
        assert c.get(path,headers={'Authorization':'Bearer '+role}).status_code==403
    pending=store.create('generate',{'practice':True})
    assert c.get('/v2/jobs/'+pending['id']+'/practice-report').status_code==409
    store.claim('test');store.fail(pending['id'],'TEST','Failed run')
    assert c.get('/v2/jobs/'+pending['id']+'/practice-report').status_code==409
    other=store.create('generate',{'practice':True});store.claim('test');store.finish(other['id'],{})
    assert c.get('/v2/jobs/'+other['id']+'/practice-report').status_code==409
    assert c.get('/v2/jobs/not-a-job/practice-report').status_code==404
