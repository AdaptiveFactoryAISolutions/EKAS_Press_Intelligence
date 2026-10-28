"""Evaluator-only temporal scoring. This module is never imported by diagnosis."""
import math
from ..domain import catalog as mechanism_catalog

STANDARD_VERSION = 'press-temporal-1.2'
TOLERANCE_S = 1.0  # one discrete sampling interval; not upstream continuous six hours


def _interval(record):
    start, end = float(record['start_s']), float(record['end_s'])
    if not math.isfinite(start + end) or end < start:
        raise ValueError('Invalid event interval')
    return start, end


def _kind(record):
    return record.get('event_kind', record.get('kind', 'fault'))


def _evidence(claim, catalog):
    refs = claim.get('evidence', [])
    valid = []
    a, b = _interval(claim)
    for ref in refs:
        key = ref if isinstance(ref, str) else ref.get('id', ref.get('evidence_id'))
        item = catalog.get(key) if key else None
        if not isinstance(item, dict) or item.get('quality', 'good') not in ('good', 'GOOD', 'valid'):
            continue
        t = item.get('t', item.get('start_s'))
        if t is not None and a - TOLERANCE_S <= float(t) <= b + TOLERANCE_S and item.get('signal'):
            valid.append(key)
    return list(dict.fromkeys(valid))


def _support(claim, records, event=None):
    """Public governed mechanism rules, never a claim-supplied signal allowlist."""
    definitions=mechanism_catalog()
    definition=next((d for d in definitions if (event and d['event_class']==event.get('event_class')) or (not event and d['failed_item']==claim.get('failed_item') and d['failure_mechanism']==claim.get('failure_mechanism'))),None)
    if not definition:return [],False
    valid=_evidence(claim,records)
    primary=set(definition['observable_signals'])
    supporting=[]
    def changed(record,direction):
        calc=record.get('calculation') or {}
        diff=calc.get('difference')
        if not isinstance(diff,(int,float)) or not math.isfinite(diff):return False
        base,cur=calc.get('baseline_mean'),calc.get('current_mean')
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (base,cur)):return False
        if not math.isclose(cur-base,diff,rel_tol=1e-6,abs_tol=1e-8):return False
        if direction=='variance':
            ratio=calc.get('variance_ratio')
            return isinstance(ratio,(int,float)) and math.isfinite(ratio) and ratio>1.1
        if direction=='decrease':return diff < -1e-8
        if direction=='increase':return diff > 1e-8
        return abs(diff)>1e-8 or abs(calc.get('within_window_trend',0))>1e-8
    for key in valid:
        record=records[key]; signal=record['signal']
        if definition['event_kind']=='benign' and record.get('source')=='operator_plc_record':
            expected='operator_speed_setpoint' if definition['event_class']=='operator_speed_change' else 'planned_changeover'
            if signal==expected:supporting.append(key)
        elif definition['event_kind']=='artifact':
            if record.get('source')=='historian_quality' and record.get('observed_quality')==('MISSING' if definition['event_class']=='historian_dropout' else 'STUCK') and record.get('calculation',{}).get('affected_samples',0)>0:supporting.append(key)
        elif signal in primary and changed(record,definition['expected_directionality'][signal]):supporting.append(key)
    if definition['event_class']=='abnormal_tonnage':
        faults=[k for k in valid if records[k]['signal']=='press_fault' and changed(records[k],'increase')]
        transient=[]
        for key in valid:
            record=records[key];calc=record.get('calculation') or {}
            if record['signal']!='tonnage':continue
            baseline,current,difference,peak=(calc.get(k) for k in ('baseline_mean','current_mean','difference','robust_window_peak'))
            if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (baseline,current,difference,peak)):continue
            if math.isclose(current-baseline,difference,rel_tol=1e-6,abs_tol=1e-8) and peak>1.12*max(baseline,1):transient.append(key)
        supporting=list(dict.fromkeys(supporting+transient+faults)) if transient and faults else []
    sufficient=bool(supporting)
    # The public die/material pair requires both load and delayed quality.
    if definition['event_class'] in ('progressive_die_wear','quality_deterioration'):
        load=[records[k] for k in valid if records[k]['signal']=='tonnage']
        if definition['event_class']=='progressive_die_wear':
            sufficient=sufficient and any(changed(r,'increase') for r in load)
        else:
            sufficient=sufficient and any(isinstance(r.get('calculation',{}).get('difference'),(int,float)) and abs(r['calculation']['difference'])<=.12*max(abs(r['calculation'].get('baseline_mean',0)),1) and math.isclose(r['calculation'].get('current_mean',float('inf'))-r['calculation'].get('baseline_mean',0),r['calculation']['difference'],rel_tol=1e-6,abs_tol=1e-8) for r in load)
    return supporting,sufficient


def _shared_support(claim,records):
    """Observed loss can justify ambiguity without pretending to identify cause."""
    support=[]
    for key in _evidence(claim,records):
        record=records[key];calc=record.get('calculation') or {}
        base,current,diff=(calc.get(k) for k in ('baseline_mean','current_mean','difference'))
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (base,current,diff)):continue
        if not math.isclose(current-base,diff,rel_tol=1e-6,abs_tol=1e-8):continue
        signal=record['signal']
        if ((signal=='spm' and diff < -max(1,abs(base)*.05)) or
            (signal in ('press_stop','press_fault') and diff>.05) or
            (signal=='feed_complete' and diff<-.05) or
            (signal=='quality_measurement' and diff>.01)):
            support.append(key)
    return support


def score(truth: list[dict], claims: list[dict], evidence_catalog=None) -> dict:
    """Greedy longest-overlap one-to-one assignment; no hidden ID matching.

    Evidence catalog is evaluator-owned provenance keyed by public evidence ID.
    Missing catalog deliberately gives no evidence quality/completeness credit.
    """
    catalog = evidence_catalog or {}
    if isinstance(catalog, list):
        catalog = {e.get('id', e.get('evidence_id')): e for e in catalog}
    candidates = []
    for ci, c in enumerate(claims):
        ca, cb = _interval(c)
        for ti, t in enumerate(truth):
            ta, tb = _interval(t)
            overlap = min(cb, tb) - max(ca, ta)
            gap = max(ta - cb, ca - tb, 0)
            if overlap > 0 or gap <= TOLERANCE_S:
                candidates.append((max(overlap, 0), -abs(ca-ta), -ci, -ti, ci, ti))
    used_c, used_t, matches = set(), set(), []
    result = dict(standard_version=STANDARD_VERSION,tolerance_s=TOLERANCE_S,points=0,detected=0,correct_cause=0,incorrect_cause=0,unresolved_correctly=0,false_positives=0,missed=0,evidence_completeness=0,evidence_quality=0,unsupported_certainty_violations=0,alternatives={'evaluated':0,'missing':0},timing={'recognition_delay_s':[]},matches=matches)
    for *_, ci, ti in sorted(candidates, reverse=True):
        if ci in used_c or ti in used_t: continue
        c, t = claims[ci], truth[ti]
        if _kind(c) != _kind(t): continue
        used_c.add(ci); used_t.add(ti)
        valid, sufficient = _support(c,catalog,t)
        unresolved = not c.get('failed_item') and not c.get('failure_mechanism')
        if unresolved:valid=list(dict.fromkeys(valid+_shared_support(c,catalog)))
        correct = all(c.get(k) and str(c[k]).casefold().strip()==str(t.get(k,'')).casefold().strip() for k in ('failed_item','failure_mechanism'))
        result['detected'] += 1; result['points'] += int(_kind(t)=='fault')
        if _kind(t)=='fault':
            if correct and sufficient: result['correct_cause']+=1; result['points']+=2
            elif unresolved and valid and any(isinstance(alt,dict) and all(alt.get(k)==t.get(k) for k in ('failed_item','failure_mechanism')) and alt.get('disposition') in ('UNRESOLVED','unresolved','PLAUSIBLE','plausible','NOT_OBSERVABLE') and alt.get('reason') for alt in c.get('alternatives',[])): result['unresolved_correctly']+=1
            else: result['incorrect_cause']+=1
        result['evidence_completeness'] += bool(valid)
        result['evidence_quality'] += len(valid)
        alternatives=c.get('alternatives',[])
        result['alternatives']['evaluated' if alternatives and all(isinstance(a,dict) and a.get('disposition') and a.get('reason') for a in alternatives) else 'missing']+=1
        result['timing']['recognition_delay_s'].append(max(0,_interval(c)[0]-_interval(t)[0]))
        matches.append(dict(claim_index=ci,truth_index=ti,overlap_s=max(0,min(_interval(c)[1],_interval(t)[1])-max(_interval(c)[0],_interval(t)[0])),valid_evidence=valid))
    result['false_positives']=len(claims)-len(used_c)
    result['missed']=len(truth)-len(used_t)
    result['points']-=result['false_positives']
    for c in claims:
        state=c.get('diagnosis_state','')
        if state in ('EVIDENCE_SUPPORTED_CAUSE','VERIFIED_ROOT_CAUSE','SUSTAINED') and (not _support(c,catalog)[1] or state in ('VERIFIED_ROOT_CAUSE','SUSTAINED')):
            result['unsupported_certainty_violations']+=1; result['points']-=1
    return result
