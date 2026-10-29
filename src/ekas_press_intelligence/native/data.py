"""Bounded, evidence-preserving access to public native historian artifacts."""
from __future__ import annotations
import hashlib
import math
import re
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq

FIXED_FILES = frozenset({'SOURCE_AVAILABILITY.md','SOURCE_AVAILABILITY.json','cycle_event_journal.parquet','cycle_events.parquet','historian.parquet','historian_10s.parquet','tags.csv','PROCESS_DESCRIPTION.md','CHALLENGE.md','submission_template.csv','PFD.svg','PFD.png','tk-101-hold-tank.svg','tk-101-hold-tank.png','README.md','CITATION.cff','LICENSE'})

def _allowed(name):
    return isinstance(name,str) and Path(name).name==name and (name in FIXED_FILES or name=='historian_grid_10s.parquet' or re.fullmatch(r'historian_(?:[1-9][0-9]*(?:p[0-9]*[1-9])?|0p[0-9]*[1-9])s\.parquet',name) is not None)

def resolve_public_file(path: Path,name: str)->Path:
    path=Path(path)
    if not _allowed(name): raise ValueError('PUBLIC_FILE_FORBIDDEN: filename is not public')
    # Refuse symlink components, even those pointing back inside the dataset.
    if any(p.is_symlink() for p in (path,*path.parents)): raise ValueError('PUBLIC_FILE_FORBIDDEN: symlink directory')
    p=path/name
    if p.is_symlink(): raise ValueError('PUBLIC_FILE_FORBIDDEN: symlink file')
    if not p.is_file(): raise FileNotFoundError(name)
    if p.resolve().parent!=path.resolve(): raise ValueError('PUBLIC_FILE_FORBIDDEN: path escape')
    return p

def public_files(path: Path)->list[dict]:
    result=[]
    for p in sorted(Path(path).iterdir()):
        if not _allowed(p.name): continue
        p=resolve_public_file(path,p.name)
        h=hashlib.sha256()
        with p.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
        result.append({'name':p.name,'size_bytes':p.stat().st_size,'sha256':h.hexdigest()})
    return result

def _names(path):
    raw=next((n for n in ('historian_10s.parquet','historian.parquet') if (Path(path)/n).exists()),None)
    grids=sorted(p.name for p in Path(path).glob('historian_*s.parquet') if p.name!=raw)
    grid='historian_60s.parquet' if 'historian_60s.parquet' in grids else (grids[0] if grids else None)
    return raw,grid

def _iso(value):
    ts=pd.Timestamp(value)
    if ts.tzinfo is None: raise ValueError('INVALID_TIMESTAMP: UTC offset required')
    return ts.tz_convert('UTC').isoformat().replace('+00:00','Z')

def _stats(path,name):
    if name is None: return None
    p=resolve_public_file(path,name); f=pq.ParquetFile(p)
    idx=f.schema_arrow.names.index('timestamp'); lows=[]; highs=[]
    for k in range(f.metadata.num_row_groups):
        st=f.metadata.row_group(k).column(idx).statistics
        if st and st.has_min_max: lows.append(st.min); highs.append(st.max)
    return {'file':name,'rows':f.metadata.num_rows,'columns':f.schema_arrow.names,'start':_iso(min(lows)) if lows else None,'end':_iso(max(highs)) if highs else None,'size_bytes':p.stat().st_size}

def dataset_info(path: Path)->dict:
    raw,grid=_names(path)
    if not raw or not grid: raise ValueError('INVALID_DATASET: raw and grid artifacts required')
    r,g=_stats(path,raw),_stats(path,grid)
    tags=pd.read_csv(resolve_public_file(path,'tags.csv')).astype(object)
    tags=tags.where(pd.notna(tags),None).to_dict('records')
    events={source:name for source,name in [('journal','cycle_event_journal.parquet'),('status','cycle_events.parquet')] if (Path(path)/name).is_file()}
    result=_dataset_metadata(path,raw,grid,r,g,tags)
    result['event_files']=events
    return result


def _dataset_metadata(path,raw,grid,r,g,tags):
    return {'name':Path(path).name,'tags':tags,'start':r['start'],'end':r['end'],'raw_file':raw,'grid_file':grid,'event_file':'cycle_events.parquet' if (Path(path)/'cycle_events.parquet').exists() else None,'rows':r['rows'],'raw':r,'grid':g,'quality_codes':{'0':'GOOD','1':'UNCERTAIN','2':'BAD'},'scoring_status':'EXTERNAL_SCORING_REQUIRED' if raw=='historian.parquet' else 'GENERATED_KEY_PRIVATE','disclosure':{'raw':'Primary irregular compressed recorded samples; quality retained.','grid':'Native derived regular grid reconstructed from compressed samples; bad quality becomes null; no gap filling performed by this service.'}}

def query_samples(path: Path,tags:list[str],source='grid',start=None,end=None,max_points=2000)->dict:
    if source not in ('grid','raw'): raise ValueError('INVALID_SOURCE: use raw or grid')
    if type(max_points) is not int or not 1<=max_points<=10000: raise ValueError('QUERY_LIMIT: max_points must be 1..10000')
    if not isinstance(tags,list) or not 1<=len(tags)<=64 or len(set(tags))!=len(tags) or any(not isinstance(t,str) for t in tags): raise ValueError('INVALID_TAGS: supply 1..64 unique tag names')
    raw,grid=_names(path); name=raw if source=='raw' else grid
    if not name: raise ValueError('INVALID_DATASET: source missing')
    dictionary=pd.read_csv(resolve_public_file(path,'tags.csv'))
    known=set(dictionary['tag'])
    if set(tags)-known: raise ValueError('UNKNOWN_TAG: '+','.join(sorted(set(tags)-known)))
    start_ts=pd.Timestamp(_iso(start)) if start is not None else None
    end_ts=pd.Timestamp(_iso(end)) if end is not None else None
    if start_ts is not None and end_ts is not None and start_ts>end_ts: raise ValueError('INVALID_INTERVAL: start exceeds end')
    filt=ds.field('tag').isin(tags) if source=='raw' else None
    for op,ts in [('start',start_ts),('end',end_ts)]:
        if ts is None: continue
        boundary=pa.scalar(ts.value,type=pa.timestamp('ns',tz='UTC'))
        condition=ds.field('timestamp')>=boundary if op=='start' else ds.field('timestamp')<=boundary
        filt=condition if filt is None else filt&condition
    columns=['timestamp','tag','value','quality'] if source=='raw' else ['timestamp',*tags]
    scanner=ds.dataset(resolve_public_file(path,name),format='parquet').scanner(columns=columns,filter=filt,batch_size=min(max_points+1,10001))
    rows=[]
    for batch in scanner.to_batches():
        rows.extend(batch.slice(0,max_points+1-len(rows)).to_pylist())
        if len(rows)>max_points: break
    truncated=len(rows)>max_points; rows=rows[:max_points]
    for row in rows:
        row['timestamp']=_iso(row['timestamp'])
        for k,v in row.items():
            if isinstance(v,float) and not math.isfinite(v): row[k]=None
    return {'source':source,'rows':rows,'truncated':truncated,'max_points':max_points,'returned_points':len(rows),'aggregation':'none','order':'native timestamp order','interval':{'start':_iso(start) if start is not None else None,'end':_iso(end) if end is not None else None},'disclosure':('Primary compressed samples; raw quality codes retained, no interpolation or invented gaps.' if source=='raw' else 'Native derived grid; interpolation inherits native reconstruction, bad quality is null. No additional interpolation or gap filling.'),'capacity':{'max_points':10000,'max_tags':64,'full_download_available':True}}


def query_events(path:Path,source='journal',start=None,end=None,max_points=2000)->dict:
    if source not in ('journal','status'):raise ValueError('INVALID_EVENT_SOURCE: use journal or status')
    if type(max_points) is not int or not 1<=max_points<=10000:raise ValueError('QUERY_LIMIT: max_points must be1..10000')
    name='cycle_event_journal.parquet' if source=='journal' else 'cycle_events.parquet'
    file=resolve_public_file(Path(path),name)
    schema=pq.read_schema(file)
    if source=='journal' and set(schema.names)!={'timestamp','event_code','count','quality'}:
        raise ValueError('INVALID_EVENT_SCHEMA: measured journal requires exactly timestamp,event_code,count,quality')
    if 'timestamp' not in schema.names:raise ValueError('INVALID_EVENT_SCHEMA: timestamp required')
    lo=pd.Timestamp(_iso(start)) if start is not None else None
    hi=pd.Timestamp(_iso(end)) if end is not None else None
    if lo is not None and hi is not None and lo>hi:raise ValueError('INVALID_INTERVAL: start exceeds end')
    filt=None
    for op,value in (('start',lo),('end',hi)):
        if value is None:continue
        boundary=pa.scalar(value.value,type=pa.timestamp('ns',tz='UTC'))
        condition=ds.field('timestamp')>=boundary if op=='start' else ds.field('timestamp')<=boundary
        filt=condition if filt is None else filt&condition
    rows=[]
    scanner=ds.dataset(file,format='parquet').scanner(filter=filt,batch_size=min(max_points+1,10001))
    for batch in scanner.to_batches():
        rows.extend(batch.slice(0,max_points+1-len(rows)).to_pylist())
        if len(rows)>max_points:break
    truncated=len(rows)>max_points;rows=rows[:max_points]
    for row in rows:
        row['timestamp']=_iso(row['timestamp'])
        for key,value in row.items():
            if isinstance(value,float) and not math.isfinite(value):row[key]=None
    return {'source':source,'file':name,'rows':rows,'truncated':truncated,'max_points':max_points,'returned_points':len(rows),'aggregation':'none',
            'event_codes':{'-1':'unavailable acquisition','0':'permissive hold','1':'completed stroke','2':'completed feed','3':'inspection delivery'} if source=='journal' else None,
            'disclosure':'Measured digital edges quantized to1ms; non-GOOD acquisition masks code/count. No private pitch, rejection detail or conservation ledger.' if source=='journal' else 'Measured status/counters on the native historian scan; not a timestamp-per-stroke journal.'}
