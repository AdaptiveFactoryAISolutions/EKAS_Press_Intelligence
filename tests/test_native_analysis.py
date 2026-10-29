"""Isolation, protocol and frozen-claim regressions for real native blind analysis."""
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd
import pytest
from ekas_press_intelligence.native.analysis import AnalysisUnavailable, build_broker_command, evidence_command, execute_analysis, validate_submission
from ekas_press_intelligence.native.evidence_tools import EvidenceTools
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def challenge(tmp_path):
    p=tmp_path/'challenge';p.mkdir()
    dates=pd.to_datetime(['2024-01-01','2024-01-02'],utc=True)
    pd.DataFrame({'timestamp':dates,'tag':['A','A'],'value':[1.,2.],'quality':[0,2]}).to_parquet(p/'historian_10s.parquet')
    pd.DataFrame({'timestamp':dates,'A':[1.,float('nan')]}).to_parquet(p/'historian_60s.parquet')
    pd.DataFrame({'tag':['A'],'description':['Measured process quantity']}).to_csv(p/'tags.csv',index=False)
    (p/'CHALLENGE.md').write_text('Find abnormal events from public evidence only. No cause list supplied.')
    (p/'PROCESS_DESCRIPTION.md').write_text('A is a measured process quantity.')
    return p


def test_tools_reject_arbitrary_sources_and_options(challenge):
    tools=EvidenceTools(challenge)
    assert tools.call('samples',{'tags':['A'],'source':'raw'})['rows'][1]['quality']==2
    for name,args in [('read_document',{'name':'../metadata/ground_truth.json'}),('read_document',{'name':'/etc/passwd'}),('samples',{'tags':['A'],'path':'/etc/passwd'}),('execute',{'code':'print(1)'}),('read_document',{'name':'FAULT_ANSWER_KEY.md'}),('read_document',{'name':'README.md'})]:
        with pytest.raises(ValueError):tools.call(name,args)


def test_evidence_namespace_uses_selected_interpreter_without_site_packages(challenge,tmp_path):
    import sysconfig
    cmd=evidence_command(challenge,tmp_path/'abi-audit',ROOT)
    assert cmd[cmd.index('-I')-1]=='/runtime/bin/python3'
    assert '-S' in cmd
    assert 'EVIDENCE_ABI_MISMATCH' in cmd[-1]
    mounts=[(cmd[i+1],cmd[i+2]) for i,v in enumerate(cmd) if v=='--ro-bind']
    assert (str(Path(sys.executable).resolve()),'/runtime/bin/python3') in mounts
    assert any(dst.startswith('/runtime/lib/python') and dst.endswith('/encodings') for _,dst in mounts)
    assert all(not dst.startswith('/runtime/') or 'site-packages' not in dst for _,dst in mounts)
    assert not any(src==sysconfig.get_path('stdlib') for src,_ in mounts)


def test_actual_sandbox_rpc_transport_and_negative_access(challenge,tmp_path):
    audit=tmp_path/'audit.jsonl';audit.touch()
    cmd=evidence_command(challenge,audit,ROOT)
    requests=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2024-11-05'}}, {'jsonrpc':'2.0','id':2,'method':'tools/list'}, {'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'read_document','arguments':{'name':'/etc/passwd'}}}, {'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'samples','arguments':{'tags':['A'],'source':'raw'}}}]
    process=subprocess.run(cmd,input=''.join(json.dumps(x)+'\n' for x in requests),text=True,capture_output=True,timeout=30)
    assert process.returncode==0,process.stderr
    responses=[json.loads(line) for line in process.stdout.splitlines()]
    assert len(responses)==4
    assert responses[2]['result']['isError']
    assert json.loads(responses[3]['result']['content'][0]['text'])['rows'][1]['quality']==2
    assert set(t['name'] for t in responses[1]['result']['tools'])=={'metadata','tags','samples','read_document','public_files','window_statistics','events'}
    assert audit.read_text()
    probe=cmd[:-1]+["import sys,json;sys.path.insert(0,'/dependencies');import numpy,pandas,pyarrow;print(json.dumps({'version':list(sys.version_info[:2]),'prefix':sys.prefix,'paths':sys.path}))"]
    checked=subprocess.run(probe,text=True,capture_output=True,timeout=30)
    assert checked.returncode==0,checked.stderr
    runtime=json.loads(checked.stdout)
    assert runtime['version']==list(sys.version_info[:2]) and runtime['prefix']=='/runtime'
    assert all('site-packages' not in p and 'dist-packages' not in p for p in runtime['paths'])


def test_frozen_claims_cannot_self_adjudicate():
    csv='start_utc,end_utc,kind,root_cause,evidence_tags,notes\n2024-01-01T00:00:00Z,2024-01-02T00:00:00Z,fault,Valve mechanical obstruction,A,Observed response\n'
    assert validate_submission(csv)['rows']==1
    with pytest.raises(ValueError): validate_submission(csv.replace('notes\n','cause_correct\n'))
    with pytest.raises(ValueError): validate_submission(csv.replace('2024-01-01T00:00:00Z','nonsense'))


def test_evidence_events_preserve_measured_quality_and_forbid_private_options(challenge):
    dates=pd.to_datetime(['2024-01-01T00:00:00.001Z','2024-01-01T00:00:00.002Z'])
    pd.DataFrame({'timestamp':dates,'event_code':[1,-1],'count':[1.,float('nan')],'quality':[0,2]}).to_parquet(challenge/'cycle_event_journal.parquet')
    tools=EvidenceTools(challenge)
    result=tools.call('events',{'source':'journal','max_points':2})
    assert result['rows'][1]['event_code']==-1 and result['rows'][1]['count'] is None
    assert result['rows'][1]['quality']==2 and result['aggregation']=='none'
    assert tools.call('metadata',{})['event_files']['journal']=='cycle_event_journal.parquet'
    with pytest.raises(ValueError):tools.call('events',{'path':'metadata/ground_truth.json'})
    with pytest.raises(ValueError):tools.call('events',{'source':'private'})


def test_broker_restricted_capabilities_and_missing_provider(challenge,tmp_path,monkeypatch):
    cmd=build_broker_command('/bin/false',tmp_path/'mcp.json',model=None,budget=1)
    assert '--restricted' in cmd and '--safe-mode' not in cmd
    settings=json.loads(cmd[cmd.index('--settings')+1]);assert settings['claudeMdExcludes']==['**'] and settings['autoMemoryEnabled'] is False
    assert cmd[cmd.index('--tools')+1]==''
    assert '--strict-mcp-config' in cmd and '--no-session-persistence' in cmd
    assert '--dangerously-skip-permissions' not in cmd
    monkeypatch.setenv('EKAS_CLAUDE_EXECUTABLE','/missing/claude')
    with pytest.raises(AnalysisUnavailable):execute_analysis({'dataset_dir':str(challenge)},tmp_path/'out',ROOT)


def test_actual_negative_namespace_proof_clears_credentials(challenge,tmp_path,monkeypatch):
    from ekas_press_intelligence.native.analysis import verify_isolation
    monkeypatch.setenv('ANTHROPIC_API_KEY','qualification-marker-not-a-credential')
    proof=verify_isolation(challenge,tmp_path/'proof-audit.jsonl',ROOT)
    assert all(proof['denied_paths'].values())
    assert proof['network_denied'] and proof['environment_clear']


def test_private_or_symlink_challenge_is_rejected(challenge,tmp_path):
    (challenge/'metadata').mkdir()
    with pytest.raises(AnalysisUnavailable,match='ANALYSIS_INPUT_FORBIDDEN'):
        execute_analysis({'dataset_dir':str(challenge)},tmp_path/'privateout',ROOT)
    (challenge/'metadata').rmdir()
    (challenge/'CHALLENGE.md').unlink();(challenge/'CHALLENGE.md').symlink_to('/etc/passwd')
    with pytest.raises(AnalysisUnavailable,match='ANALYSIS_INPUT_FORBIDDEN'):
        evidence_command(challenge,tmp_path/'audit',ROOT)


@pytest.fixture
def mocked_analysis_executable(monkeypatch):
    # This test replaces preflight and run_broker: the placeholder is never run.
    monkeypatch.setenv('EKAS_CLAUDE_EXECUTABLE',sys.executable)


def test_provider_errors_remain_typed_and_no_claims_frozen(challenge,tmp_path,monkeypatch,mocked_analysis_executable):
    import ekas_press_intelligence.native.analysis as analysis
    profile=tmp_path/'profile';profile.mkdir();(profile/'.credentials.json').write_text('{"accessToken":"qualification-only","refreshToken":"never-copy"}')
    monkeypatch.setattr(analysis,'_provider_preflight',lambda *_:('qualification fake-cli',str(profile)))
    monkeypatch.setattr(analysis,'verify_isolation',lambda *_:{'network_denied':True})
    monkeypatch.setattr(analysis,'evidence_command',lambda *_:['/bin/false'])
    messages=[{'type':'system','subtype':'init','tools':[*analysis.ALLOWED_TOOLS,'StructuredOutput'],'plugins':[]},{'type':'result','subtype':'error_during_execution','is_error':True}]
    def fail_request(cmd,prompt,cwd,env,timeout,allowed,status_path):
        credential=json.loads((Path(env['CLAUDE_CONFIG_DIR'])/'.credentials.json').read_text())
        assert 'refreshToken' not in credential
        assert env['CLAUDE_CODE_DISABLE_AUTO_MEMORY']=='1'
        Path(status_path).write_text('{"exit_code":1}')
        return messages[0],messages[1],{'exit_code':1}
    monkeypatch.setattr(analysis,'run_broker',fail_request)
    target=tmp_path/'provider-failed'
    with pytest.raises(AnalysisUnavailable,match='PROVIDER_REQUEST_FAILED'):
        execute_analysis({'dataset_dir':str(challenge)},target,ROOT)
    assert not (target/'submission.csv').exists()
    assert (target/'provider_status.json').exists()


def test_window_statistics_real_parquet_matches_pandas(tmp_path):
    import numpy as np
    tools_path=tmp_path/'statistics';tools_path.mkdir()
    stamps=pd.date_range('2024-01-01',periods=9000,freq='min',tz='UTC')
    values=np.sin(np.arange(9000)/100)+100
    quality=np.zeros(9000,dtype=int);quality[::37]=2
    grid_values=values.copy();grid_values[quality!=0]=np.nan
    pd.DataFrame({'timestamp':stamps,'tag':['A']*9000,'value':values,'quality':quality}).to_parquet(tools_path/'historian_10s.parquet')
    pd.DataFrame({'timestamp':stamps,'A':grid_values}).to_parquet(tools_path/'historian_60s.parquet')
    pd.DataFrame({'tag':['A']}).to_csv(tools_path/'tags.csv',index=False)
    tools=EvidenceTools(tools_path)
    for source in ['raw','grid']:
        result=tools.call('window_statistics',{'tags':['A'],'source':source,'start':'2024-01-01T00:00:00Z','end':'2024-01-08T00:00:00Z','bin_seconds':86400})
        expected=pd.Series(grid_values,index=stamps).resample('D').agg(['mean','min','max','count'])
        assert result['derived'] and result['truncated'] is False
        assert result['observations_scanned']==9000
        for actual,(_,row) in zip(result['rows'],expected.iterrows()):
            assert actual['mean']==pytest.approx(row['mean'],abs=1e-10)
            assert actual['min']==row['min'] and actual['max']==row['max']
            assert actual['valid_count']==row['count']
        if source=='raw':assert sum(row['quality_counts'].get('2',0) for row in result['rows'])==int((quality==2).sum())
        else:assert sum(row['null_count'] for row in result['rows'])==int((quality==2).sum())
    with pytest.raises(ValueError):tools.call('window_statistics',{'tags':['A'],'path':'/etc/passwd'})
    with pytest.raises(ValueError):tools.call('window_statistics',{'tags':['A'],'bin_seconds':60,'start':'2020-01-01T00:00:00Z','end':'2024-01-01T00:00:00Z'})


def test_oversized_rpc_line_is_read_in_bounded_chunks_and_next_request_survives(monkeypatch):
    import io
    from types import SimpleNamespace
    from ekas_press_intelligence.native.evidence_tools import serve
    class GuardedInput(io.BytesIO):
        def readline(self,size=-1):
            assert 0<size<=131073,'RPC parser attempted an unbounded line allocation'
            return super().readline(size)
        def __iter__(self):return self
        def __next__(self):
            value=self.readline()
            if not value:raise StopIteration
            return value
    source=GuardedInput(b'x'*1_000_000+b'\n'+b'{"jsonrpc":"2.0","id":7,"method":"ping"}\n')
    output=io.StringIO()
    monkeypatch.setattr(sys,'stdin',SimpleNamespace(buffer=source));monkeypatch.setattr(sys,'stdout',output)
    serve('/unused-public-path')
    responses=[json.loads(line) for line in output.getvalue().splitlines()]
    assert responses[0]['error']['code']==-32600
    assert responses[1]=={'jsonrpc':'2.0','id':7,'result':{}}


def test_statistics_interval_does_not_round_requested_precision(challenge):
    result=EvidenceTools(challenge).call('window_statistics',{'tags':['A'],'source':'raw','start':'2024-01-01T00:00:00.000000001Z','end':'2024-01-02T00:00:00Z'})
    assert sum(row['count'] for row in result['rows'])==1


def test_public_snapshot_rejects_changes_during_copy(challenge,tmp_path,monkeypatch):
    import ekas_press_intelligence.native.analysis as analysis
    original=analysis.shutil.copy2
    def changed(source,destination):
        if Path(source).name=='CHALLENGE.md':Path(source).write_text('Changed during acquisition')
        return original(source,destination)
    monkeypatch.setattr(analysis.shutil,'copy2',changed)
    public=tmp_path/'snapshot';public.mkdir()
    with pytest.raises(AnalysisUnavailable,match='EVIDENCE_SNAPSHOT_CHANGED'):
        analysis.copy_public_snapshot(challenge,public)


def test_snapshot_provenance_stays_bound_to_actual_copy(challenge,tmp_path):
    import ekas_press_intelligence.native.analysis as analysis
    public=tmp_path/'snapshot';public.mkdir()
    manifest=analysis.copy_public_snapshot(challenge,public)
    (challenge/'CHALLENGE.md').write_text('Origin changed after acquisition')
    analysis.verify_public_snapshot(public,manifest)
    assert manifest==analysis.public_files(public)
    copied=public/'CHALLENGE.md';assert copied.stat().st_mode&0o777==0o400
    copied.chmod(0o600);copied.write_text('Snapshot changed during provider')
    with pytest.raises(AnalysisUnavailable,match='EVIDENCE_SNAPSHOT_CHANGED'):
        analysis.verify_public_snapshot(public,manifest)


@pytest.mark.parametrize('mutate_snapshot',[False,True])
def test_analysis_binds_provider_snapshot_not_later_origin(challenge,tmp_path,monkeypatch,mutate_snapshot):
    import ekas_press_intelligence.native.analysis as analysis
    monkeypatch.setenv('EKAS_CLAUDE_EXECUTABLE','/bin/false')
    monkeypatch.setattr(analysis,'_provider_preflight',lambda *_:('mock-provider',None))
    monkeypatch.setattr(analysis,'broker_environment',lambda *_:{})
    monkeypatch.setattr(analysis,'verify_isolation',lambda *_:{'test_only':True})
    observed={}
    def transport(public,*_):observed['public']=public;return ['/bin/false']
    monkeypatch.setattr(analysis,'evidence_command',transport)
    target=tmp_path/'analysis'
    before=analysis.public_files(challenge)
    def provider(*_):
        changed=(observed['public'] if mutate_snapshot else challenge)/'CHALLENGE.md'
        changed.chmod(0o600);changed.write_text('Changed during provider invocation')
        entries=[{'tool':name,'status':'ok'} for name in ('metadata','read_document','window_statistics')]
        (target/'evidence_queries.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in entries))
        return {'tools':analysis.ALLOWED_TOOLS},{'structured_output':{'submission_csv':','.join(analysis.SUBMISSION_FIELDS)+'\n','notes':'Test-only provider mock.','coverage':'No qualification claim.'}},{'exit_code':0}
    monkeypatch.setattr(analysis,'run_broker',provider)
    parameters={'dataset_dir':str(challenge),'qualification_probe':True}
    if mutate_snapshot:
        with pytest.raises(AnalysisUnavailable,match='EVIDENCE_SNAPSHOT_CHANGED'):execute_analysis(parameters,target,ROOT)
        assert not (target/'submission.csv').exists()
        assert (target/'input_snapshot.json').is_file()
    else:
        execute_analysis(parameters,target,ROOT)
        provenance=json.loads((target/'analysis_provenance.json').read_text())
        assert provenance['input_files']==before
        assert provenance['input_files']!=analysis.public_files(challenge)


def test_evidence_stdlib_excludes_customization_and_rejects_external_symlinks(challenge,tmp_path,monkeypatch):
    import ekas_press_intelligence.native.analysis as analysis
    stdlib=tmp_path/'selected-stdlib';stdlib.mkdir()
    outside=tmp_path/'private-code';outside.write_text('private sentinel')
    for name in ('sitecustomize.py','usercustomize.pyc'):
        (stdlib/name).symlink_to(outside)
    monkeypatch.setattr(analysis.sysconfig,'get_path',lambda name:str(stdlib))
    cmd=evidence_command(challenge,tmp_path/'customization-audit',ROOT)
    assert str(outside) not in cmd
    (stdlib/'unexpected.py').symlink_to(outside)
    with pytest.raises(AnalysisUnavailable,match='ISOLATION_UNAVAILABLE'):
        evidence_command(challenge,tmp_path/'escape-audit',ROOT)
