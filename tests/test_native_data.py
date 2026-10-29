from pathlib import Path
import pandas as pd
import pytest
from ekas_press_intelligence.native.data import dataset_info, query_samples, resolve_public_file


def test_real_parquet_queries_preserve_quality_and_nulls(tmp_path):
    pd.DataFrame({'tag':['A','A','B'], 'timestamp':pd.to_datetime(['2024-01-01','2024-01-02','2024-01-02'],utc=True), 'value':[1.,float('nan'),3.], 'quality':[0,1,0]}).to_parquet(tmp_path/'historian.parquet')
    pd.DataFrame({'timestamp':pd.to_datetime(['2024-01-01','2024-01-02'],utc=True),'A':[1.,float('nan')]}).to_parquet(tmp_path/'historian_60s.parquet')
    pd.DataFrame({'tag':['A','B']}).to_csv(tmp_path/'tags.csv',index=False)
    info=dataset_info(tmp_path)
    assert info['raw']['rows']==3
    rows=query_samples(tmp_path,['A'],source='raw')['rows']
    assert rows[1]['quality']==1 and rows[1]['value'] is None
    assert rows[0]['timestamp'].endswith('Z')
    assert query_samples(tmp_path,['A'],max_points=1)['truncated']
    with pytest.raises(ValueError): query_samples(tmp_path,['unknown'])


def test_paths_and_bounds(tmp_path):
    for n in ['../truth.json','metadata/ground_truth.json','FAULT_ANSWER_KEY.md','/etc/passwd']:
        with pytest.raises(ValueError): resolve_public_file(tmp_path,n)
    (tmp_path/'tags.csv').symlink_to('/etc/passwd')
    with pytest.raises(ValueError): resolve_public_file(tmp_path,'tags.csv')
    with pytest.raises(ValueError): query_samples(tmp_path,['A'],max_points=10001)


def test_original_historianrca_matches_actual_parquet():
    import pyarrow.parquet as pq
    root=Path(__file__).resolve().parents[1]/'vendor/HistorianRCA'
    info=dataset_info(root)
    assert info['raw_file']=='historian.parquet'
    assert info['raw']['rows']==5650781
    assert info['grid']['rows']==129600
    assert info['scoring_status']=='EXTERNAL_SCORING_REQUIRED'
    tag=info['tags'][0]['tag']
    actual=pq.read_table(root/'historian.parquet',filters=[('tag','=',tag)]).to_pandas().head(5)
    rows=query_samples(root,[tag],source='raw',max_points=5)['rows']
    assert [r['value'] for r in rows]==actual['value'].tolist()
    assert [r['quality'] for r in rows]==actual['quality'].tolist()
    assert query_samples(root,[tag],source='grid',max_points=2)['aggregation']=='none'


def test_timestamp_and_source_rejections(tmp_path):
    with pytest.raises(ValueError): query_samples(tmp_path,[],source='other')
    with pytest.raises(ValueError): query_samples(tmp_path,[],max_points=True)


def test_real_query_bounds_no_filling_and_naive_rejected(tmp_path):
    dates=pd.to_datetime(['2024-01-01','2024-01-03'],utc=True)
    pd.DataFrame({'tag':['A','A'],'timestamp':dates,'value':[1.,3.],'quality':[0,2]}).to_parquet(tmp_path/'historian.parquet')
    pd.DataFrame({'timestamp':dates,'A':[1.,float('nan')]}).to_parquet(tmp_path/'historian_60s.parquet')
    pd.DataFrame({'tag':['A']}).to_csv(tmp_path/'tags.csv',index=False)
    assert query_samples(tmp_path,['A'],source='raw',start='2024-01-02T00:00:00Z',end='2024-01-02T23:59:59Z')['rows']==[]
    result=query_samples(tmp_path,['A'],source='raw',start='2024-01-03T00:00:00Z')
    assert len(result['rows'])==1 and result['rows'][0]['quality']==2
    with pytest.raises(ValueError): query_samples(tmp_path,['A'],start='2024-01-01')
    with pytest.raises(ValueError): query_samples(tmp_path,['A'],start='2024-01-03T00:00:00Z',end='2024-01-01T00:00:00Z')


def test_only_safe_cycle_event_artifact_is_public(tmp_path):
    from ekas_press_intelligence.native.data import public_files
    pd.DataFrame({'timestamp':pd.to_datetime(['2024-01-01'],utc=True),'COUNT-271':[1]}).to_parquet(tmp_path/'cycle_events.parquet')
    (tmp_path/'exact_private_event_ledger.json').write_text('{"cause":"private"}')
    files=public_files(tmp_path)
    assert [f['name'] for f in files]==['cycle_events.parquet']
    assert files[0]['size_bytes']>0 and len(files[0]['sha256'])==64

def test_query_preserves_nanosecond_interval_boundaries(tmp_path):
    dates=pd.to_datetime(['2024-01-01T00:00:00.000000000Z','2024-01-01T00:00:00.000000001Z'])
    pd.DataFrame({'timestamp':dates,'A':[1.,2.]}).to_parquet(tmp_path/'historian_60s.parquet')
    pd.DataFrame({'timestamp':dates,'tag':['A','A'],'value':[1.,2.],'quality':[0,0]}).to_parquet(tmp_path/'historian.parquet')
    pd.DataFrame({'tag':['A']}).to_csv(tmp_path/'tags.csv',index=False)
    for source in ('raw','grid'):
        rows=query_samples(tmp_path,['A'],source=source,start=dates[1].isoformat())['rows']
        assert len(rows)==1
        assert rows[0].get('A',rows[0].get('value'))==2.

def test_measured_event_queries_preserve_codes_quality_and_time(tmp_path):
    from ekas_press_intelligence.native.data import query_events
    dates=pd.to_datetime(['2024-01-01T00:00:00.001Z','2024-01-01T00:00:00.002Z','2024-01-01T00:00:00.003Z'])
    pd.DataFrame({'timestamp':dates,'event_code':[2,1,-1],'count':[1.,1.,float('nan')],'quality':[0,0,2]}).to_parquet(tmp_path/'cycle_event_journal.parquet')
    result=query_events(tmp_path,max_points=2)
    assert result['truncated'] and len(result['rows'])==2
    result=query_events(tmp_path,start='2024-01-01T00:00:00.002000001Z')
    assert result['rows']==[{'timestamp':'2024-01-01T00:00:00.003000Z','event_code':-1,'count':None,'quality':2}]
    assert result['aggregation']=='none'
    with pytest.raises(ValueError):query_events(tmp_path,source='../metadata')
    with pytest.raises(ValueError):query_events(tmp_path,max_points=10001)
