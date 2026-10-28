"""Controlled before/after verification from observed samples or measured KPIs."""
from statistics import mean, stdev
from math import isfinite, sqrt


COMPARISON_POLICY = {
    'version':'controlled-press-comparison-1.0',
    'performance_relative_change':.05,
    'count_rate_relative_change':.20,
    'downtime_exposure_fraction':.005,
    'quality_deviation_absolute_change':.01,
    'quality_deviation_relative_change':.10,
    'scrap_rate_absolute_change':.005,
    'scrap_minimum_observed_units':100,
    'confidence_level':.95,
    'sample_mean_block_s':60,
    'uncertainty_model':'95% Wilson binomial intervals for scrap; Poisson count-rate margin; 60-second block-mean margin where observed. Overlap means compatible uncertainty, not equivalence.',
}


def _mean_uncertainty(samples,signal,running_only=False):
    blocks={}
    for row in samples:
        value=row.get(signal)
        if isinstance(value,(int,float)) and isfinite(value) and (not running_only or row.get('press_run')):
            blocks.setdefault(int(row['t']//60),[]).append(value)
    means=[mean(values) for values in blocks.values()]
    return 1.96*stdev(means)/sqrt(len(means)) if len(means)>1 else None


def _wilson(rate,n):
    z=1.96;center=(rate+z*z/(2*n))/(1+z*z/n)
    half=z*sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
    return [max(0,center-half),min(1,center+half)]


def _metrics(payload):
    if payload.get('metrics') and not payload.get('samples'): return dict(payload['metrics'])
    samples=sorted(payload.get('samples',[]),key=lambda s:s['t'])
    if len(samples)<2: return {}
    exposure=samples[-1]['t']-samples[0]['t']
    if exposure<=0:return {}
    inspection=sorted([r for r in payload.get('quality',[]) if isinstance(r.get('t'),(int,float)) and samples[0]['t']<=r['t']<=samples[-1]['t']],key=lambda r:r['t'])
    pairs=list(zip(samples,samples[1:]))
    downtime=sum(b['t']-a['t'] for a,b in pairs if not a.get('press_run',False))
    stops=[]; stop_start=None
    for s in samples:
        if not s.get('press_run',False) and stop_start is None: stop_start=s['t']
        if s.get('press_run',False) and stop_start is not None: stops.append(s['t']-stop_start);stop_start=None
    if stop_start is not None:stops.append(samples[-1]['t']-stop_start)
    def delta(k):
        records=samples if all(isinstance(r.get(k),(int,float)) for r in (samples[0],samples[-1])) else inspection
        if len(records)<2 or not all(isinstance(r.get(k),(int,float)) for r in (records[0],records[-1])):return None
        change=records[-1][k]-records[0][k]
        return change if change>=0 else None
    parts,scrap=delta('part_count'),delta('scrap_count')
    spms=[s['spm'] for s in samples if s.get('press_run') and s.get('spm') is not None]
    quality=[s['quality_measurement'] for s in samples if isinstance(s.get('quality_measurement'),(float,int))]
    if not quality: quality=[s['quality_measurement'] for s in inspection if isinstance(s.get('quality_measurement'),(int,float))]
    faults=sum(bool(b.get('press_fault')) and not bool(a.get('press_fault')) for a,b in pairs)+bool(samples[0].get('press_fault'))
    good=sum(s.get('quality','good') in ('good','GOOD','valid') and all(v in ('good','GOOD','valid') for v in s.get('data_quality',{}).values()) for s in samples)/len(samples)
    rate=payload.get('context',{}).get('rate',max(spms,default=0))
    return dict(inspected_count=parts+scrap if parts is not None and scrap is not None else None,scrap_count=scrap,spm_uncertainty_95=_mean_uncertainty(samples,'spm',running_only=True),quality_uncertainty_95=_mean_uncertainty(samples,'quality_measurement'),exposure_s=exposure,data_quality=good,microstops=sum(0<d<=60 for d in stops),downtime_s=downtime,spm=mean(spms) if spms else 0,throughput=parts*3600/exposure if parts is not None else None,oee=parts/(rate*exposure/60) if rate and parts is not None else None,scrap_rate=scrap/(parts+scrap) if parts is not None and scrap is not None and parts+scrap else None,quality=mean(quality) if quality else None,repeat_faults=faults)


def verify(before: dict, after: dict, action: dict) -> dict:
    b,a=_metrics(before),_metrics(after)
    reasons=[]; bc,ac=before.get('context',{}),after.get('context',{})
    controls={}
    for field in ('job','die_id','material','rate'):
        left,right=bc.get(field),ac.get(field)
        controls[field]=left is not None and right is not None and left==right
        if not controls[field]:reasons.append('Uncontrolled or missing '+field)
    for label,payload in [('before',before),('after',after)]:
        if payload.get('metrics') and not payload.get('samples'):
            provenance=payload.get('control_provenance',{})
            if not provenance.get('source') or provenance.get('controls')!=payload.get('context'):reasons.append(label+' offline control provenance missing')
        for field in ('job','die_id','material','rate'):
            expected=payload.get('context',{}).get(field)
            if any(s.get(field,expected)!=expected for s in payload.get('samples',[])):reasons.append(label+' varying '+field)
        rates=[s.get('spm') for s in payload.get('samples',[]) if s.get('press_run') and isinstance(s.get('spm'),(int,float))]
        if rates and max(rates)-min(rates)>max(1,mean(rates)*.1):reasons.append(label+' varying running rate')
    if before.get('samples') or after.get('samples'):
        commanded=[]
        for payload in (before,after):
            rows=payload.get('samples',[])
            values=[r.get('rate_setpoint') for r in rows]
            complete=bool(values) and all(isinstance(v,(int,float)) and isfinite(v) for v in values)
            commanded.append(set(values) if complete else set())
        observed_equal=all(len(v)==1 for v in commanded) and commanded[0]==commanded[1]
        controls['observed_rate_setpoint']=observed_equal
        achieved_changed=isinstance(b.get('spm'),(int,float)) and isinstance(a.get('spm'),(int,float)) and abs(b['spm']-a['spm'])>1e-6
        if any(commanded) and not observed_equal:reasons.append('Observed commanded rate differs or is incomplete')
        if achieved_changed and not observed_equal:reasons.append('Achieved rate changed without observed equal commanded rate')
    for label,m in [('before',b),('after',a)]:
        if not isinstance(m.get('exposure_s'),(int,float)) or not isfinite(m['exposure_s']) or m['exposure_s']<300:reasons.append(label+' exposure below 300 seconds')
        if not isinstance(m.get('data_quality'),(int,float)) or not isfinite(m['data_quality']) or not .95<=m['data_quality']<=1:reasons.append(label+' data quality below 95 percent')
    if b.get('exposure_s',0) and a.get('exposure_s',0) and min(b['exposure_s'],a['exposure_s'])/max(b['exposure_s'],a['exposure_s'])<.8:reasons.append('Exposure differs by more than 20 percent')
    required=('microstops','downtime_s','spm','throughput','oee','scrap_rate','quality','repeat_faults')
    if any(not isinstance(m.get(k),(int,float)) or not isfinite(m[k]) or m[k]<0 for m in (b,a) for k in required):reasons.append('Required outcome metrics missing')
    comparisons={}
    for k in required:
        bv,av=b.get(k),a.get(k)
        if bv is None or av is None:continue
        if k in ('microstops','repeat_faults','downtime_s'):
            bv=bv/max(b.get('exposure_s',1),1);av=av/max(a.get('exposure_s',1),1)
        comparisons[k]=dict(before=bv,after=av,delta=av-bv,provenance={label:payload.get('context',{}).get('source') or payload.get('control_provenance',{}).get('source') or 'provided observed samples' for label,payload in (('before',before),('after',after))})
    improved=[];regressions=[];qualifications=[]
    for key,comparison in comparisons.items():
        bv,av,delta=(comparison[k] for k in ('before','after','delta'))
        threshold=0;assessment='WITHIN_ENGINEERING_TOLERANCE'
        if not all(isinstance(v,(int,float)) and isfinite(v) for v in (bv,av,delta)):continue
        if key=='scrap_rate':
            bn,an=b.get('inspected_count'),a.get('inspected_count')
            if not all(isinstance(n,(int,float)) and isfinite(n) and n>=100 for n in (bn,an)) or not 0<=bv<=1 or not 0<=av<=1:
                reasons.append('Insufficient observed inspected counts for scrap uncertainty')
                comparison['assessment']='INSUFFICIENT_EXPOSURE';continue
            before_ci,after_ci=_wilson(bv,bn),_wilson(av,an)
            comparison['before_interval_95']=before_ci;comparison['after_interval_95']=after_ci
            threshold=.005
            disjoint=after_ci[0]>before_ci[1] or before_ci[0]>after_ci[1]
            significant=abs(delta)>=threshold and disjoint
            if not disjoint:assessment='COMPATIBLE_WITH_SAMPLING_NOISE'
        else:
            if key in ('spm','throughput','oee'):
                threshold=max(abs(bv)*.05, .5 if key=='spm' else 1 if key=='throughput' else .03)
                if key=='spm':
                    margins=[m.get('spm_uncertainty_95',0) for m in (b,a)]
                    if all(isinstance(v,(int,float)) and isfinite(v) for v in margins):threshold=max(threshold,sqrt(sum(v*v for v in margins)))
                elif key=='throughput' and all(isinstance(m.get('inspected_count'),(int,float)) for m in (b,a)):
                    threshold=max(threshold,1.96*sqrt(sum(m['inspected_count']/(m['exposure_s']/3600)**2 for m in (b,a))))
            elif key in ('microstops','repeat_faults'):
                threshold=max(abs(bv)*.2,1.96*sqrt(sum(m[key]/m['exposure_s']**2 for m in (b,a))))
            elif key=='downtime_s':threshold=max(abs(bv)*.2,.005)
            elif key=='quality':
                threshold=max(abs(bv)*.1,.01)
                margins=[m.get('quality_uncertainty_95',0) for m in (b,a)]
                if all(isinstance(v,(int,float)) and isfinite(v) for v in margins):threshold=max(threshold,sqrt(sum(v*v for v in margins)))
            significant=abs(delta)>max(threshold,1e-12)
        if significant:
            lower_better=key in ('microstops','downtime_s','scrap_rate','repeat_faults','quality')
            improvement=delta<0 if lower_better else delta>0
            (improved if improvement else regressions).append(key)
            assessment='MEANINGFUL_IMPROVEMENT' if improvement else 'MEANINGFUL_REGRESSION'
        comparison.update(meaningful_change_threshold=threshold,assessment=assessment)
        if assessment=='COMPATIBLE_WITH_SAMPLING_NOISE':qualifications.append('Scrap intervals overlap; no meaningful change established, not proof of identical reject risk.')
    status='INCONCLUSIVE' if reasons else ('VERIFIED' if improved and not regressions else 'NOT_VERIFIED')
    if status=='NOT_VERIFIED':reasons.append('Meaningful regression observed' if regressions else 'No meaningful improvement exceeds comparison policy thresholds')
    sustained_requirement=max(300,action.get('sustained_duration_s',86400))
    return dict(comparison_policy=dict(COMPARISON_POLICY),qualifications=qualifications,status=status,sustained=status=='VERIFIED' and a.get('exposure_s',0)>=sustained_requirement,sustained_duration_required_s=sustained_requirement,controls=controls,reasons=reasons,regressions=regressions,improvements=improved,metrics={'before':b,'after':a},comparisons=comparisons,qualification='Observed controlled comparison; work-order completion alone is not evidence of success.')
