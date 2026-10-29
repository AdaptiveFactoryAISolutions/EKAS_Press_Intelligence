"""Streaming availability profiles preserve existing native records exactly."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from ekas_press_intelligence.native.observability import execute_observability,profile_contract
from ekas_press_intelligence.native.data import public_files,resolve_public_file
ROOT=Path(__file__).resolve().parents[1]
PLANT='heated_stirred_tank'


@pytest.mark.parametrize('profile,code',[('sparse','OBSERVABILITY_SCHEMA_MISMATCH'),('enhanced','OBSERVABILITY_CANNOT_RESTORE')])
def test_missing_required_channels_explain_historical_source_recovery(source,tmp_path,profile,code):
    folder,contract=source
    missing=next(n for n in contract['plant_tags'] if n not in contract['withheld_tags'])
    tags=pd.read_csv(folder/'tags.csv');tags[tags['tag']!=missing].to_csv(folder/'tags.csv',index=False)
    before=public_files(folder)
    with pytest.raises(ValueError) as error:
        execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':profile},tmp_path/'output',ROOT)
    message=str(error.value)
    assert message.startswith(code+':') and missing in message
    assert 'earlier model version' in message and 'verified runtime' in message
    assert public_files(folder)==before and not (tmp_path/'output').exists()


def test_sparse_without_declared_withholding_discloses_no_restriction(source,tmp_path,monkeypatch):
    import hashlib
    from ekas_press_intelligence.native import observability
    folder,original=source;contract=dict(original,withheld_tags=[])
    contract.pop('contract_sha256')
    contract['contract_sha256']=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    monkeypatch.setattr(observability,'profile_contract',lambda *_:contract)
    before=public_files(folder)
    result=execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse'},tmp_path/'export',ROOT)
    exported=tmp_path/'export/public'
    manifest=json.loads((exported/'SOURCE_AVAILABILITY.json').read_text())
    assert manifest['restriction_applied'] is False and result['restriction_applied'] is False
    assert 'no withheld channels' in manifest['availability_note']
    assert 'no withheld channels' in (exported/'SOURCE_AVAILABILITY.md').read_text()
    for name in ('historian_10s.parquet','historian_60s.parquet','cycle_events.parquet'):
        pd.testing.assert_frame_equal(pd.read_parquet(folder/name),pd.read_parquet(exported/name))
    assert public_files(folder)==before and manifest['resimulated'] is False

@pytest.fixture
def source(tmp_path):
    contract=profile_contract(PLANT,ROOT)
    tags=contract['plant_tags'];count=1500
    folder=tmp_path/'public';folder.mkdir()
    dates=pd.date_range('2024-01-01',periods=count,freq='min',tz='UTC')
    values=np.arange(count*len(tags),dtype=np.float32).reshape(count,len(tags))/4
    values[::71,0]=np.nan
    raw=pd.DataFrame({'timestamp':np.repeat(dates,len(tags)),'tag':pd.Categorical(np.tile(tags,count)),'value':values.reshape(-1),'quality':np.arange(count*len(tags),dtype=np.int64)%3})
    raw.to_parquet(folder/'historian_10s.parquet',index=False,row_group_size=19000)
    grid=pd.DataFrame({'timestamp':dates,**{tag:values[:,i] for i,tag in enumerate(tags)}})
    grid.to_parquet(folder/'historian_60s.parquet',index=False,row_group_size=600)
    grid.iloc[::2].to_parquet(folder/'historian_120s.parquet',index=False)
    grid[['timestamp',tags[0],contract['withheld_tags'][0]]].to_parquet(folder/'cycle_events.parquet',index=False)
    pd.DataFrame({'tag':tags,'description':['Public physical observation']*len(tags)}).to_csv(folder/'tags.csv',index=False)
    (folder/'CHALLENGE.md').write_text('Public task. Every event has a single, known root cause, and every root cause can be determined from the files in this folder alone.')
    (folder/'PROCESS_DESCRIPTION.md').write_text('Actual source process description. No fault schedule.')
    (folder/'PFD.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>Physical design inventory</text></svg>')
    (folder/'LICENSE').write_text('Public license retained')
    (folder/'unknown_private.txt').write_text('Do not export this unallowlisted input')
    return folder,contract


def test_sparse_real_parquet_rows_columns_quality_and_metadata_exact(source,tmp_path):
    folder,contract=source;before=public_files(folder)
    result=execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse'},tmp_path/'sparse',ROOT)
    public=tmp_path/'sparse/public';retained=[n for n in contract['plant_tags'] if n not in contract['withheld_tags']]
    raw=pd.read_parquet(folder/'historian_10s.parquet');expected=raw[raw['tag'].isin(retained)].reset_index(drop=True)
    pd.testing.assert_frame_equal(pd.read_parquet(public/'historian_10s.parquet'),expected)
    for filename in ['historian_60s.parquet','historian_120s.parquet','cycle_events.parquet']:
        original=pd.read_parquet(folder/filename)
        pd.testing.assert_frame_equal(pd.read_parquet(public/filename),original[[n for n in original.columns if n=='timestamp' or n in retained]])
    assert pd.read_csv(public/'tags.csv')['tag'].tolist()==retained
    assert (public/'PFD.svg').read_bytes()==(folder/'PFD.svg').read_bytes()
    assert not (public/'unknown_private.txt').exists()
    assert 'can be determined from the files in this folder alone' not in (public/'CHALLENGE.md').read_text()
    manifest=json.loads((public/'SOURCE_AVAILABILITY.json').read_text())
    assert manifest['profile']=='sparse' and manifest['source_digests']==before
    assert result['public_directory']=='public' and result['retained_tag_count']==len(retained)
    assert public_files(folder)==before
    assert resolve_public_file(public,'SOURCE_AVAILABILITY.md').is_file()


def test_enhanced_is_byte_exact_and_cannot_restore_sparse_input(source,tmp_path):
    folder,contract=source
    execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'enhanced'},tmp_path/'enhanced',ROOT)
    for name in ['historian_10s.parquet','historian_60s.parquet','historian_120s.parquet','tags.csv','cycle_events.parquet']:
        assert (tmp_path/'enhanced/public'/name).read_bytes()==(folder/name).read_bytes()
    execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse'},tmp_path/'sparse',ROOT)
    with pytest.raises(ValueError,match='CANNOT_RESTORE'):
        execute_observability({'dataset_dir':str(tmp_path/'sparse/public'),'plant':PLANT,'profile':'enhanced'},tmp_path/'invalid',ROOT)


def test_streaming_export_never_loads_entire_parquet(source,tmp_path,monkeypatch):
    folder,_=source
    def forbidden(*args,**kwargs):raise AssertionError('Whole-file Parquet read is forbidden')
    monkeypatch.setattr(pq,'read_table',forbidden)
    monkeypatch.setattr(pd,'read_parquet',forbidden)
    result=execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse'},tmp_path/'streamed',ROOT)
    assert result['streaming']['batch_rows']==16384
    assert result['streaming']['max_batch_rows']<=16384


def test_profile_source_and_path_rejections(source,tmp_path):
    folder,_=source
    for parameters in [{'dataset_dir':str(folder),'plant':PLANT,'profile':'imagined'},{'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse','withheld':['TIC-101.PV']}]:
        with pytest.raises(ValueError):execute_observability(parameters,tmp_path/'bad',ROOT)
    with pytest.raises(ValueError):execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse'},folder/'nested',ROOT)
    (folder/'FAULT_ANSWER_KEY.md').write_text('Private source is forbidden')
    with pytest.raises(ValueError):execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'sparse'},tmp_path/'private',ROOT)


def test_enhanced_rejects_tag_dictionary_claiming_missing_grid_channels(source,tmp_path):
    folder,contract=source
    path=folder/'historian_60s.parquet'
    frame=pd.read_parquet(path).drop(columns=[contract['plant_tags'][0]])
    frame.to_parquet(path,index=False)
    with pytest.raises(ValueError,match='CANNOT_RESTORE'):
        execute_observability({'dataset_dir':str(folder),'plant':PLANT,'profile':'enhanced'},tmp_path/'missing',ROOT)


PRESS_CONTRACT_PROBE = r'''
"""Actual verified metadata + public Parquet export parity; no physical generation."""
from pathlib import Path
import json,os,shutil,sys,uuid
import numpy as np
import pandas as pd
root=Path(sys.argv[1]);base=Path(sys.argv[2]);runtime=root/'work'/('observability-test-runtime-'+uuid.uuid4().hex)
sys.path.insert(0,str(root/'scripts'))
from prepare_native_runtime import prepare_runtime
try:
    prepare_runtime(root,runtime);os.environ['EKAS_NATIVE_RUNTIME']=str(runtime)
    from ekas_press_intelligence.native.observability import profile_contract,execute_observability
    contract=profile_contract('stamping_press',root)
    from historiansim.plants import get_plant
    native=get_plant('stamping_press')
    assert contract['withheld_tags']==list(native.hard_mode_withheld)
    assert set(contract['journal_status_tags'].values()).isdisjoint(contract['withheld_tags'])
    tags=contract['plant_tags'];folder=base/'public';folder.mkdir(parents=True)
    dates=pd.date_range('2024-01-01',periods=4,freq='min',tz='UTC')
    values=np.arange(4*len(tags),dtype=np.float32).reshape(4,len(tags));values[2,0]=np.nan
    raw=pd.DataFrame({'timestamp':np.repeat(dates,len(tags)),'tag':pd.Categorical(np.tile(tags,4)),'value':values.reshape(-1),'quality':np.arange(4*len(tags))%3})
    raw.to_parquet(folder/'historian_10s.parquet',index=False)
    grid=pd.DataFrame({'timestamp':dates,**{tag:values[:,i] for i,tag in enumerate(tags)}});grid.to_parquet(folder/'historian_60s.parquet',index=False)
    pd.DataFrame({'tag':tags,'description':['Existing measured acquisition channel']*len(tags)}).to_csv(folder/'tags.csv',index=False)
    (folder/'CHALLENGE.md').write_text('Public native storage-fixture task; no physics qualification claim.')
    (folder/'PROCESS_DESCRIPTION.md').write_text('Public storage fixture for verified native plant tag contracts.')
    journal=pd.DataFrame({'timestamp':pd.date_range('2024-01-01',periods=6,freq='ms',tz='UTC'),'event_code':np.array([0,1,-1,2,1,-1],dtype=np.int8),'count':[0.,1.,np.nan,1.,2.,np.nan],'quality':np.array([0,0,2,0,0,1],dtype=np.uint8)})
    journal.to_parquet(folder/'cycle_event_journal.parquet',index=False)
    import historiansim.pipeline as pipeline
    def forbidden(*_,**__):raise AssertionError('Exporter must not generate another physical run')
    pipeline.generate=forbidden
    result=execute_observability({'dataset_dir':str(folder),'plant':'stamping_press','profile':'sparse'},base/'sparse',root)
    public=base/'sparse/public';visible=[tag for tag in tags if tag not in contract['withheld_tags']]
    assert (public/'cycle_event_journal.parquet').read_bytes()==(folder/'cycle_event_journal.parquet').read_bytes()
    pd.testing.assert_frame_equal(pd.read_parquet(public/'historian_10s.parquet'),raw[raw['tag'].isin(visible)].reset_index(drop=True))
    pd.testing.assert_frame_equal(pd.read_parquet(public/'historian_60s.parquet'),grid[['timestamp',*visible]])
    assert result['retained_tag_count']==len(visible)
    manifest=json.loads((public/'SOURCE_AVAILABILITY.json').read_text())
    assert manifest['withheld_tags']==list(native.hard_mode_withheld) and manifest['resimulated'] is False
    print(json.dumps({'actual_native_tag_count':len(tags),'actual_withheld_tag_count':len(contract['withheld_tags']),'retained_tag_count':len(visible),'journal_byte_exact':True,'native_contract_sha256':contract['contract_sha256']}))
finally:
    if runtime.exists():shutil.rmtree(runtime)
'''


def test_verified_press_contract_and_journal_exact_copy_in_isolated_runtime(tmp_path):
    import os,subprocess,sys
    # Script uses the actual prepare/verify routines and native PLANT metadata;
    # synthetic Parquet values exercise export parity only, never physics claims.
    env=dict(os.environ);env.pop('EKAS_NATIVE_RUNTIME',None)
    process=subprocess.run([sys.executable,'-c',PRESS_CONTRACT_PROBE,str(ROOT),str(tmp_path/'press')],env=env,capture_output=True,text=True,timeout=180)
    assert process.returncode==0,process.stderr
    evidence=json.loads(process.stdout.splitlines()[-1])
    assert evidence['journal_byte_exact'] and evidence['actual_withheld_tag_count']>0
    assert evidence['retained_tag_count']==evidence['actual_native_tag_count']-evidence['actual_withheld_tag_count']
