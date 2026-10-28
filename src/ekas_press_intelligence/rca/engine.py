"""Evidence-only, conservative hypothesis evaluation. No simulator dependency."""
from statistics import mean, pstdev
from ..domain import catalog


def _robust(values):
    ordered=sorted(values)
    cut=max(1,int(len(ordered)*.04)) if len(ordered)>=20 else 0
    return ordered[cut:-cut] if cut else ordered


def investigate(evidence, question=''):
    context=evidence.get('context',{}); rows=evidence.get('samples',[])
    start=context.get('analysis_start_s',rows[0]['t'] if rows else 0); end=context.get('analysis_end_s',rows[-1]['t'] if rows else 0)
    rows=[r for r in rows if start<=r['t']<=end]
    if len(rows)<4: return {'error':'INSUFFICIENT_EVIDENCE','qualification':'At least four measured samples are required.','period':{'start_s':start,'end_s':end}}
    keys=sorted({k for r in rows for k,v in r.items() if k not in ('t','data_quality') and isinstance(v,(int,float))})
    facts=[]; features={}; quality_flags=set()
    for r in rows:
        quality_flags.update(str(v).upper() for v in r.get('data_quality',{}).values())
    for flag in sorted(quality_flags - {'GOOD'}):
        facts.append({'id':'quality-'+flag.lower(),'t':end,'quality':'GOOD','observed_quality':flag,'source':'historian_quality','signal':'data_quality','asset':'Historian','timestamp':{'start_s':start,'end_s':end},'calculation':{'flag':flag,'affected_samples':sum(flag in r.get('data_quality',{}).values() for r in rows)},'rule':'Non-GOOD acquisition quality invalidates affected measurements','confidence':'RECORDED','qualification':'Acquisition artifact, not proof of equipment failure.'})
    for index,event in enumerate(evidence.get('events',[])):
        if start<=event.get('t',-1)<=end:
            facts.append({'id':f'event-{index}','t':event['t'],'quality':'GOOD','source':'operator_plc_record','signal':event.get('type','event'),'asset':event.get('asset','Line 03'),'timestamp':event['t'],'calculation':None,'rule':'Recorded operating context','confidence':'RECORDED','qualification':'Operating record supports chronology; does not prove a physical cause.'})
    for index,record in enumerate(evidence.get('maintenance',[])):
        facts.append({'id':f'maintenance-{index}','t':None,'quality':'CONTEXTUAL','source':'maintenance_record','signal':None,'asset':record.get('asset','unavailable'),'timestamp':record.get('date'),'calculation':{'record':record,'repeat_failure':record.get('repeat_failure',False)},'rule':'Maintenance history is contextual prior evidence only','confidence':'CONTEXTUAL','qualification':'A repeat failure or completed work order does not establish the present cause.'})
    for collection,source,prefix in (('pfmea','pfmea_prior','pfmea'),('control_plan','control_plan_prior','control-plan')):
        for index,record in enumerate(evidence.get(collection,[])):
            facts.append({'id':f'{prefix}-{index}','t':record.get('t'),'quality':'CONTEXTUAL','source':source,'signal':None,'signal_ids':record.get('signal_ids',[]),'asset':record.get('asset') or 'Unscoped prior','timestamp':record.get('date'),'calculation':{'record':record,'scope':'asset' if record.get('asset') else 'unscoped'},'rule':'Public process prior; cannot establish a measured failure','confidence':'PRIOR','qualification':'Requires matching measured observations and alternative elimination. Unscoped records do not establish an asset association.'})
    baseline_rows=evidence.get('baseline_samples',[])
    quality_rows=[r for r in evidence.get('quality',[]) if isinstance(r.get('t'),(int,float)) and start<=r['t']<=end]
    quality_keys=[key for key in ('quality_measurement','scrap_count','fpy','quality_drift') if key not in keys and any(isinstance(r.get(key),(int,float)) for r in quality_rows)]
    sources={key:rows for key in keys}
    sources.update({key:quality_rows for key in quality_keys})
    for key,source_rows in sources.items():
        inspection=key in quality_keys
        valid=[r for r in source_rows if isinstance(r.get(key),(int,float)) and r.get('data_quality',{}).get(key,'GOOD')=='GOOD']
        if len(valid)<4: continue
        reference_rows=baseline_rows
        if inspection and baseline_rows:
            base_start=min(r['t'] for r in baseline_rows);base_end=max(r['t'] for r in baseline_rows)
            reference_rows=[r for r in evidence.get('baseline_quality',evidence.get('quality',[])) if base_start<=r.get('t',-1)<=base_end]
        n=max(2,len(valid)//4)
        reference=[r for r in reference_rows if isinstance(r.get(key),(int,float)) and r.get('data_quality',{}).get(key,'GOOD')=='GOOD']
        before=[float(r[key]) for r in reference] if len(reference)>=2 else [float(r[key]) for r in valid[:n]]
        after=[float(r[key]) for r in valid[-n:]]
        if key in ('stroke_count','part_count','scrap_count','strip_progression'):
            source_before=reference if len(reference)>=2 else valid[:n]
            source_after=valid[-n:]
            before=[(b[key]-a[key])/max(b['t']-a['t'],1) for a,b in zip(source_before,source_before[1:])]
            after=[(b[key]-a[key])/max(b['t']-a['t'],1) for a,b in zip(source_after,source_after[1:])]
        before=_robust(before); after=_robust(after)
        baseline=mean(before); change=mean(after)-baseline; scale=max(abs(baseline),1.)
        features[key]={'change':change,'relative':change/scale,'baseline':baseline,'current':mean(after),'absolute_change':abs(change),'peak':max(_robust([float(r[key]) for r in valid])),'window_mean':mean(float(r[key]) for r in valid),'window_trend':mean(_robust([float(r[key]) for r in valid[-n:]]))-mean(_robust([float(r[key]) for r in valid[:n]])),'variance_ratio':pstdev(after)/max(pstdev(before),.01)}
        facts.append({'id':f'inspection-{key}' if inspection else f'measurement-{key}','t':valid[-1]['t'],'quality':'GOOD','source':'quality_inspection' if inspection else 'historian','signal':key,'asset':'Quality inspection' if inspection else 'Line 03','timestamp':{'start_s':valid[0]['t'],'end_s':valid[-1]['t']},'calculation':{'baseline_mean':baseline,'current_mean':mean(after),'difference':change,'variance_ratio':features[key]['variance_ratio'],'robust_window_peak':features[key]['peak'],'within_window_trend':features[key]['window_trend'],'tail_trim_fraction':.04,'baseline_samples':len(before),'current_samples':len(after)},'rule':'Baseline/current quartile mean, window peak and variance comparison','confidence':'MEASURED','qualification':'Association and trend; does not prove physical causation.'})
    def relative(key): return features.get(key,{}).get('relative',0.)
    def low(key): return relative(key)<-.12
    def high(key): return relative(key)>.12
    def peak_high(key): return features.get(key,{}).get('peak',0)>1.12*max(features.get(key,{}).get('baseline',0),1)
    def moved_position(): return features.get('feeder_position',{}).get('absolute_change',0)>.5
    def variable(key): return features.get(key,{}).get('variance_ratio',0)>3
    operator=any(e.get('type') in ('operator_speed_change','speed_change','operator_rate_change','operator_speed_setpoint') and start<=e.get('t',0)<=end for e in evidence.get('events',[]))
    planned=any(e.get('type') in ('planned_stop','changeover','planned_changeover') and start<=e.get('t',0)<=end for e in evidence.get('events',[]))
    rules={
        'feeder_sensor_drift': [('feeder_position',moved_position()),('feeder_position',not variable('feeder_position') and moved_position() and abs(features.get('feeder_position',{}).get('window_trend',0))>.15)],
        'feeder_mechanical_instability':[('feeder_position',variable('feeder_position')),('motor_current',variable('motor_current')),('material_present',not low('material_present'))],
        'misfeed':[('strip_progression',low('strip_progression')),('feed_complete',low('feed_complete')),('die_protection',high('die_protection')),('feeder_position',not moved_position() and not variable('feeder_position')),('material_present',not low('material_present'))],
        'material_starvation':[('material_present',low('material_present')),('loop_height',low('loop_height')),('decoiler_ready',not low('decoiler_ready'))],
        'decoiler_interruption':[('decoiler_ready',low('decoiler_ready')),('loop_height',low('loop_height'))],
        'lubrication_pressure_loss':[('lube_pressure',low('lube_pressure')),('spm',low('spm'))],
        'die_protection_trip':[('die_protection',high('die_protection')),('feeder_ready',not low('feeder_ready') and high('die_protection'))],
        'progressive_die_wear':[('quality_measurement',high('quality_measurement')),('tonnage',high('tonnage'))],
        'abnormal_tonnage':[('tonnage',peak_high('tonnage') and not high('quality_measurement')),('press_fault',high('press_fault') and peak_high('tonnage'))],
        'press_speed_degradation':[('spm',low('spm')),('motor_current',high('motor_current'))],
        'repeated_microstops':[('feed_complete',variable('feed_complete')),('feeder_position',not moved_position() and not variable('feeder_position') and variable('feed_complete')),('die_protection',not high('die_protection') and variable('feed_complete')),('material_present',not low('material_present')),('lube_pressure',not low('lube_pressure'))],
        'quality_deterioration':[('quality_measurement',high('quality_measurement')),('scrap_count',high('scrap_count')),('tonnage',not high('tonnage'))],
        'operator_speed_change':[('operator_event',operator)],'planned_stop':[('operator_event',planned)],
        'historian_dropout':[('data_quality','MISSING' in quality_flags)],'stuck_sensor':[('data_quality','STUCK' in quality_flags)]}
    hypotheses=[]
    for item in catalog():
        name=item['event_class']; checks=rules.get(name,[]); supports=[]; contradicts=[]; missing=[]
        for signal,match in checks:
            present=signal in features or signal in ('operator_event','data_quality')
            if not present: missing.append(signal)
            elif match: supports.append(signal)
            else: contradicts.append(signal)
        score=len(supports)/max(len(checks),1)+.1*len(supports)
        if name in ('historian_dropout','stuck_sensor') and supports: score=2.
        if name in ('operator_speed_change','planned_stop') and supports: score=1.8
        disposition='NOT_OBSERVABLE' if missing else ('CONTRADICTED' if contradicts else ('SUPPORTED' if supports else 'UNRESOLVED'))
        if disposition!='SUPPORTED': score=0.
        hypotheses.append({'event_class':name,'event_kind':item['event_kind'],'asset':item['asset'],'item':item['failed_item'],'failed_item':item['failed_item'],'mechanism':item['failure_mechanism'],'failure_mechanism':item['failure_mechanism'],'score':round(score,3),'disposition':disposition,'supporting_evidence':[('quality-'+ ('missing' if name=='historian_dropout' else 'stuck')) if x=='data_quality' else next((f['id'] for f in facts if f['source']=='operator_plc_record'), 'operator_event') if x=='operator_event' else ('inspection-' if x in quality_keys else 'measurement-')+x for x in supports],'contradicting_evidence':contradicts,'missing_evidence':missing,'contextual_evidence':[f['id'] for f in facts if f['quality']=='CONTEXTUAL' and (not f.get('asset') or f.get('asset')==item['asset'])],'reason':('Complete measured mechanism signature: '+', '.join(dict.fromkeys(supports))+'.' if disposition=='SUPPORTED' else 'Missing essential observations: '+', '.join(dict.fromkeys(missing))+'.' if disposition=='NOT_OBSERVABLE' else 'Measured mechanism tests contradicted by: '+', '.join(dict.fromkeys(contradicts))+'.' if contradicts else 'No mechanism evidence establishes or eliminates this candidate.'),'verification_requirement':item['verification_method']})
    hypotheses.sort(key=lambda h:(-h['score'],h['event_class']))
    supported=[h for h in hypotheses if h['disposition']=='SUPPORTED']; primary=supported[0] if supported else None
    artifact=primary and primary['event_class'] in ('historian_dropout','stuck_sensor')
    benign=primary and primary['event_class'] in ('operator_speed_change','planned_stop')
    # Evidence-supported physical cause requires multiple independent mechanism
    # observations and elimination of positively supported alternatives.
    state='OBSERVED_ANOMALY'
    if primary and not artifact and not benign:
        state='SUSPECTED_CAUSE'
        prior=next(item for item in catalog() if item['event_class']==primary['event_class'])
        unresolved_competitors=[h for h in hypotheses if h['event_class'] in prior['competing_causes'] and h['disposition'] in ('NOT_OBSERVABLE','UNRESOLVED')]
        if len(supported)==1 and not unresolved_competitors and not primary['missing_evidence'] and (len(set(primary['supporting_evidence']))>=2 or primary['event_class']=='feeder_sensor_drift'): state='EVIDENCE_SUPPORTED_CAUSE'
    qualification='Synthetic evidence. Correlation is not physical verification; unresolved alternatives require investigation. Missing instrumentation cannot establish a root cause.'
    if artifact: answer='Historian data quality is impaired. Equipment failure cannot be concluded from the affected measurements.'
    elif benign: answer='A recorded operator action or planned stop explains the observed operating change; no equipment failure is established.'
    elif primary: answer=f"The measured evidence supports investigating {primary['item']}: {primary['mechanism']}. Competing explanations remain subject to verification."
    else: answer='The available evidence does not distinguish a physical cause. Inspect the missing observations and alternative hypotheses.'
    kpis={'spm':features.get('spm',{}).get('current'),'baseline_spm':features.get('spm',{}).get('baseline'),'samples':len(rows),'data_quality_flags':sorted(quality_flags)}
    return {'observed_problem':'Acquisition data quality impaired' if quality_flags-{'GOOD'} else 'Measured process change' if any(abs(f['relative'])>.08 or f['variance_ratio']>3 for k,f in features.items() if k not in ('ambient_temperature','material_thickness')) else 'No measured process change established','direct_answer':answer,'kpis':kpis,'evidence':facts,'hypotheses':hypotheses,'alternatives':hypotheses[1:] if primary else hypotheses,'diagnosis_state':state,'cause_claim_eligible':state=='EVIDENCE_SUPPORTED_CAUSE','qualification':qualification,'recommended_action':'Restore and validate historian measurements before equipment diagnosis.' if artifact else 'Inspect the leading hypothesis and obtain missing discriminating observations before corrective action.','verification_requirement':primary['verification_requirement'] if primary else 'Obtain independent measurements and controlled before/after evidence.','period':{'start_s':start,'end_s':end}}
