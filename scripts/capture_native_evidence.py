"""Capture immutable evidence summaries from completed actual jobs, without keys."""
import argparse
import hashlib
import json
from pathlib import Path
from ekas_press_intelligence.native.jobs import JobStore,TERMINAL
from ekas_press_intelligence.native.data import public_files


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',required=True,type=Path)
    parser.add_argument('--job',required=True);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();store=JobStore(args.state);job=store.get(args.job)
    if job['state'] not in TERMINAL:raise SystemExit('Only terminal jobs can be captured')
    result=job.get('result') or {};target=args.state/'artifacts'/args.job
    evidence={k:job[k] for k in ('id','operation','parameters','state','created_at','updated_at','error','audit_failures')}
    evidence['result']={k:v for k,v in result.items() if k not in ('dataset','private_directory','public_directory')}
    info=result.get('dataset')
    if info:evidence['dataset_summary']={k:info[k] for k in ('start','end','rows','raw','grid','event_files','disclosure') if k in info}
    relative=result.get('public_directory')
    if relative:
        public=(target/relative).resolve()
        if not public.is_relative_to(target.resolve()):raise SystemExit('Public artifact path escaped job')
        actual=public_files(public)
        if actual!=result.get('files'):raise SystemExit('Public artifact hashes no longer match completed result')
        evidence['verified_public_files']=actual
    validation=target/'private/metadata/validation.json'
    if validation.is_file():
        evidence['actual_native_validation_report']=json.loads(validation.read_text())
        evidence['actual_native_validation_sha256']=hashlib.sha256(validation.read_bytes()).hexdigest()
    try:
        registered=store.dataset(args.job)
        evidence['registration']={k:v for k,v in registered.items() if k in ('id','source','status','scoring_status','parent_dataset_id','physical_source_dataset_id')}
    except KeyError:evidence['registration']=None
    evidence['scope']='Actual completed native job, unchanged pass/fail findings and public hashes. No press qualification or EKAS deployment readiness is inferred; private answer keys are omitted.'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:json.dump(evidence,stream,indent=2,allow_nan=False);stream.write('\n')
    args.output.chmod(0o400)
    print(json.dumps({'output':str(args.output),'job':args.job,'state':job['state']}))


if __name__=='__main__':main()
