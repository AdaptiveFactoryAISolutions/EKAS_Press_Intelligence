"""Public historian artifacts using preserved HistorianSim compression.

Discrete signals store changes without interpolation. Analog records use a
0.1%-span swinging-door deadband; quality transitions are always retained.
Missing values are stored empty with MISSING quality, never interpolated into
valid evidence. Regular one-second export preserves the original observations.
"""
import csv
import gzip
import hashlib
from pathlib import Path
import numpy as np
from historiansim.historian.swinging_door import compress
from ekas_press_intelligence.domain import signals


def export_historian(evidence, destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    rows=evidence['samples']; times=np.array([r['t'] for r in rows],dtype=float)
    keys=sorted(set().union(*(r.keys() for r in rows)) - {'t','data_quality'})
    meta={s['signal_id']:s for s in signals()}
    manifest={'regular_rows':len(rows),'compressed_rows':0,'compression':'HistorianSim swinging-door; analog deadband 0.001 observed span; discrete change only; quality boundaries retained','signals':{},'files':[]}
    regular=destination/'regular_1s.csv.gz'
    with gzip.open(regular,'wt',newline='') as f:
        writer=csv.writer(f);writer.writerow(['t']+keys+[k+'_quality' for k in keys])
        for row in rows:
            writer.writerow([row['t']]+[row.get(k) for k in keys]+[row.get('data_quality',{}).get(k,'GOOD') for k in keys])
    compressed=destination/'historian_compressed.csv.gz'
    with gzip.open(compressed,'wt',newline='') as f:
        writer=csv.writer(f);writer.writerow(['signal','t','value','quality'])
        for key in keys:
            values=[r.get(key) for r in rows]
            quality=[r.get('data_quality',{}).get(key,'GOOD') for r in rows]
            flags=np.array([0 if q=='GOOD' else 1 if q=='MISSING' else 2 for q in quality],dtype=np.int8)
            discrete=meta.get(key,{}).get('kind')=='discrete' or any(isinstance(v,str) for v in values if v is not None)
            if discrete:
                keep={0,len(rows)-1}
                for i in range(1,len(rows)):
                    if values[i]!=values[i-1] or flags[i]!=flags[i-1]: keep.update((i-1,i))
                keep=sorted(keep)
            else:
                numeric=np.array([0. if v is None else float(v) for v in values])
                valid=[float(v) for v,q in zip(values,flags) if v is not None and q==0]
                span=(min(valid),max(valid)) if valid else (0.,1.)
                keep=compress(times,numeric,flags,.001,span).tolist()
            for i in keep: writer.writerow([key,rows[i]['t'],values[i],quality[i]])
            manifest['signals'][key]={'compressed_samples':len(keep),'missing_samples':sum(v is None for v in values),'kind':'discrete' if discrete else 'analog','quality_transition_policy':'retain both sides'}
            manifest['compressed_rows']+=len(keep)
    for path in (regular,compressed):
        manifest['files'].append({'path':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return manifest
