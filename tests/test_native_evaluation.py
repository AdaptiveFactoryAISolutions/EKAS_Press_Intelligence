"""Fresh-evaluator and bounded provider-broker regressions."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,sys,time
import pytest
from ekas_press_intelligence.native.analysis import AnalysisUnavailable,run_broker
from ekas_press_intelligence.native.evaluation import execute_evaluation,validate_judgments
ROOT=Path(__file__).resolve().parents[1]


def test_judgments_exact_rows_and_boolean_only():
    assert validate_judgments({'judgments':[{'row':2,'correct':True,'reason':'Same failed component and mechanism'}],'notes':''},[2])[0]['correct']
    for value in [{'judgments':[{'row':2,'correct':'Y','reason':'not boolean'}],'notes':''},{'judgments':[{'row':3,'correct':True,'reason':'Wrong row'}],'notes':''}]:
        with pytest.raises(ValueError):validate_judgments(value,[2])


def test_hash_mismatch_precedes_key_access_or_provider(tmp_path):
    with pytest.raises(ValueError,match='SUBMISSION_HASH_MISMATCH'):
        execute_evaluation({'dataset_dir':'/missing/private','submission_csv':'immutable','submission_sha256':'0'*64},tmp_path/'out',ROOT)


def script(tmp_path,body):
    path=tmp_path/'provider.py';path.write_text(body)
    return [sys.executable,str(path)]


@pytest.mark.parametrize('tools,plugins',[(['Bash'],[]),(['StructuredOutput'],[{'name':'unexpected-plugin'}])])
def test_broker_denies_unexpected_init_before_following_output(tmp_path,tools,plugins):
    command=script(tmp_path,'import json,time\nprint('+repr(json.dumps({'type':'system','subtype':'init','tools':tools,'plugins':plugins}))+',flush=True)\ntime.sleep(30)\n')
    begin=time.monotonic()
    with pytest.raises(AnalysisUnavailable,match='ISOLATION_UNAVAILABLE'):
        run_broker(command,'prompt',tmp_path,os.environ.copy(),10,[],tmp_path/'status.json')
    assert time.monotonic()-begin<5


@pytest.mark.parametrize('stream',['stdout','stderr'])
def test_broker_output_capacity_is_bounded(tmp_path,stream):
    command=script(tmp_path,f'import sys\nsys.{stream}.write("X"*100000)\nsys.{stream}.flush()\n')
    with pytest.raises(AnalysisUnavailable,match='PROVIDER_OUTPUT_LIMIT'):
        run_broker(command,'prompt',tmp_path,os.environ.copy(),10,[],tmp_path/'status.json',max_stdout=4096,max_stderr=4096)


@pytest.mark.parametrize('separate_session',[False,True])
def test_broker_timeout_kills_owned_descendant_group(tmp_path,separate_session):
    child=tmp_path/'child.pid'
    code='import subprocess,sys,time\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],start_new_session='+repr(separate_session)+')\nopen('+repr(str(child))+',"w").write(str(p.pid))\ntime.sleep(60)\n'
    command=script(tmp_path,code)
    with pytest.raises(AnalysisUnavailable,match='PROVIDER_TIMEOUT'):
        run_broker(command,'prompt',tmp_path,os.environ.copy(),1,[],tmp_path/'status.json')
    pid=int(child.read_text());status=Path(f'/proc/{pid}/status')
    assert not status.exists() or 'State:\tZ' in status.read_text()
    audit=json.loads((tmp_path/'status.json').read_text())
    assert audit['owned_descendants_observed']>=1 and audit['cleanup_complete'] is True


def native_private_key(tmp_path):
    folder=tmp_path/'private';(folder/'metadata').mkdir(parents=True)
    cfg={'time':{'start':'2024-01-01T00:00:00','timezone':'UTC'}}
    truth={'episodes':[{'episode_id':'EP-TEST','class':'fault','true_onset_s':86400,'true_end_s':172800,'true_root_cause':'TEST-PUMP','true_root_cause_label':'Supply pump bearing wear','failed_component':'P-101','mechanism':'Bearing wear increases shaft friction and motor current'}]}
    (folder/'metadata/manifest.json').write_text(json.dumps({'config':cfg}))
    (folder/'metadata/ground_truth.json').write_text(json.dumps(truth))
    return folder


@pytest.fixture
def mocked_evaluator_executable(monkeypatch):
    # These contracts mock preflight and run_broker; no provider is executed.
    # Use an explicit local placeholder instead of depending on host Claude.
    monkeypatch.setenv('EKAS_CLAUDE_EXECUTABLE',sys.executable)


def test_native_pairing_feeds_only_matched_immutable_claim_to_fresh_evaluator(tmp_path,monkeypatch,mocked_evaluator_executable):
    import ekas_press_intelligence.native.evaluation as evaluation
    folder=native_private_key(tmp_path)
    text='start_utc,end_utc,kind,root_cause,evidence_tags,notes\n2024-01-02T00:00:00Z,2024-01-03T00:00:00Z,fault,P-101 bearing wear causes high current,JI-101,Frozen claim\n2024-01-10T00:00:00Z,2024-01-11T00:00:00Z,fault,Unmatched alternative,JI-101,False positive\n'
    monkeypatch.setattr(evaluation,'_provider_preflight',lambda *_:('fake-for-unit-test',None))
    monkeypatch.setattr(evaluation,'broker_environment',lambda *_:{})
    def runner(command,prompt,cwd,env,timeout,allowed,path):
        assert allowed==[] and command[command.index('--tools')+1]==''
        assert json.loads(command[command.index('--mcp-config')+1])=={'mcpServers':{}}
        payload=json.loads(prompt)
        assert [p['row'] for p in payload['matched_claims']]==[2]
        assert payload['matched_claims'][0]['matched_key']['failed_component']=='P-101'
        assert str(folder) not in prompt and 'analyst_notes' not in prompt
        return {'tools':['StructuredOutput'],'plugins':[],'model':'unit-test'},{'structured_output':{'judgments':[{'row':2,'correct':True,'reason':'Same component and bearing-wear mechanism'}],'notes':'Independent fixture judgment'},'is_error':False},{'exit_code':0}
    monkeypatch.setattr(evaluation,'run_broker',runner)
    result=execute_evaluation({'dataset_dir':str(folder),'submission_csv':text,'submission_sha256':hashlib.sha256(text.encode()).hexdigest()},tmp_path/'out',ROOT)
    assert result['matched_rows']==[2] and result['judgments'][0]['correct'] is True
    assert result['status']=='PROPOSALS_REQUIRE_AUTHORIZED_PERSISTENCE'


def test_worker_sigterm_reaps_broker_owned_children(tmp_path):
    child=tmp_path/'descendant.pid'
    provider=tmp_path/'provider.py'
    provider.write_text('import json,subprocess,sys,time\np=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"])\nopen('+repr(str(child))+',"w").write(str(p.pid))\nprint(json.dumps({"type":"system","subtype":"init","tools":["StructuredOutput"],"plugins":[]}),flush=True)\ntime.sleep(60)\n')
    parent=tmp_path/'parent.py'
    parent.write_text('import signal,sys,os\nfrom pathlib import Path\nfrom ekas_press_intelligence.native.analysis import run_broker\nsignal.signal(signal.SIGTERM,lambda *_:sys.exit(130))\nrun_broker([sys.executable,'+repr(str(provider))+'],"prompt",'+repr(str(tmp_path))+',os.environ.copy(),60,[],Path('+repr(str(tmp_path/'status.json'))+'))\n')
    process=subprocess.Popen([sys.executable,str(parent)])
    try:
        deadline=time.monotonic()+5
        while not child.exists() and time.monotonic()<deadline:time.sleep(.02)
        assert child.exists()
        process.terminate();assert process.wait(timeout=5)==130
        pid=int(child.read_text());status=Path(f'/proc/{pid}/status')
        assert not status.exists() or 'State:\tZ' in status.read_text()
    finally:
        if process.poll() is None:process.kill();process.wait()


def test_no_matched_claims_never_fabricates_provider_or_judgments(tmp_path,monkeypatch):
    import ekas_press_intelligence.native.evaluation as evaluation
    folder=native_private_key(tmp_path)
    text='start_utc,end_utc,kind,root_cause,evidence_tags,notes\n2024-01-10T00:00:00Z,2024-01-11T00:00:00Z,fault,Incorrect event timing,JI-101,False positive\n'
    def forbidden(*_):raise AssertionError('Provider must not run without matched claims')
    monkeypatch.setattr(evaluation,'_provider_preflight',forbidden)
    result=execute_evaluation({'dataset_dir':str(folder),'submission_csv':text,'submission_sha256':hashlib.sha256(text.encode()).hexdigest()},tmp_path/'out',ROOT)
    assert result['judgments']==[] and result['provider_invoked'] is False
    assert result['status']=='NO_MATCHED_CLAIMS'


@pytest.mark.parametrize('optional_extra',[False,True])
def test_human_native_five_columns_optional_extra_and_discarded_rows(tmp_path,monkeypatch,optional_extra,mocked_evaluator_executable):
    import ekas_press_intelligence.native.evaluation as evaluation
    folder=native_private_key(tmp_path)
    text='start_utc,end_utc,kind,root_cause,evidence_tags,human_comment\nnot-a-time,2024-01-03T00:00:00Z,fault,Invalid timestamp,JI-101,Native parser discards this row\n2024-01-02T00:00:00Z,2024-01-03T00:00:00Z,fault,P-101 bearing wear raises motor current,JI-101,Valid human claim without notes\n'
    if not optional_extra:
        import csv,io
        rows=list(csv.reader(io.StringIO(text)));out=io.StringIO();writer=csv.writer(out,lineterminator='\n')
        writer.writerows(row[:5] for row in rows);text=out.getvalue()
    monkeypatch.setattr(evaluation,'_provider_preflight',lambda *_:('unit-test-only',None))
    monkeypatch.setattr(evaluation,'broker_environment',lambda *_:{})
    def proposed_unit_judgment(command,prompt,cwd,env,timeout,allowed,path):
        payload=json.loads(prompt)
        assert [pair['row'] for pair in payload['matched_claims']]==[3]
        if optional_extra:assert payload['matched_claims'][0]['claim']['human_comment']=='Valid human claim without notes'
        else:assert set(payload['matched_claims'][0]['claim'])=={'start_utc','end_utc','kind','root_cause','evidence_tags'}
        return {'tools':['StructuredOutput'],'plugins':[],'model':'unit-test-only'},{'structured_output':{'judgments':[{'row':3,'correct':True,'reason':'Unit-test proposal for matched item and mechanism'}],'notes':'Mocked proposal contract, not provider proof'},'is_error':False},{'exit_code':0}
    monkeypatch.setattr(evaluation,'run_broker',proposed_unit_judgment)
    result=execute_evaluation({'dataset_dir':str(folder),'submission_csv':text,'submission_sha256':hashlib.sha256(text.encode()).hexdigest()},tmp_path/'out',ROOT)
    assert result['matched_rows']==[3] and result['discarded_rows']==1
    assert result['submission_sha256']==hashlib.sha256(text.encode()).hexdigest()


def test_human_blank_adjudication_column_allowed_nonblank_denied(tmp_path):
    import ekas_press_intelligence.native.evaluation as evaluation
    folder=native_private_key(tmp_path)
    base='start_utc,end_utc,kind,root_cause,evidence_tags,cause_correct\ninvalid,invalid,fault,Bad row,JI-101,'
    for suffix,allowed in [('\n',True),('Y\n',False)]:
        text=base+suffix
        parameters={'dataset_dir':str(folder),'submission_csv':text,'submission_sha256':hashlib.sha256(text.encode()).hexdigest()}
        if allowed:
            result=execute_evaluation(parameters,tmp_path/'blank',ROOT)
            assert result['discarded_rows']==1 and result['judgments']==[]
        else:
            with pytest.raises(ValueError,match='SELF_ADJUDICATION'):
                execute_evaluation(parameters,tmp_path/'selfgrade',ROOT)
