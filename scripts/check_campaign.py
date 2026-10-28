"""Fail closed on incomplete or adverse full-duration qualification artifacts."""
import json
import sys
from pathlib import Path


def violations(report):
    errors=[]
    if not report.get('source_stable_during_run'):errors.append('Source changed during run')
    if report.get('duration_s',0)<86400:errors.append('Full-duration campaign missing')
    if set(report.get('profiles',{}))!={'sparse','enhanced'}:errors.append('Both profiles required')
    for name,p in report.get('profiles',{}).items():
        for check in ('deterministic','same_physics_truth_across_profiles','same_shared_observations_across_profiles'):
            if not p.get(check):errors.append(name+': '+check)
        if not p.get('physics',{}).get('passed'):errors.append(name+': physics')
        if not p.get('per_class_agrees_with_scorer') or not all(p['per_class_agrees_with_scorer'].values()):errors.append(name+': scorer agreement')
        rows=p.get('per_class',[]);m=p.get('scoring',{})
        if len(rows)<16 or m.get('detected')!=len(rows):errors.append(name+': event detection')
        for key in ('incorrect_cause','false_positives','missed','unsupported_certainty_violations'):
            if m.get(key)!=0:errors.append(name+': '+key)
        if m.get('evidence_completeness')!=len(rows):errors.append(name+': evidence completeness')
        physical=sum(r.get('event_kind')=='fault' for r in rows)
        if not physical:errors.append(name+': physical challenges missing')
        elif name=='enhanced' and m.get('correct_cause')!=physical:errors.append(name+': physical cause discrimination')
        elif name=='sparse' and m.get('correct_cause',0)+m.get('unresolved_correctly',0)!=physical:errors.append(name+': uncertainty handling')
        if len(p.get('recovery',[]))!=len(rows) or not all(r.get('returned_to_baseline_rate') for r in p.get('recovery',[])):errors.append(name+': recovery')
        if name=='enhanced' and (len(p.get('manifestations',[]))!=len(rows) or not all(r.get('measured_manifestation') for r in p.get('manifestations',[]))):errors.append(name+': manifestation')
        if p.get('export',{}).get('regular_rows')!=report.get('duration_s'):errors.append(name+': historian rows')
    return errors


if __name__=='__main__':
    path=Path(sys.argv[1] if len(sys.argv)>1 else 'validation/campaign.json')
    problems=violations(json.loads(path.read_text()))
    if problems:raise SystemExit('\n'.join(problems))
    print('Full-duration campaign acceptance checks passed')
