"""Read-only beginner summaries of complete primary observations; no private truth."""
from __future__ import annotations
import hashlib
import math
from pathlib import Path
import pyarrow.compute as pc
import pyarrow as pa
import pyarrow.parquet as pq
from .data import resolve_public_file, _iso

VERSION='1.0'
CASE_LABELS={'LINE-FEED-SLIP':'Feeder slipping','LINE-SUPPLY-STARVATION':'Material supply starvation',
             'LINE-LUBE-RESTRICTION':'Lubrication restriction','LINE-STATION-SENSOR':'Station sensor failure',
             'LINE-SCRAP-BLOCKAGE':'Scrap removal blocked','LINE-WASHER-COLD':'Washer heating lost',
             'LINE-WASHER-LOW-FLOW':'Washer spray flow low','LINE-PACKING-SLOW':'Manual packing slowed'}
SIGNALS={
    'SIC-1500.PV':('Press speed','strokes per minute'),
    'TI-WASH':('Washer temperature','degrees Celsius'),
    'COUNT-STROKES':('Press strokes','strokes'),
    'COUNT-PRODUCED':('Parts produced','parts'),
    'COUNT-PACKED':('Parts packed','parts'),
    'COUNT-REJECTED':('Parts rejected','parts'),
    'COUNT-WASHER':('Parts in the washer','parts'),
    'COUNT-DISCHARGE':('Parts on the discharge conveyor','parts'),
    'COUNT-PACK-QUEUE':('Parts that wait for packing','parts'),
    'II-DRIVE':('Press motor current','amperes'),
    'WI-TOTAL':('Total forming force','kilonewtons'),
}
FINDINGS={
    'noise_is_colored':('Sensor-noise pattern','Some simulated sensor changes did not pass the expected noise-pattern check.'),
    'pca_dimensionality':('Signal relationship','The statistical check found a problem with the relationships between signals.'),
    'no_fault_twin':('Comparison run without faults','The comparison-run check did not pass. Do not use it as a validated fault comparison.'),
}


def _digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def _scan(path):
    """All-record statistics; fixed 240 time buckets retain extrema and endpoints."""
    source=pq.ParquetFile(path)
    required={'tag','timestamp','value','quality'}
    if not required.issubset(source.schema_arrow.names):
        raise ValueError('REPORT_SOURCE_SCHEMA: Primary readings need tag, timestamp, value and quality columns')
    stats={name:dict(label=label,unit=unit,stored_count=0,good_count=0,unusable_count=0,
                    first=None,last=None,minimum=None,maximum=None,points=[],plot_reduced=False)
           for name,(label,unit) in SIGNALS.items()}
    # First pass derives the entire primary observation interval, not a UI query window.
    low=high=None
    for batch in source.iter_batches(batch_size=65536,columns=['timestamp']):
        bounds=pc.min_max(batch.column(0)).as_py()
        if bounds['min'] is not None:
            low=min(low,bounds['min']) if low else bounds['min']
            high=max(high,bounds['max']) if high else bounds['max']
    if low is None:raise ValueError('REPORT_SOURCE_EMPTY: No primary observation times are available')
    span=max((high-low).total_seconds(),1)
    buckets={name:{} for name in SIGNALS}
    latest={name:None for name in SIGNALS}
    for batch in source.iter_batches(batch_size=65536,columns=['tag','timestamp','value','quality']):
        selected=batch.filter(pc.is_in(batch.column(0),value_set=pa.array(list(SIGNALS))))
        for row in selected.to_pylist():
            name=row['tag'];s=stats[name];s['stored_count']+=1
            timestamp=row['timestamp'];value=row['value']
            valid=(timestamp is not None and row['quality']==0 and isinstance(value,(int,float))
                   and math.isfinite(value) and (not name.startswith('COUNT-') or value>=0 and float(value).is_integer()))
            if timestamp is not None and (latest[name] is None or timestamp>=latest[name][0]):
                latest[name]=(timestamp,float(value) if valid else None)
            if not valid:s['unusable_count']+=1;continue
            value=float(value);point={'time':_iso(timestamp),'value':value,'_at':timestamp}
            s['good_count']+=1
            if s['first'] is None or timestamp<s['first']['_at']:s['first']=point
            s['minimum']=value if s['minimum'] is None else min(s['minimum'],value)
            s['maximum']=value if s['maximum'] is None else max(s['maximum'],value)
            bucket=min(239,max(0,int((timestamp-low).total_seconds()/span*240)))
            points=buckets[name].setdefault(bucket,[])
            # Four representatives per bucket: earliest, latest, low and high.
            candidates=points+[point]
            buckets[name][bucket]=[min(candidates,key=lambda p:p['_at']),max(candidates,key=lambda p:p['_at']),
                                   min(candidates,key=lambda p:p['value']),max(candidates,key=lambda p:p['value'])]
    for name,s in stats.items():
        last=latest[name]
        s['last']=({'time':_iso(last[0]),'value':last[1]} if last and last[1] is not None else None)
        s['latest_observation_time']=_iso(last[0]) if last else None
        unique={(p['_at'],p['value']):p for group in buckets[name].values() for p in group}
        s['points']=[{k:p[k] for k in ('time','value')} for p in sorted(unique.values(),key=lambda p:p['_at'])]
        if s['first'] is not None:s['first']={k:s['first'][k] for k in ('time','value')}
        s['plot_reduced']=s['good_count']>len(s['points'])
    return stats,_iso(low),_iso(high)


def _validation(result):
    entries=result.get('validation')
    valid=isinstance(entries,list) and bool(entries) and all(isinstance(x,dict) and type(x.get('passed')) is bool for x in entries)
    findings=[]
    for item in entries if isinstance(entries,list) else []:
        if not isinstance(item,dict) or item.get('passed') is not False:continue
        name=str(item.get('name','unknown'))
        title,explanation=FINDINGS.get(name,('Recorded check needs attention','This check did not pass. The recorded name is in the evidence details.'))
        findings.append(dict(name=name,title=title,explanation=explanation,severity=item.get('severity','not recorded')))
    status='findings' if findings or result.get('native_validation_passed') is False else 'passed' if valid and result.get('native_validation_passed') is True else 'unavailable'
    engineering=result.get('engineering_acceptance')
    passed=engineering.get('passed') if isinstance(engineering,dict) else None
    return dict(native_status=status,engineering_status='passed' if passed is True else 'failed' if passed is False else 'unavailable',findings=findings)


def build_report(job:dict,binding:dict,public_path:Path)->dict:
    config=job['parameters'].get('config') or {};params=config.get('params') or {}
    primary=resolve_public_file(public_path,'historian_10s.parquet')
    before=_digest(primary);stats,start,end=_scan(primary)
    if _digest(primary)!=before:raise ValueError('REPORT_SOURCE_CHANGED: The source changed during the report request. Try again')
    counter_names=['COUNT-PRODUCED','COUNT-PACKED','COUNT-WASHER','COUNT-DISCHARGE','COUNT-PACK-QUEUE','COUNT-REJECTED']
    counters=[stats[n]['last'] for n in counter_names]
    ready=all(counters) and len({p['time'] for p in counters if p})==1 and all(p['time']==end for p in counters if p)
    balance=dict(status='unavailable',produced_minus_packed=None,in_line=None,rejected=None,time=None)
    if ready:
        values=[int(p['value']) for p in counters];difference=values[0]-values[1];remaining=sum(values[2:5]);rejected=values[5]
        balance=dict(status='agrees' if difference==remaining+rejected and difference>=0 else 'differs',
                     produced_minus_packed=difference,in_line=remaining,rejected=rejected,time=counters[0]['time'])
    episodes=config.get('episodes') or {};faults=episodes.get('n_faults')
    # Admin sees the requested case, never a claimed diagnosis or private physical cause.
    case='No injected fault' if faults==0 else 'Fault practice' if isinstance(faults,int) and faults>0 else 'Case not recorded'
    return dict(schema_version=1,report_version=VERSION,job_id=job['id'],dataset_id=job['result']['dataset_id'],
                title='Your press simulation: results and next steps',scope='Simulation practice only',
                qualification_status='UNQUALIFIED_PRACTICE',start=start,end=end,created_at=job.get('created_at'),completed_at=job.get('updated_at'),
                setup=dict(speed_spm=params.get('speed_spm'),washer_temperature_c=params.get('washer_temperature_c'),
                           stations=params.get('stations'),packers=params.get('packers'),packing_rate_per_min=params.get('packing_rate_per_min'),
                           seed=config.get('seed'),fault_count=faults,case=case,
                           requested_cases=[CASE_LABELS.get(name,'Selection not in the report term list') for name in episodes.get('cause_ids') or []],
                           requested_faults=episodes.get('cause_ids') or [],duration_days=(config.get('time') or {}).get('days')),
                signals=stats,balance=balance,validation=_validation(job['result']),
                provenance=dict(primary_file=primary.name,primary_sha256=before,**binding,
                                summaries='All stored primary readings; no reconstructed grid, resimulation or added readings.',
                                plot='Up to 960 stored points per signal. Each time bucket keeps its first, last, lowest and highest good reading.'),
                language=dict(reference='ASD-STE100 Issue 9, 2025-01-15',conformance='NOT_FULLY_REVIEWED',
                              note='The wording uses the standard as a reference. Full vocabulary and terminology review remains open.'))
