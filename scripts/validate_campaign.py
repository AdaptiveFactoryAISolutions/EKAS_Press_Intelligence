#!/usr/bin/env python3
"""Full-duration public-observation detection, isolated diagnosis and evaluation.

No truth is accepted by detector or claim builder. Simulation truth is written
outside diagnostic storage and loaded for scoring only after claims are frozen.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
from statistics import mean, pstdev
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/HistorianSim/src')]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


from ekas_press_intelligence.rca.campaign import detect_windows


def frozen_claims(evidence, windows, worker):
    """Create immutable JSON-compatible claims using public worker output only."""
    claims=[]; facts={}; reports=[]
    baseline=[r for r in evidence['samples'] if r['t']<3600]
    for index,(start,end) in enumerate(windows):
        subset={k:v for k,v in evidence.items() if k!='samples'}
        subset['context']=dict(evidence['context'],analysis_start_s=start,analysis_end_s=end-1)
        subset['samples']=[r for r in evidence['samples'] if start<=r['t']<end]
        subset['baseline_samples']=baseline
        report=worker(subset,'Why did measured production or quality change in this period?')
        reports.append(report)
        supported=[h for h in report.get('hypotheses',[]) if h['disposition']=='SUPPORTED']
        primary=supported[0] if supported else None
        kind=primary.get('event_kind','fault') if primary else 'fault'
        # Suspected causes retain explicit ambiguity instead of being scored as
        # definitive item/mechanism claims. Artifact/operator records are direct.
        assert_cause=primary is not None and (kind!='fault' or report.get('cause_claim_eligible',False) or report.get('diagnosis_state')=='EVIDENCE_SUPPORTED_CAUSE')
        evidence_ids=[]
        supporting_ids={ref for h in report.get('hypotheses',[]) if h.get('disposition') in ('SUPPORTED','NOT_OBSERVABLE','UNRESOLVED') for ref in h.get('supporting_evidence',[])}
        for fact in report.get('evidence',[]):
            ref=f'window-{index}:{fact["id"]}'
            facts[ref]=dict(fact,id=ref)
            if fact['id'] in supporting_ids and fact.get('quality')=='GOOD': evidence_ids.append(ref)
        alternatives=[]
        for hypothesis in report.get('hypotheses',[]):
            alt=dict(hypothesis)
            if not assert_cause and alt['disposition'] in ('SUPPORTED','NOT_OBSERVABLE'): alt['disposition']='UNRESOLVED'
            alternatives.append(alt)
        claims.append(dict(start_s=start,end_s=end,event_kind=kind,failed_item=primary['failed_item'] if assert_cause else None,failure_mechanism=primary['failure_mechanism'] if assert_cause else None,event_class=primary['event_class'] if assert_cause else None,diagnosis_state=report.get('diagnosis_state','OBSERVED_ANOMALY'),evidence=evidence_ids,alternatives=alternatives,qualification=report.get('qualification','')))
    return claims,facts,reports


def shared_observation_digest(evidence):
    from ekas_press_intelligence.domain import profile_signals
    sparse=profile_signals('sparse')
    hasher=hashlib.sha256()
    for row in evidence['samples']:
        shared={key:row.get(key) for key in ['t']+sparse}
        shared['data_quality']={k:v for k,v in row.get('data_quality',{}).items() if k in sparse}
        hasher.update(json.dumps(shared,sort_keys=True,separators=(',',':')).encode())
    return hasher.hexdigest()


def measured_manifestations(evidence, truth):
    # Evaluator-only characterization AFTER claims have been frozen.
    from ekas_press_intelligence.domain import catalog
    cat={c['event_class']:c for c in catalog()}; rows=evidence['samples']; result=[]
    for event in truth:
        entry=cat[event['event_class']]; signal=entry['observable_signals'][0]
        baseline=[r for r in rows[:7200] if isinstance(r.get(signal),(int,float))]
        during=[r for r in rows if event['start_s']<=r['t']<event['end_s']]
        valid=[r for r in during if isinstance(r.get(signal),(int,float))]
        output={'event_class':event['event_class'],'signal':signal,'available':bool(baseline),'interval_samples':len(during)}
        if event['event_kind']=='artifact':
            flag='MISSING' if event['event_class']=='historian_dropout' else 'STUCK'
            output['measured_manifestation']=any(flag in r.get('data_quality',{}).values() for r in during)
        elif baseline and valid:
            before=[r[signal] for r in baseline]; after=[r[signal] for r in valid]
            if signal in ('stroke_count','part_count','scrap_count','strip_progression'):
                before=[(b[signal]-a[signal])/max(1,b['t']-a['t']) for a,b in zip(baseline,baseline[1:])]
                after=[(b[signal]-a[signal])/max(1,b['t']-a['t']) for a,b in zip(valid,valid[1:])]
            delta=mean(after)-mean(before); deviation=max(abs(x-mean(before)) for x in after)
            output.update(baseline_mean=mean(before),event_mean=mean(after),delta=delta,baseline_std=pstdev(before),event_std=pstdev(after),max_deviation=deviation)
            direction=entry['expected_directionality'][signal]
            output['measured_manifestation']=(pstdev(after)>max(.1,pstdev(before)*3) if direction in ('variance','intermittent') else abs(delta)>max(.01,pstdev(before)*3) or deviation>max(.1,pstdev(before)*6))
        else: output['measured_manifestation']=None
        result.append(output)
    return result


def check_physics(evidence):
    rows=evidence['samples']; valid=[r for r in rows if r.get('stroke_count') is not None]
    errors=[];checks=0
    def require(condition,message):
        nonlocal checks
        checks+=1
        if not condition: errors.append(message)
    require(len(rows)==evidence['context']['duration_s'],'sample count')
    require(all(r['t']==i for i,r in enumerate(rows)),'regular integer scan times')
    require(all(r['press_run']+r['press_stop']==1 for r in valid),'run/stop complement')
    require(all(0<=r['spm']<=65 for r in valid if r['spm'] is not None),'SPM engineering bounds')
    require(all(a['stroke_count']<=b['stroke_count'] for a,b in zip(valid,valid[1:])),'monotonic strokes')
    require(all(r['part_count']<=r['stroke_count'] for r in valid),'good count <= strokes')
    adjacent=[(a,b) for a,b in zip(rows,rows[1:]) if a.get('stroke_count') is not None and b.get('stroke_count') is not None]
    require(all((b['plc_state']=='STROKE') == (b['stroke_count']>a['stroke_count']) and (b['press_run'] or b['stroke_count']==a['stroke_count']) and (not b['press_run'] or b['plc_state']==('STROKE' if b['stroke_count']>a['stroke_count'] else 'FEED')) for a,b in adjacent),'scan-end PLC state matches completed strokes')
    if evidence['context']['profile']=='enhanced':
        require(all(r['part_count']+r['scrap_count']==r['stroke_count'] for r in valid),'good+scrap = strokes')
        require(all(r['strip_progression']==r['stroke_count'] for r in valid),'one feed pitch per stroke')
        require(all(0<=r['loop_height']<=1.5 and -.2<=r['lube_pressure']<=10.2 and 0<=r['tonnage']<=180 for r in valid),'continuous engineering bounds')
    return {'passed':not errors,'checks':checks,'errors':errors,'samples':len(rows),'baseline_samples':sum(r['t']<7200 for r in rows),'baseline_mean_spm':mean(r['spm'] for r in rows[:7200] if r['spm'] is not None)}


def evaluate_by_class(truth,claims,metrics,reports,evidence_catalog=None):
    from ekas_press_intelligence.benchmark.evaluator import score
    matched={m['truth_index']:m for m in metrics['matches']};result=[]
    for i,event in enumerate(truth):
        match=matched.get(i);claim=claims[match['claim_index']] if match else None
        # Use exactly the evaluator's evidence sufficiency and ambiguity rules;
        # identity alone must never manufacture per-class correctness.
        local=score([event],[claim] if claim else [],evidence_catalog or {})
        result.append(dict(event_class=event['event_class'],event_kind=event['event_kind'],detected=bool(local['detected']),correct_cause=bool(local['correct_cause']),incorrect_cause=bool(local['incorrect_cause']),unresolved_correctly=bool(local['unresolved_correctly']),missed=not bool(local['detected']),overlap_s=match['overlap_s'] if match else 0,evidence_completeness=bool(local['evidence_completeness']),unsupported_certainty=bool(local['unsupported_certainty_violations'])))
    return result


def run(output_dir=ROOT/'validation',raw_dir=ROOT/'work/campaign',duration_s=86400):
    from ekas_press_intelligence.simulator.engine import simulate
    from ekas_press_intelligence.simulator.export import export_historian
    from ekas_press_intelligence.sandbox import investigate_isolated
    from ekas_press_intelligence.benchmark.evaluator import score
    from ekas_press_intelligence.observability.model import assess
    from ekas_press_intelligence.domain import profile_signals
    output_dir=Path(output_dir);raw_dir=Path(raw_dir);output_dir.mkdir(parents=True,exist_ok=True);raw_dir.mkdir(parents=True,exist_ok=True)
    source_paths=['src/ekas_press_intelligence/'+p for p in ('domain.py','acquisition.py','simulator/engine.py','simulator/export.py','rca/engine.py','rca/campaign.py','benchmark/evaluator.py','sandbox.py','observability/model.py')]
    source_paths.append('scripts/validate_campaign.py')
    source_hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}
    report={'source_sha256':source_hashes,'seed':7,'duration_s':duration_s,'synthetic':True,'blind_boundary':'Evidence-only public detector and Bubblewrap worker; frozen claims saved before evaluator truth load','profiles':{}}
    truth_digest=None
    shared_digest=None
    for profile in ('sparse','enhanced'):
        print('Generating',profile,flush=True)
        first=simulate(7,duration_s,profile)
        path=raw_dir/profile;path.mkdir(exist_ok=True)
        truth_path=path/'private_truth.json';truth_path.write_text(json.dumps(first.truth,sort_keys=True))
        this_truth=digest(first.truth)
        if truth_digest is None: truth_digest=this_truth
        public=first.evidence;del first
        hash_one=digest(public)
        shared=shared_observation_digest(public)
        if shared_digest is None: shared_digest=shared
        with gzip.open(path/'public_evidence.json.gz','wt') as f: json.dump(public,f,separators=(',',':'))
        second=simulate(7,duration_s,profile)
        deterministic=hash_one==digest(second.evidence) and this_truth==digest(second.truth)
        del second
        invariant=check_physics(public)
        windows=detect_windows(public)
        print('Diagnosing',profile,len(windows),'publicly detected windows',flush=True)
        claims,facts,reports=frozen_claims(public,windows,investigate_isolated)
        frozen=json.dumps(claims,sort_keys=True,indent=2)
        for prior in (path/'frozen_claims.json',path/'diagnostic_reports.json'):
            if prior.exists():
                archive=path/'history';archive.mkdir(exist_ok=True)
                saved=archive/(prior.stem+'-'+hashlib.sha256(prior.read_bytes()).hexdigest()[:12]+prior.suffix)
                if not saved.exists(): saved.write_bytes(prior.read_bytes())
        (path/'frozen_claims.json').write_text(frozen)
        (path/'diagnostic_reports.json').write_text(json.dumps(reports))
        # Evaluation starts here. No evaluator data was passed into diagnosis.
        truth=json.loads(truth_path.read_text())
        metrics=score(truth,json.loads(frozen),facts)
        class_results=evaluate_by_class(truth,claims,metrics,reports,facts)
        consistency={key:sum(int(row[key]) for row in class_results)==metrics[key] for key in ('detected','correct_cause','incorrect_cause','unresolved_correctly','missed','evidence_completeness')}
        if not all(consistency.values()): raise AssertionError('Per-class evaluator metrics disagree with aggregate score: '+str(consistency))
        recovery=[]
        for event in truth:
            end=event['end_s'];tail=[r for r in public['samples'] if end+300<=r['t']<end+600 and r.get('spm') is not None]
            recovery.append({'event_class':event['event_class'],'samples':len(tail),'mean_spm':mean(r['spm'] for r in tail) if tail else None,'returned_to_baseline_rate':bool(tail and mean(r['spm'] for r in tail)>58)})
        exported=export_historian(public,path/'historian')
        report['profiles'][profile]={'deterministic':deterministic,'evidence_sha256':hash_one,'truth_sha256':this_truth,'same_physics_truth_across_profiles':this_truth==truth_digest,'shared_observations_sha256':shared,'same_shared_observations_across_profiles':shared==shared_digest,'frozen_claims_sha256':hashlib.sha256(frozen.encode()).hexdigest(),'physics':invariant,'windows':[list(w) for w in windows],'scoring':metrics,'per_class':class_results,'per_class_agrees_with_scorer':consistency,'manifestations':measured_manifestations(public,truth),'recovery':recovery,'observability':assess(profile_signals(profile)),'export':exported}
        del public
    report['source_stable_during_run']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in source_hashes.items())
    report['acceptance_note']='Measured diagnostic failures and unresolved cases remain visible; passing physics/determinism does not imply diagnostic or manual acceptance.'
    previous=output_dir/'campaign.json'
    if previous.exists():
        history=output_dir/'history';history.mkdir(exist_ok=True)
        archived=history/('campaign-'+hashlib.sha256(previous.read_bytes()).hexdigest()[:12]+'.json')
        if not archived.exists(): archived.write_bytes(previous.read_bytes())
    (output_dir/'campaign.json').write_text(json.dumps(report,indent=2,sort_keys=True))
    lines=['# Full-duration synthetic campaign validation','',f'Seed 7; {duration_s} seconds; evidence-only detection and OS-isolated RCA.','', '| Profile | Repeat digest | Physics | Windows | Detected | Correct | Unresolved | Incorrect | FP | Missed |','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,p in report['profiles'].items():
        m=p['scoring'];lines.append(f"| {name} | {p['deterministic']} | {p['physics']['passed']} | {len(p['windows'])} | {m['detected']} | {m['correct_cause']} | {m['unresolved_correctly']} | {m['incorrect_cause']} | {m['false_positives']} | {m['missed']} |")
    lines+=['','Raw public datasets, compressed/regular historian exports, private truth and frozen claims remain in ignored `work/campaign/`. `campaign.json` retains hashes, artifact sizes/counts, per-class results, recovery and measured observability.','',report['acceptance_note']]
    (output_dir/'CAMPAIGN.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({p:{k:v for k,v in x['scoring'].items() if k in ('detected','correct_cause','incorrect_cause','unresolved_correctly','false_positives','missed')} for p,x in report['profiles'].items()},indent=2),flush=True)
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--duration-s',type=int,default=86400);args=parser.parse_args()
    run(duration_s=args.duration_s)
