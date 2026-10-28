"""Public-evidence campaign window detection. No simulator or truth imports."""
from statistics import mean, pstdev


def detect_windows(evidence, baseline_s=3600, bin_s=60):
    """Evidence-only detector. Thresholds are engineering limits, not event IDs.

    Acquisition quality, throughput loss, dimensions, feed motion and continuous
    load/pressure are independent detectors. Adjacent flagged bins are merged;
    a normal gap longer than two minutes separates investigations.
    """
    rows=evidence['samples']; baseline=[r for r in rows if r['t']<baseline_s]
    def vals(group,key):
        return [float(r[key]) for r in group if isinstance(r.get(key),(int,float)) and r.get('data_quality',{}).get(key,'GOOD')=='GOOD']
    def avg(group,key):
        v=vals(group,key);return mean(v) if v else None
    reference={k:avg(baseline,k) for k in ('spm','quality_measurement','tonnage','lube_pressure','motor_current','feeder_position')}
    bins={}
    for row in rows:
        if row['t']>=baseline_s: bins.setdefault((row['t']//bin_s)*bin_s,[]).append(row)
    flagged=[]
    for start, group in sorted(bins.items()):
        flag=any(q in ('MISSING','STUCK') for r in group for q in r.get('data_quality',{}).values())
        current=avg(group,'spm'); base=reference['spm']
        flag|=current is not None and base is not None and current<base*.90
        for key,threshold in (('quality_measurement',.05),('lube_pressure',.6),('feeder_position',.6),('motor_current',4),('tonnage',12)):
            current=avg(group,key);base=reference[key]
            flag|=current is not None and base is not None and abs(current-base)>threshold
        position=vals(group,'feeder_position')
        flag|=len(position)>3 and pstdev(position)>.5
        for record in evidence.get('quality',[]):
            if start<=record.get('t',-1)<start+bin_s and record.get('quality_measurement',0)>.08: flag=True
        if flag: flagged.append((start,min(start+bin_s,rows[-1]['t']+1)))
    merged=[]
    for start,end in flagged:
        if merged and start-merged[-1][1]<=120: merged[-1]=(merged[-1][0],end)
        else: merged.append((start,end))
    return merged

